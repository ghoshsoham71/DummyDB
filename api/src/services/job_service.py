import asyncio
import logging
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor

from src.utils.jobs.models import Job, JobType, JobStatus

logger = logging.getLogger(__name__)

class JobManager:
    """Centralized job queue and task management"""
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.jobs: Dict[str, Job] = {}
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running, self._lock = False, threading.Lock()
        self.job_handlers: Dict[JobType, Callable] = {}
        
    def register_handler(self, job_type: JobType, handler: Callable):
        self.job_handlers[job_type] = handler
    
    def create_job(self, job_type: JobType, parameters: Dict[str, Any], parent_job_id: Optional[str] = None) -> str:
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id, job_type=job_type, parameters=parameters, parent_job_id=parent_job_id)
        with self._lock: self.jobs[job_id] = job
        return job_id
    
    async def submit_job(self, job_type: JobType, parameters: Dict[str, Any], parent_job_id: Optional[str] = None) -> str:
        job_id = self.create_job(job_type, parameters, parent_job_id)
        await self.job_queue.put(job_id)
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock: return self.jobs.get(job_id)
    
    def update_job_status(self, job_id: str, status: JobStatus, message: str = "", progress: Optional[float] = None, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        with self._lock:
            if job_id not in self.jobs: return
            job = self.jobs[job_id]
            job.status, job.message = status, message
            if progress is not None: job.progress = min(100.0, max(0.0, progress))
            if result is not None: job.result = result
            if error is not None: job.error = error
            if status == JobStatus.RUNNING and job.started_at is None: job.started_at = datetime.now(timezone.utc)
            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                job.completed_at = datetime.now(timezone.utc)
                if status == JobStatus.COMPLETED: job.progress = 100.0

    async def process_jobs(self):
        while self.running:
            try:
                job_id = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)
                job = self.get_job(job_id)
                if not job or job.job_type not in self.job_handlers:
                    self.update_job_status(job_id, JobStatus.FAILED, "No handler")
                    continue
                handler, loop = self.job_handlers[job.job_type], asyncio.get_event_loop()
                try:
                    self.update_job_status(job_id, JobStatus.RUNNING, "Started")
                    def cb(p: float, m: str = ""): self.update_job_status(job_id, JobStatus.RUNNING, m, p)
                    res = await loop.run_in_executor(self.executor, self._execute_job, handler, job.parameters, cb)
                    self.update_job_status(job_id, JobStatus.COMPLETED, "Success", result=res)
                except Exception as e:
                    self.update_job_status(job_id, JobStatus.FAILED, f"Failed: {e}", error=str(e))
                finally: self.job_queue.task_done()
            except asyncio.TimeoutError: continue
            except Exception as e: logger.error(f"Queue error: {e}")

    def _execute_job(self, handler, parameters, progress_callback) -> Dict[str, Any]:
        if 'progress_callback' in handler.__code__.co_varnames:
            return handler(parameters, progress_callback=progress_callback)
        return handler(parameters)

    def start(self):
        if self.running: return
        self.running = True
        asyncio.create_task(self.process_jobs())

    def stop(self):
        self.running = False
        self.executor.shutdown(wait=True)

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if not job or job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]: return False
        self.update_job_status(job_id, JobStatus.CANCELLED, "Cancelled")
        return True

    def get_job_list(self, status: Optional[JobStatus] = None, job_type: Optional[JobType] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with self._lock: jobs = list(self.jobs.values())
        if status: jobs = [j for j in jobs if j.status == status]
        if job_type: jobs = [j for j in jobs if j.job_type == job_type]
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return [j.to_dict() for j in jobs[offset:offset + limit]]

    def get_job_stats(self) -> Dict[str, Any]:
        with self._lock: jobs = list(self.jobs.values())
        return {"total": len(jobs), "pending": len([j for j in jobs if j.status == JobStatus.PENDING]), "running": len([j for j in jobs if j.status == JobStatus.RUNNING]), "completed": len([j for j in jobs if j.status == JobStatus.COMPLETED]), "failed": len([j for j in jobs if j.status == JobStatus.FAILED])}

    def cleanup_old_jobs(self, max_age_hours: int = 168):
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        with self._lock:
            old = [i for i, j in self.jobs.items() if j.completed_at and j.completed_at < cutoff]
            for i in old: self.jobs.pop(i)
        return len(old)

job_manager = JobManager()