import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import threading
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(str, Enum):
    SCHEMA_PARSE = "schema_parse"
    SEED_GENERATION = "seed_generation"
    SYNTHETIC_GENERATION = "synthetic_generation"
    DATA_EVALUATION = "data_evaluation"
    PIPELINE = "pipeline"
    BATCH_PROCESS = "batch_process"

@dataclass
class Job:
    """Job data structure"""
    job_id: str
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    message: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parent_job_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "message": self.message,
            "parameters": self.parameters,
            "result": self.result,
            "error": self.error,
            "parent_job_id": self.parent_job_id
        }

class JobManager:
    """Centralized job queue and task management"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.jobs: Dict[str, Job] = {}
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        self._lock = threading.Lock()
        
        # Job handlers registry
        self.job_handlers: Dict[JobType, Callable] = {}
        
    def register_handler(self, job_type: JobType, handler: Callable):
        """Register job handler function"""
        self.job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")
    
    def create_job(self, 
                  job_type: JobType, 
                  parameters: Dict[str, Any],
                  parent_job_id: Optional[str] = None) -> str:
        """Create a new job"""
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            job_type=job_type,
            parameters=parameters,
            parent_job_id=parent_job_id
        )
        
        with self._lock:
            self.jobs[job_id] = job
        
        logger.info(f"Created job {job_id} of type {job_type}")
        return job_id
    
    async def submit_job(self, 
                        job_type: JobType, 
                        parameters: Dict[str, Any],
                        parent_job_id: Optional[str] = None) -> str:
        """Submit job to queue"""
        job_id = self.create_job(job_type, parameters, parent_job_id)
        await self.job_queue.put(job_id)
        logger.info(f"Submitted job {job_id} to queue")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        with self._lock:
            return self.jobs.get(job_id)
    
    def update_job_status(self, 
                         job_id: str, 
                         status: JobStatus,
                         message: str = "",
                         progress: float = None,
                         result: Dict[str, Any] = None,
                         error: str = None):
        """Update job status"""
        with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = status
                job.message = message
                
                if progress is not None:
                    job.progress = min(100.0, max(0.0, progress))
                
                if result is not None:
                    job.result = result
                
                if error is not None:
                    job.error = error
                
                if status == JobStatus.RUNNING and job.started_at is None:
                    job.started_at = datetime.now(timezone.utc)
                
                if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    job.completed_at = datetime.now(timezone.utc)
                    if status == JobStatus.COMPLETED:
                        job.progress = 100.0
                
                logger.debug(f"Updated job {job_id}: {status} - {message}")
    
    async def process_jobs(self):
        """Process jobs from queue"""
        logger.info("Starting job processor")
        
        while self.running:
            try:
                # Wait for job with timeout
                job_id = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)
                
                job = self.get_job(job_id)
                if not job:
                    logger.error(f"Job {job_id} not found")
                    continue
                
                # Check if handler exists
                if job.job_type not in self.job_handlers:
                    self.update_job_status(
                        job_id, 
                        JobStatus.FAILED,
                        f"No handler registered for job type: {job.job_type}"
                    )
                    continue
                
                # Execute job in thread pool
                handler = self.job_handlers[job.job_type]
                loop = asyncio.get_event_loop()
                
                try:
                    self.update_job_status(job_id, JobStatus.RUNNING, "Job started")
                    
                    # Execute handler with progress callback
                    def progress_callback(progress: float, message: str = ""):
                        self.update_job_status(job_id, JobStatus.RUNNING, message, progress)
                    
                    result = await loop.run_in_executor(
                        self.executor, 
                        self._execute_job, 
                        handler, 
                        job.parameters, 
                        progress_callback
                    )
                    
                    self.update_job_status(
                        job_id, 
                        JobStatus.COMPLETED,
                        "Job completed successfully",
                        result=result
                    )
                    
                except Exception as e:
                    logger.error(f"Job {job_id} failed: {e}")
                    self.update_job_status(
                        job_id,
                        JobStatus.FAILED,
                        f"Job failed: {str(e)}",
                        error=str(e)
                    )
                
                finally:
                    self.job_queue.task_done()
                    
            except asyncio.TimeoutError:
                # No job in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error processing job queue: {e}")
    
    def _execute_job(self, handler: Callable, parameters: Dict[str, Any], progress_callback: Callable) -> Dict[str, Any]:
        """Execute job handler with progress tracking"""
        try:
            # Call handler with parameters and progress callback
            if 'progress_callback' in handler.__code__.co_varnames:
                return handler(parameters, progress_callback=progress_callback)
            else:
                return handler(parameters)
        except Exception as e:
            logger.error(f"Handler execution failed: {e}")
            raise
    
    def start(self):
        """Start job manager"""
        if self.running:
            logger.warning("Job manager already running")
            return
        
        self.running = True
        # Start background task for processing jobs
        asyncio.create_task(self.process_jobs())
        logger.info("Job manager started")
    
    def stop(self):
        """Stop job manager"""
        self.running = False
        self.executor.shutdown(wait=True)
        logger.info("Job manager stopped")
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = self.get_job(job_id)
        if not job:
            return False
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        self.update_job_status(job_id, JobStatus.CANCELLED, "Job cancelled by user")
        logger.info(f"Cancelled job {job_id}")
        return True
    
    def get_job_list(self, 
                    status: Optional[JobStatus] = None,
                    job_type: Optional[JobType] = None,
                    limit: int = 50,
                    offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of jobs with filters"""
        with self._lock:
            jobs = list(self.jobs.values())
        
        # Apply filters
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        if job_type:
            jobs = [job for job in jobs if job.job_type == job_type]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        paginated_jobs = jobs[offset:offset + limit]
        
        return [job.to_dict() for job in paginated_jobs]
    
    def get_job_stats(self) -> Dict[str, Any]:
        """Get job statistics"""
        with self._lock:
            jobs = list(self.jobs.values())
        
        stats = {
            "total_jobs": len(jobs),
            "pending": len([j for j in jobs if j.status == JobStatus.PENDING]),
            "running": len([j for j in jobs if j.status == JobStatus.RUNNING]),
            "completed": len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            "failed": len([j for j in jobs if j.status == JobStatus.FAILED]),
            "cancelled": len([j for j in jobs if j.status == JobStatus.CANCELLED]),
            "queue_size": self.job_queue.qsize() if hasattr(self.job_queue, 'qsize') else 0,
            "max_workers": self.max_workers,
            "is_running": self.running
        }
        
        # Add job type breakdown
        job_types = {}
        for job in jobs:
            job_type = job.job_type.value
            if job_type not in job_types:
                job_types[job_type] = {"total": 0, "completed": 0, "failed": 0}
            job_types[job_type]["total"] += 1
            if job.status == JobStatus.COMPLETED:
                job_types[job_type]["completed"] += 1
            elif job.status == JobStatus.FAILED:
                job_types[job_type]["failed"] += 1
        
        stats["job_types"] = job_types
        return stats
    
    def cleanup_old_jobs(self, max_age_hours: int = 168):  # 7 days default
        """Clean up old completed/failed jobs"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        with self._lock:
            old_jobs = [
                job_id for job_id, job in self.jobs.items()
                if job.completed_at and job.completed_at < cutoff_time
                and job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
            ]
            
            for job_id in old_jobs:
                del self.jobs[job_id]
        
        logger.info(f"Cleaned up {len(old_jobs)} old jobs")
        return len(old_jobs)

# Global job manager instance
job_manager = JobManager()