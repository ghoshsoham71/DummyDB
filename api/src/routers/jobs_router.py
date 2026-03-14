# api/src/routers/jobs_router.py

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from ..db.session import get_db
from ..services.job_service import job_manager
import asyncio
import json

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        return None
    return await job_manager.get_job(db, jid)

@router.websocket("/{job_id}/stream")
async def job_stream(websocket: WebSocket, job_id: str, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    try:
        jid = uuid.UUID(job_id)
        while True:
            job = await job_manager.get_job(db, jid)
            if job:
                await websocket.send_json({
                    "status": job.status.value,
                    "progress": job.progress,
                    "error_message": job.error_message
                })
                if job.status in ["completed", "failed", "cancelled"]:
                    break
            await asyncio.sleep(1) # Poll for updates
    except (WebSocketDisconnect, ValueError):
        pass
