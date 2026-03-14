from typing import List, Callable
from .job_manager import JobType

class PipelineStep:
    """Represents a single step in a data pipeline"""
    def __init__(self, name: str, job_type: JobType, handler: Callable, depends_on: List[str] = None):
        self.name = name
        self.job_type = job_type
        self.handler = handler
        self.depends_on = depends_on or []
