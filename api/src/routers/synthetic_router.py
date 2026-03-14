import logging
import uuid
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import FileResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from ..lib.schemas import SyntheticGenerationResponse, GenerateRequest
from ..services.job_service import job_manager, JobType
from ..services.file_service import file_manager
from ..services.schema_store import get_schema_by_id, PARSED_SCHEMAS
from ..db.session import get_db
from pathlib import Path
from ..lib.auth import get_current_user
# from ..services.synthetic_service import register_synthetic_handler # Commented out if not needed or broken
from .synthetic.templates import SYNTHETIC_TEMPLATES

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Synthetic Data"], prefix="/synthetic")
limiter = Limiter(key_func=get_remote_address)

@router.post("/generate", response_model=SyntheticGenerationResponse)
@limiter.limit("5/minute")
async def generate_synthetic(
    request: Request, 
    req: GenerateRequest, 
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    s = get_schema_by_id(req.schema_id)
    if not s or s.get("user_id") != user.id: 
        raise HTTPException(404, "Not found")
    
    jid = await job_manager.submit_job(
        db, 
        JobType.SYNTHETIC_GENERATION, 
        {**req.dict(), "seed_data_dir": "seed_data", "output_dir": f"synthetic_data/{req.schema_id}"},
        schema_id=req.schema_id
    )
    return SyntheticGenerationResponse(
        success=True, 
        generation_id=jid, 
        message=f"Job {jid} submitted", 
        statistics={"job_id": jid},
        processing_time=0.0
    )

@router.post("/generate/stream")
async def stream_synthetic(req: GenerateRequest, user=Depends(get_current_user)):
    s = get_schema_by_id(req.schema_id)
    if not s or s.get("user_id") != user.id: raise HTTPException(404, "Not found")
    from ..utils.mock_data_generator import generate_mock_data_streaming
    def stream():
        for ev in generate_mock_data_streaming(schema=s["schema"], num_rows=req.num_rows or {}, default_rows=10, output_dir=f"synthetic_data/{req.schema_id}"):
            yield f"data: {ev}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")

@router.get("/download/{schema_id}")
async def download_synthetic(schema_id: str, user=Depends(get_current_user)):
    # Note: user.id check might need adjustment if user Object doesn't have .id
    # Assuming user is a dict or object from get_current_user
    d = Path(f"synthetic_data/{schema_id}")
    csvs = list(d.glob("*.csv"))
    if not csvs: raise HTTPException(404, "No data")
    arc = file_manager.create_archive([str(f) for f in csvs], f"synthetic_{schema_id}")
    return FileResponse(arc, filename=f"synthetic_{schema_id}.zip", media_type="application/zip")

@router.get("/jobs/{job_id}/status")
async def get_status(job_id: str, db: AsyncSession = Depends(get_db)):
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(400, "Invalid job ID")
        
    j = await job_manager.get_job(db, jid)
    if not j: raise HTTPException(404, "Not found")
    return {
        "job_id": job_id, 
        "status": j.status.value, 
        "progress": j.progress, 
        "result": j.result_metadata
    }

@router.get("/templates")
async def get_templates(): 
    return {"templates": SYNTHETIC_TEMPLATES}