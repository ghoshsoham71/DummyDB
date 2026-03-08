import logging
import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
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
from src.routers.schema_parse_router import get_schema_by_id

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
    """Handler for synthetic data generation jobs"""
    try:
        if progress_callback:
            progress_callback(10, "Loading schema...")
        
        # Get schema data
        schema_id = parameters["schema_id"]
        schema_data = get_schema_by_id(schema_id)
        
        if not schema_data:
            raise Exception(f"Schema {schema_id} not found")
        
        if progress_callback:
            progress_callback(20, "Initializing SDV generator...")
        
        # Import SDV generator
        from src.utils.sdv_synthetic_generator import SDVSyntheticGenerator
        
        # Initialize generator
        generator = SDVSyntheticGenerator(schema_data["schema"])
        
        if progress_callback:
            progress_callback(30, "Creating metadata...")
        
        # Create metadata
        generator.create_metadata()
        
        if progress_callback:
            progress_callback(40, "Loading seed data...")
        
        # Load seed data
        seed_data_dir = parameters.get("seed_data_dir", "seed_data")
        generator.load_seed_data(seed_data_dir)
        
        if progress_callback:
            progress_callback(60, "Training synthesizer...")
        
        # Train synthesizer
        synthesizer_type = parameters.get("synthesizer_type", "HMA")
        generator.train_synthesizer(synthesizer_type)
        
        if progress_callback:
            progress_callback(80, "Generating synthetic data...")
        
        # Generate synthetic data
        scale = parameters.get("scale_factor", 2.0)
        num_rows = parameters.get("num_rows")
        
        if num_rows:
            synthetic_data = generator.generate_synthetic_data(num_rows=num_rows)
        else:
            synthetic_data = generator.generate_synthetic_data(scale=scale)
        
        if progress_callback:
            progress_callback(90, "Saving synthetic data...")
        
        # Save synthetic data
        output_dir = parameters.get("output_dir", "synthetic_data")
        generator.save_synthetic_data(output_dir)
        
        if progress_callback:
            progress_callback(95, "Evaluating quality...")
        
        # Evaluate quality
        try:
            evaluation = generator.evaluate_quality()
            quality_score = evaluation.get("overall_score")
        except Exception as e:
            logger.warning(f"Quality evaluation failed: {e}")
            quality_score = None
        
        if progress_callback:
            progress_callback(100, "Generation complete!")
        
        # Get summary
        summary = generator.get_generation_summary()
        
        # Get file paths
        file_paths = []
        output_path = Path(output_dir)
        if output_path.exists():
            file_paths = [str(f) for f in output_path.glob("*_synthetic.csv")]
        
        return {
            "success": True,
            "output_directory": output_dir,
            "file_paths": file_paths,
            "quality_score": quality_score,
            "generation_summary": summary,
            "synthesizer_type": synthesizer_type,
            "scale_factor": scale
        }
        
    except Exception as e:
        logger.error(f"Synthetic generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Register handler
job_manager.register_handler(JobType.SYNTHETIC_GENERATION, synthetic_generation_handler)

@router.post("/generate", response_model=SyntheticGenerationResponse)
@limiter.limit("5/minute")
async def generate_synthetic_data(
    request: Request,
    generate_request: GenerateRequest,
    background_tasks: BackgroundTasks
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

@router.get("/jobs/{job_id}/status")
@limiter.limit("50/minute")
async def get_generation_status(request: Request, job_id: str):
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
    offset: int = Query(0, ge=0)
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
async def cancel_generation_job(request: Request, job_id: str):
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
    config: Optional[Dict[str, Any]] = None
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
async def get_generation_stats(request: Request):
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