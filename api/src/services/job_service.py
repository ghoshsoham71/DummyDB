# api/src/services/job_service.py

import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import GenerationJob, JobStatus, JobType
from ..utils.jobs.broker import job_broker
from sqlalchemy import select

class JobService:
    async def create_job(
        self,
        db: AsyncSession, 
        schema_id: str, 
        job_type: JobType, 
        parameters: Dict[str, Any]
    ) -> GenerationJob:
        job = GenerationJob(
            schema_id=schema_id,
            job_type=job_type,
            parameters=parameters,
            status=JobStatus.PENDING
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Enqueue for worker
        await job_broker.enqueue_job(str(job.id), job_type.value, parameters)
        
        return job

    async def get_job(self, db: AsyncSession, job_id: uuid.UUID) -> Optional[GenerationJob]:
        result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
        return result.scalars().first()

    async def update_job_status(self, db: AsyncSession, job_id: uuid.UUID, status: JobStatus, progress: Optional[float] = None, error: Optional[str] = None):
        job = await self.get_job(db, job_id)
        if job:
            job.status = status
            if progress is not None:
                job.progress = progress
            if error:
                job.error_message = error
            await db.commit()

    async def submit_job(self, db: AsyncSession, job_type: JobType, parameters: Dict[str, Any], schema_id: Optional[str] = None) -> str:
        """Submit a job and return its ID."""
        if schema_id is None:
            # Try to get schema_id from parameters if possible
            sid = parameters.get("schema_id")
            if isinstance(sid, str):
                schema_id = sid
            else:
                # Fallback to a random UUID string if absolutely necessary
                schema_id = str(uuid.uuid4())
        
        job = await self.create_job(db, schema_id, job_type, parameters)
        return str(job.id)

job_manager = JobService()