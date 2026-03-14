import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from src.lib.schemas import SeedDataResponse
from src.services.job_service import job_manager, JobType
from src.services.file_service import file_manager
from src.services.schema_store import get_schema_by_id
from .seed.constants import SUPPORTED_LOCALES, DATA_GENERATORS
from .seed.handler import seed_handler

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Seed Data"], prefix="/seed")
limiter = Limiter(key_func=get_remote_address)

class GenerateSeedRequest(BaseModel):
    schema_id: str; base_rows: int = 10; locale: str = "en_US"; custom_generators: Optional[dict] = None; output_format: str = "csv"

job_manager.register_handler(JobType.SEED_GENERATION, seed_handler)

@router.post("/generate", response_model=SeedDataResponse)
@limiter.limit("10/minute")
async def generate_seed_data(request: Request, req: GenerateSeedRequest):
    if not get_schema_by_id(req.schema_id): raise HTTPException(404, "Schema not found")
    jid = await job_manager.submit_job(JobType.SEED_GENERATION, {**req.dict(), "output_dir": f"seed_data/{req.schema_id}"})
    return SeedDataResponse(success=True, seed_id=jid, message=f"Job {jid} submitted")

@router.get("/jobs/{job_id}/status")
async def get_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job: raise HTTPException(404, "Not found")
    return {"job_id": job_id, "status": job.status.value, "progress": job.progress, "result": job.result, "error": job.error}

@router.get("/download/{seed_id}")
async def download_seed(seed_id: str):
    job = job_manager.get_job(seed_id)
    if not job or not job.result: raise HTTPException(404, "Not ready")
    paths = job.result.get("file_paths", [])
    if not paths: raise HTTPException(404, "No files")
    arc = file_manager.create_archive(paths, f"seed_{seed_id}")
    return FileResponse(arc, filename=f"seed_{seed_id}.zip", media_type="application/zip")

@router.get("/locales")
async def get_locales(): return {"supported_locales": SUPPORTED_LOCALES}

@router.get("/generators")
async def get_generators(): return {"generators": DATA_GENERATORS}