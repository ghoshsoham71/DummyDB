import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

from src.lib.schemas import (
    SeedDataRequest,
    SeedDataResponse,
    ErrorResponse
)
from src.utils.job_manager import job_manager, JobType
from src.utils.file_manager import file_manager
from src.services.schema_store import get_schema_by_id

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Seed Data Generation"], prefix="/seed")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

class GenerateSeedRequest(BaseModel):
    schema_id: str
    base_rows: int = 10
    locale: str = "en_US"
    custom_generators: Optional[Dict[str, Dict[str, Any]]] = None
    output_format: str = "csv"

def seed_data_generation_handler(parameters: Dict[str, Any], 
                               progress_callback=None) -> Dict[str, Any]:
    """Handler for seed data generation jobs"""
    try:
        if progress_callback:
            progress_callback(10, "Loading schema...")
        
        # Get schema data
        schema_id = parameters["schema_id"]
        schema_data = get_schema_by_id(schema_id)
        
        if not schema_data:
            raise Exception(f"Schema {schema_id} not found")
        
        if progress_callback:
            progress_callback(20, "Initializing seed data generator...")
        
        # Import seed data generator
        from seed_data_generator import SeedDataGenerator
        
        # Initialize generator
        locale = parameters.get("locale", "en_US")
        generator = SeedDataGenerator(schema_data["schema"], locale)
        
        if progress_callback:
            progress_callback(40, "Generating seed data...")
        
        # Generate seed data
        base_rows = parameters.get("base_rows", 10)
        output_dir = parameters.get("output_dir", f"seed_data/{schema_id}")
        
        datasets = generator.generate_all_seed_data(output_dir, base_rows)
        
        if progress_callback:
            progress_callback(90, "Saving generated data...")
        
        # Get summary
        summary = generator.get_generation_summary()
        
        if progress_callback:
            progress_callback(100, "Seed data generation complete!")
        
        # Get file paths
        file_paths = []
        output_path = Path(output_dir)
        if output_path.exists():
            file_paths = [str(f) for f in output_path.glob("*.csv")]
        
        return {
            "success": True,
            "output_directory": output_dir,
            "file_paths": file_paths,
            "generation_summary": summary,
            "base_rows": base_rows,
            "locale": locale,
            "datasets_generated": len(datasets)
        }
        
    except Exception as e:
        logger.error(f"Seed data generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Register handler
job_manager.register_handler(JobType.SEED_GENERATION, seed_data_generation_handler)

@router.post("/generate", response_model=SeedDataResponse)
@limiter.limit("10/minute")
async def generate_seed_data(
    request: Request,
    generate_request: GenerateSeedRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate seed data from schema
    
    This endpoint creates a background job to generate realistic seed data
    using the specified schema and parameters.
    """
    try:
        logger.info(f"Starting seed data generation for schema: {generate_request.schema_id}")
        
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
            "base_rows": generate_request.base_rows,
            "locale": generate_request.locale,
            "custom_generators": generate_request.custom_generators,
            "output_format": generate_request.output_format,
            "output_dir": f"seed_data/{generate_request.schema_id}"
        }
        
        # Submit job
        job_id = await job_manager.submit_job(
            JobType.SEED_GENERATION,
            job_params
        )
        
        return SeedDataResponse(
            success=True,
            seed_id=job_id,
            message=f"Seed data generation job submitted with ID: {job_id}",
            processing_time=0.0,
            statistics={"job_id": job_id, "schema_id": generate_request.schema_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit seed generation job: {e}")
        return SeedDataResponse(
            success=False,
            seed_id=None,
            message=f"Failed to submit generation job: {str(e)}",
            processing_time=0.0
        )

@router.get("/jobs/{job_id}/status")
@limiter.limit("50/minute")
async def get_seed_generation_status(request: Request, job_id: str):
    """Get status of seed data generation job"""
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
async def list_seed_generation_jobs(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List seed data generation jobs"""
    jobs = job_manager.get_job_list(
        job_type=JobType.SEED_GENERATION,
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
async def cancel_seed_generation_job(request: Request, job_id: str):
    """Cancel a seed data generation job"""
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

@router.get("/download/{seed_id}")
@limiter.limit("20/minute")
async def download_seed_data(request: Request, seed_id: str):
    """Download generated seed data as ZIP archive"""
    try:
        # Get job result
        job = job_manager.get_job(seed_id)
        
        if not job or not job.result:
            raise HTTPException(
                status_code=404,
                detail=f"Seed generation {seed_id} not found or not completed"
            )
        
        # Get file paths from job result
        file_paths = job.result.get("file_paths", [])
        
        if not file_paths:
            raise HTTPException(
                status_code=404,
                detail="No files available for download"
            )
        
        # Create archive
        archive_name = f"seed_data_{seed_id}"
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

@router.get("/locales")
@limiter.limit("50/minute")
async def get_supported_locales(request: Request):
    """Get supported locales for data generation"""
    locales = {
        "en_US": "English (United States)",
        "en_GB": "English (United Kingdom)", 
        "es_ES": "Spanish (Spain)",
        "fr_FR": "French (France)",
        "de_DE": "German (Germany)",
        "it_IT": "Italian (Italy)",
        "pt_BR": "Portuguese (Brazil)",
        "ja_JP": "Japanese (Japan)",
        "ko_KR": "Korean (South Korea)",
        "zh_CN": "Chinese (Simplified)",
        "ru_RU": "Russian (Russia)",
        "ar_SA": "Arabic (Saudi Arabia)",
        "hi_IN": "Hindi (India)"
    }
    
    return {
        "supported_locales": locales,
        "default_locale": "en_US",
        "total_locales": len(locales)
    }

@router.get("/generators")
@limiter.limit("50/minute")
async def get_data_generators(request: Request):
    """Get available data generators and their configurations"""
    generators = {
        "personal": {
            "name": "Personal Information Generator",
            "fields": ["first_name", "last_name", "full_name", "email", "phone_number"],
            "description": "Generate realistic personal information"
        },
        "address": {
            "name": "Address Generator",
            "fields": ["street_address", "city", "state", "postal_code", "country"],
            "description": "Generate realistic addresses"
        },
        "company": {
            "name": "Company Information Generator", 
            "fields": ["company_name", "company_email", "job_title", "department"],
            "description": "Generate business-related information"
        },
        "financial": {
            "name": "Financial Data Generator",
            "fields": ["credit_card", "bank_account", "currency", "amount"],
            "description": "Generate financial and monetary data"
        },
        "datetime": {
            "name": "Date/Time Generator",
            "fields": ["date", "time", "datetime", "timestamp"],
            "description": "Generate various date and time formats"
        },
        "text": {
            "name": "Text Content Generator",
            "fields": ["sentence", "paragraph", "text", "word"],
            "description": "Generate text content of various lengths"
        },
        "internet": {
            "name": "Internet Data Generator",
            "fields": ["url", "domain", "username", "password", "ipv4", "ipv6"],
            "description": "Generate internet-related data"
        },
        "numeric": {
            "name": "Numeric Data Generator",
            "fields": ["integer", "float", "decimal", "percentage"],
            "description": "Generate various numeric data types"
        }
    }
    
    return {
        "generators": generators,
        "total_generators": len(generators)
    }

@router.post("/validate-config")
@limiter.limit("20/minute")
async def validate_seed_config(
    request: Request,
    schema_id: str,
    config: Dict[str, Any]
):
    """Validate seed data generation configuration"""
    try:
        # Get schema data
        schema_data = get_schema_by_id(schema_id)
        if not schema_data:
            raise HTTPException(
                status_code=404,
                detail=f"Schema {schema_id} not found"
            )
        
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Validate base_rows
        base_rows = config.get("base_rows", 10)
        if base_rows < 1:
            validation_results["errors"].append("base_rows must be at least 1")
            validation_results["valid"] = False
        elif base_rows > 10000:
            validation_results["warnings"].append("base_rows > 10000 may take a long time to generate")
        
        # Validate locale
        locale = config.get("locale", "en_US")
        supported_locales = ["en_US", "en_GB", "es_ES", "fr_FR", "de_DE", "it_IT", "pt_BR", "ja_JP", "ko_KR", "zh_CN", "ru_RU", "ar_SA", "hi_IN"]
        if locale not in supported_locales:
            validation_results["warnings"].append(f"Locale '{locale}' may not be fully supported")
        
        # Validate custom generators
        custom_generators = config.get("custom_generators", {})
        if custom_generators:
            for table_name, generators in custom_generators.items():
                if not isinstance(generators, dict):
                    validation_results["errors"].append(f"Custom generators for table '{table_name}' must be a dictionary")
                    validation_results["valid"] = False
        
        # Add recommendations
        if base_rows < 100:
            validation_results["recommendations"].append("Consider using at least 100 rows for better data variety")
        
        schema_tables = len([t for db in schema_data["schema"].get("databases", []) for t in db.get("tables", [])])
        if schema_tables > 10 and base_rows > 1000:
            validation_results["recommendations"].append("Large schemas with many rows may take significant time to generate")
        
        return validation_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Config validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Config validation failed: {str(e)}"
        )

@router.get("/stats")
@limiter.limit("50/minute")
async def get_seed_data_stats(request: Request):
    """Get seed data generation statistics"""
    try:
        # Get job statistics for seed generation
        job_stats = job_manager.get_job_stats()
        
        # Filter for seed generation jobs
        seed_jobs = job_manager.get_job_list(job_type=JobType.SEED_GENERATION, limit=1000)
        
        # Calculate seed-specific stats
        total_seed_jobs = len(seed_jobs)
        completed_seed_jobs = len([j for j in seed_jobs if j["status"] == "completed"])
        failed_seed_jobs = len([j for j in seed_jobs if j["status"] == "failed"])
        
        # Get file statistics
        seed_files = file_manager.list_files("seed_data", "*.csv", recursive=True)
        
        return {
            "job_statistics": {
                "total_seed_jobs": total_seed_jobs,
                "completed": completed_seed_jobs,
                "failed": failed_seed_jobs,
                "success_rate": (completed_seed_jobs / total_seed_jobs * 100) if total_seed_jobs > 0 else 0
            },
            "file_statistics": {
                "total_files": len(seed_files),
                "total_size": sum(f.get("size", 0) for f in seed_files),
                "recent_files": seed_files[:10]
            },
            "system_health": {
                "active_generations": len([j for j in seed_jobs if j["status"] == "running"]),
                "queue_size": job_stats.get("queue_size", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get seed data stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get seed data statistics: {str(e)}"
        )