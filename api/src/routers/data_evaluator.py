import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.lib.schemas import EvaluationResponse
from src.utils.job_manager import job_manager, JobType
from src.services.evaluation_service import EvaluateRequest, register_evaluation_handler

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Evaluation"], prefix="/evaluation")
limiter = Limiter(key_func=get_remote_address)
register_evaluation_handler()

@router.post("/evaluate", response_model=EvaluationResponse)
@limiter.limit("5/minute")
async def evaluate(request: Request, req: EvaluateRequest):
    if not Path(req.real_data_dir).exists() or not Path(req.synthetic_data_dir).exists():
        raise HTTPException(404, "Data directory not found")
    jid = await job_manager.submit_job(JobType.DATA_EVALUATION, {**req.dict(), "output_report": req.output_report or f"eval_{datetime.now().strftime('%Y%m%d_%H')}.json"})
    return EvaluationResponse(success=True, evaluation_id=jid, message=f"Job {jid} submitted")

@router.get("/jobs/{job_id}/status")
async def get_status(job_id: str):
    j = job_manager.get_job(job_id)
    if not j: raise HTTPException(404, "Not found")
    res = {"job_id": job_id, "status": j.status.value, "progress": j.progress, "message": j.message}
    if j.result and j.status.value == "completed": res.update(j.result)
    return res

@router.get("/download/{evaluation_id}")
async def download_report(evaluation_id: str):
    j = job_manager.get_job(evaluation_id)
    if not j or not j.result: raise HTTPException(404, "Not found")
    p = j.result.get("report_path")
    if not p or not Path(p).exists(): raise HTTPException(404, "File not found")
    return FileResponse(p, filename=f"eval_{evaluation_id}.json", media_type="application/json")