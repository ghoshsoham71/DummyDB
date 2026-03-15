# api/src/services/job_service.py

import uuid
from typing import Dict, Any, Optional, List
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

    async def get_job_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get aggregate job statistics from the database."""
        from sqlalchemy import func
        
        # Count total jobs
        total_stmt = select(func.count(GenerationJob.id))
        total_result = await db.execute(total_stmt)
        total_count = total_result.scalar() or 0
        
        # Count by status
        status_stmt = select(GenerationJob.status, func.count(GenerationJob.id)).group_by(GenerationJob.status)
        status_result = await db.execute(status_stmt)
        by_status = {status.value: count for status, count in status_result.all()}
        
        # Calculate success rate
        completed = by_status.get(JobStatus.COMPLETED, 0)
        failed = by_status.get(JobStatus.FAILED, 0)
        total_finished = completed + failed
        success_rate = (completed / total_finished * 100) if total_finished > 0 else 100.0
        
        return {
            "total": total_count,
            "by_status": by_status,
            "success_rate": round(success_rate, 2),
            "active": by_status.get(JobStatus.RUNNING, 0) + by_status.get(JobStatus.PENDING, 0)
        }

    async def get_job_list(self, db: AsyncSession, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List recent jobs with a limit and offset."""
        stmt = select(GenerationJob).order_by(GenerationJob.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        jobs = result.scalars().all()
        
        return [
            {
                "job_id": str(j.id),
                "schema_id": j.schema_id,
                "type": j.job_type.value,
                "status": j.status.value,
                "progress": j.progress,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
                "message": j.error_message or "",
            }
            for j in jobs
        ]

job_manager = JobService()