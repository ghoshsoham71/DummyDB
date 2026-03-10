import logging
import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

from src.lib.schemas import (
    SyntheticGenerationRequest,
    SyntheticGenerationResponse,
    ErrorResponse
)
from src.utils.job_manager import job_manager, JobType
from src.utils.file_manager import file_manager
from src.services.schema_store import get_schema_by_id, PARSED_SCHEMAS
from src.lib.auth import get_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Synthetic Data Generation"], prefix="/synthetic")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

class GenerateRequest(BaseModel):
    schema_id: str
    scale_factor: float = 2.0
    num_rows: Optional[Dict[str, int]] = None
    synthesizer_type: str = "HMA"
    output_format: str = "csv"
    seed: Optional[int] = None

def synthetic_generation_handler(parameters: Dict[str, Any], 
                               progress_callback=None) -> Dict[str, Any]:
    """Handler for synthetic data generation jobs using Groq LLM."""
    try:
        if progress_callback:
            progress_callback(10, "Loading schema...")
        
        # Get schema data
        schema_id = parameters["schema_id"]
        schema_data = get_schema_by_id(schema_id)
        
        if not schema_data:
            raise Exception(f"Schema {schema_id} not found")
        
        schema = schema_data["schema"]
        num_rows = parameters.get("num_rows", {})
        # Check if seed data is already provided
        seed_data_dir = parameters.get("seed_data_dir", f"seed_data/{schema_id}")
        output_dir = parameters.get("output_dir", f"synthetic_data/{schema_id}")
        has_seed_data = Path(seed_data_dir).exists() and any(Path(seed_data_dir).glob("*.csv"))
        
        if progress_callback:
            if has_seed_data:
                progress_callback(20, "Using provided seed data (no rate limit)...")
            else:
                progress_callback(20, "Generating seed data with LLM (Groq)...")
        
        # Generate data using Groq LLM
        from src.utils.mock_data_generator import generate_mock_data, save_mock_data_csv
        
        generated_data = generate_mock_data(
            schema=schema,
            num_rows=num_rows,
            default_rows=10,
            skip_rate_limit=has_seed_data,
        )
        
        if not generated_data:
            raise Exception("LLM returned no data for any table")
        
        if progress_callback:
            progress_callback(80, "Saving generated data...")
        
        # Save to CSV
        file_paths = save_mock_data_csv(generated_data, output_dir)
        
        if progress_callback:
            progress_callback(100, "Generation complete!")
        
        # Build summary
        summary = {
            table: {"rows": len(rows), "columns": len(rows[0]) if rows else 0}
            for table, rows in generated_data.items()
        }
        
        return {
            "success": True,
            "output_directory": output_dir,
            "file_paths": file_paths,
            "quality_score": None,
            "generation_summary": summary,
            "synthesizer_type": "groq-llm",
            "scale_factor": parameters.get("scale_factor", 2.0),
        }
        
    except Exception as e:
        logger.error(f"Synthetic generation failed: {e}")
        raise  # let the job manager mark it as FAILED

# Register handler
job_manager.register_handler(JobType.SYNTHETIC_GENERATION, synthetic_generation_handler)

@router.post("/generate", response_model=SyntheticGenerationResponse)
@limiter.limit("5/minute")
async def generate_synthetic_data(
    request: Request,
    generate_request: GenerateRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """
    Generate synthetic data from schema
    
    This endpoint creates a background job to generate synthetic data
    using the specified schema and parameters.
    """
    try:
        logger.info(f"Starting synthetic data generation for schema: {generate_request.schema_id}")
        
        # Validate schema exists
        schema_data = get_schema_by_id(generate_request.schema_id)
        if not schema_data:
            raise HTTPException(
                status_code=404,
                detail=f"Schema {generate_request.schema_id} not found"
            )
        if schema_data.get("user_id") != user.id:
            raise HTTPException(status_code=404, detail="Schema not found")
        
        # Prepare job parameters
        job_params = {
            "schema_id": generate_request.schema_id,
            "scale_factor": generate_request.scale_factor,
            "num_rows": generate_request.num_rows,
            "synthesizer_type": generate_request.synthesizer_type,
            "output_format": generate_request.output_format,
            "seed": generate_request.seed,
            "seed_data_dir": "seed_data",
            "output_dir": f"synthetic_data/{generate_request.schema_id}"
        }
        
        # Submit job
        job_id = await job_manager.submit_job(
            JobType.SYNTHETIC_GENERATION,
            job_params
        )
        
        return SyntheticGenerationResponse(
            success=True,
            generation_id=job_id,
            message=f"Synthetic data generation job submitted with ID: {job_id}",
            processing_time=0.0,
            statistics={"job_id": job_id, "schema_id": generate_request.schema_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit synthetic generation job: {e}")
        return SyntheticGenerationResponse(
            success=False,
            generation_id=None,
            message=f"Failed to submit generation job: {str(e)}",
            processing_time=0.0
        )

@router.post("/generate/stream")
@limiter.limit("3/minute")
async def generate_synthetic_data_stream(
    request: Request,
    generate_request: GenerateRequest,
    user=Depends(get_current_user),
):
    """
    Stream synthetic data generation via Server-Sent Events.
    Each table's progress is sent as a separate SSE event.
    """
    schema_data = get_schema_by_id(generate_request.schema_id)
    if not schema_data:
        raise HTTPException(status_code=404, detail=f"Schema {generate_request.schema_id} not found")
    if schema_data.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Check if seed data exists → skip rate limiting
    seed_dir = Path(f"seed_data/{generate_request.schema_id}")
    has_seed_data = seed_dir.exists() and any(seed_dir.glob("*.csv"))

    from src.utils.mock_data_generator import generate_mock_data_streaming

    def event_stream():
        for event_json in generate_mock_data_streaming(
            schema=schema_data["schema"],
            num_rows=generate_request.num_rows or {},
            default_rows=10,
            output_dir=f"synthetic_data/{generate_request.schema_id}",
            skip_rate_limit=has_seed_data,
        ):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("/rate-limits")
async def get_rate_limits():
    """Return current rate limit configuration for UI display."""
    from src.utils.rate_limiter import (
        MAX_TOKENS, REFILL_RATE, MAX_CONCURRENT,
        MAX_TABLES_PER_REQUEST, MAX_ROWS_PER_TABLE,
    )
    return {
        "requests_per_minute": 3,
        "token_bucket_size": MAX_TOKENS,
        "token_refill_per_sec": REFILL_RATE,
        "max_concurrent_calls": MAX_CONCURRENT,
        "max_tables_per_request": MAX_TABLES_PER_REQUEST,
        "max_rows_per_table": MAX_ROWS_PER_TABLE,
        "seed_data_bypasses": True,
    }

@router.get("/download/{schema_id}")
@limiter.limit("20/minute")
async def download_synthetic_data(request: Request, schema_id: str, user=Depends(get_current_user)):
    """Download generated synthetic data as a ZIP archive."""
    # Verify user owns this schema
    schema_data = PARSED_SCHEMAS.get(schema_id)
    if not schema_data or schema_data.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Schema not found")

    output_dir = Path(f"synthetic_data/{schema_id}")
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail=f"No generated data found for schema {schema_id}")

    csv_files = list(output_dir.glob("*.csv"))
    if not csv_files:
        raise HTTPException(status_code=404, detail="No CSV files found in the output directory")

    # Create ZIP archive
    archive_path = file_manager.create_archive(
        [str(f) for f in csv_files],
        f"synthetic_{schema_id}",
    )

    return FileResponse(
        path=archive_path,
        filename=f"synthetic_{schema_id}.zip",
        media_type="application/zip",
    )

@router.get("/jobs/{job_id}/status")
@limiter.limit("50/minute")
async def get_generation_status(request: Request, job_id: str, user=Depends(get_current_user)):
    """Get status of synthetic data generation job"""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "progress": job.progress,
        "message": job.message,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": job.result,
        "error": job.error
    }

@router.get("/jobs")
@limiter.limit("50/minute")
async def list_generation_jobs(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user),
):
    """List synthetic data generation jobs"""
    jobs = job_manager.get_job_list(
        job_type=JobType.SYNTHETIC_GENERATION,
        limit=limit,
        offset=offset
    )
    
    return {
        "jobs": jobs,
        "total_jobs": len(jobs),
        "limit": limit,
        "offset": offset
    }

@router.delete("/jobs/{job_id}")
@limiter.limit("10/minute")
async def cancel_generation_job(request: Request, job_id: str, user=Depends(get_current_user)):
    """Cancel a synthetic data generation job"""
    success = job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or cannot be cancelled"
        )
    
    return {
        "message": f"Job {job_id} cancelled successfully",
        "job_id": job_id
    }

@router.get("/download/{generation_id}")
@limiter.limit("20/minute")
async def download_synthetic_data(request: Request, generation_id: str):
    """Download generated synthetic data as ZIP archive"""
    try:
        # Get job result
        job = job_manager.get_job(generation_id)
        
        if not job or not job.result:
            raise HTTPException(
                status_code=404,
                detail=f"Generation {generation_id} not found or not completed"
            )
        
        # Get file paths from job result
        file_paths = job.result.get("file_paths", [])
        
        if not file_paths:
            raise HTTPException(
                status_code=404,
                detail="No files available for download"
            )
        
        # Create archive
        archive_name = f"synthetic_data_{generation_id}"
        archive_path = file_manager.create_archive(file_paths, archive_name)
        
        return FileResponse(
            path=archive_path,
            filename=f"{archive_name}.zip",
            media_type="application/zip"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create download archive: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create download archive: {str(e)}"
        )

@router.get("/templates")
@limiter.limit("50/minute")
async def get_generation_templates(request: Request):
    """Get available synthetic data generation templates/configurations"""
    templates = {
        "quick_generation": {
            "name": "Quick Generation",
            "description": "Fast generation with basic settings",
            "scale_factor": 2.0,
            "synthesizer_type": "HMA",
            "recommended_for": "Small datasets, quick testing"
        },
        "balanced_generation": {
            "name": "Balanced Generation",
            "description": "Good balance of quality and speed",
            "scale_factor": 5.0,
            "synthesizer_type": "HMA",
            "recommended_for": "Medium datasets, production use"
        },
        "high_quality": {
            "name": "High Quality Generation",
            "description": "Maximum quality with CTGAN synthesizer",
            "scale_factor": 10.0,
            "synthesizer_type": "CTGAN",
            "recommended_for": "Large datasets, maximum quality needed"
        }
    }
    
    return {
        "templates": templates,
        "total_templates": len(templates)
    }

@router.post("/batch-generate")
@limiter.limit("3/minute")
async def batch_generate_synthetic_data(
    request: Request,
    schema_ids: List[str],
    config: Optional[Dict[str, Any]] = None,
    user=Depends(get_current_user),
):
    """Generate synthetic data for multiple schemas"""
    try:
        config = config or {}
        job_ids = []
        
        for schema_id in schema_ids:
            # Validate schema exists
            schema_data = get_schema_by_id(schema_id)
            if not schema_data:
                logger.warning(f"Schema {schema_id} not found, skipping")
                continue
            
            # Prepare job parameters
            job_params = {
                "schema_id": schema_id,
                "scale_factor": config.get("scale_factor", 2.0),
                "synthesizer_type": config.get("synthesizer_type", "HMA"),
                "output_format": config.get("output_format", "csv"),
                "seed_data_dir": "seed_data",
                "output_dir": f"synthetic_data/{schema_id}"
            }
            
            # Submit job
            job_id = await job_manager.submit_job(
                JobType.SYNTHETIC_GENERATION,
                job_params
            )
            job_ids.append(job_id)
        
        return {
            "message": f"Submitted {len(job_ids)} synthetic data generation jobs",
            "job_ids": job_ids,
            "total_schemas": len(schema_ids),
            "successful_submissions": len(job_ids)
        }
        
    except Exception as e:
        logger.error(f"Batch generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch generation failed: {str(e)}"
        )

@router.get("/stats")
@limiter.limit("50/minute")
async def get_generation_stats(request: Request, user=Depends(get_current_user)):
    """Get synthetic data generation statistics"""
    try:
        # Get job statistics
        job_stats = job_manager.get_job_stats()
        
        # Get file statistics
        storage_stats = file_manager.get_storage_stats()
        
        # Count synthetic data files
        synthetic_files = file_manager.list_files("synthetic_data", "*.csv", recursive=True)
        
        return {
            "job_statistics": job_stats,
            "storage_statistics": storage_stats,
            "synthetic_files": {
                "total_files": len(synthetic_files),
                "total_size": sum(f.get("size", 0) for f in synthetic_files),
                "recent_files": synthetic_files[:10]  # Latest 10 files
            },
            "system_health": {
                "job_queue_size": job_stats.get("queue_size", 0),
                "active_generations": job_stats.get("running", 0),
                "failed_generations": job_stats.get("failed", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get generation stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get generation statistics: {str(e)}"
        )