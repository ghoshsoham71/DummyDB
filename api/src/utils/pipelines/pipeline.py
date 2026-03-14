import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from .job_manager import job_manager, JobStatus
from .pipeline_step import PipelineStep

logger = logging.getLogger(__name__)

class DataPipeline:
    """Data processing pipeline orchestrator"""
    def __init__(self, pipeline_id: str, name: str):
        self.pipeline_id = pipeline_id
        self.name = name
        self.steps: Dict[str, PipelineStep] = {}
        self.step_order: List[str] = []
        self.results: Dict[str, Any] = {}
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
    
    def add_step(self, step: PipelineStep):
        self.steps[step.name] = step
        self._update_step_order()
    
    def _update_step_order(self):
        visited, temp_visited, order = set(), set(), []
        def visit(name: str):
            if name in temp_visited: raise ValueError(f"Circular dependency: {name}")
            if name in visited: return
            temp_visited.add(name)
            for dep in self.steps[name].depends_on:
                if dep in self.steps: visit(dep)
            temp_visited.remove(name)
            visited.add(name)
            order.append(name)
        for name in self.steps.keys():
            if name not in visited: visit(name)
        self.step_order = order
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        self.status, self.started_at = JobStatus.RUNNING, datetime.now()
        try:
            for name in self.step_order:
                step = self.steps[name]
                params = {**parameters, **self.results}
                job_id = await job_manager.submit_job(step.job_type, params, parent_job_id=self.pipeline_id)
                res = await self._wait_for_job(job_id)
                if res["status"] == JobStatus.FAILED:
                    raise Exception(f"Step {name} failed: {res.get('error')}")
                self.results[name] = res.get("result", {})
            self.status, self.completed_at = JobStatus.COMPLETED, datetime.now()
            return {"status": "success", "results": self.results, "processing_time": (self.completed_at - self.started_at).total_seconds()}
        except Exception as e:
            self.status, self.completed_at, self.error_message = JobStatus.FAILED, datetime.now(), str(e)
            return {"status": "failed", "error": str(e), "results": self.results}
    
    async def _wait_for_job(self, job_id: str, timeout: int = 3600) -> Dict[str, Any]:
        start = datetime.now()
        while (datetime.now() - start).total_seconds() < timeout:
            job = job_manager.get_job(job_id)
            if not job: raise Exception(f"Job {job_id} not found")
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return {"status": job.status, "result": job.result, "error": job.error}
            await asyncio.sleep(1)
        raise Exception(f"Job {job_id} timed out")
