import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import json
import asyncio

from .job_manager import job_manager, JobType, JobStatus
from .file_manager import file_manager

logger = logging.getLogger(__name__)

class PipelineStep:
    """Represents a single step in a data pipeline"""
    
    def __init__(self, 
                 name: str, 
                 job_type: JobType, 
                 handler: Callable,
                 depends_on: List[str] = None):
        self.name = name
        self.job_type = job_type
        self.handler = handler
        self.depends_on = depends_on or []

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
        """Add a step to the pipeline"""
        self.steps[step.name] = step
        self._update_step_order()
    
    def _update_step_order(self):
        """Update step execution order based on dependencies"""
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(step_name: str):
            if step_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving step: {step_name}")
            if step_name in visited:
                return
            
            temp_visited.add(step_name)
            step = self.steps[step_name]
            
            for dependency in step.depends_on:
                if dependency in self.steps:
                    visit(dependency)
            
            temp_visited.remove(step_name)
            visited.add(step_name)
            order.append(step_name)
        
        for step_name in self.steps.keys():
            if step_name not in visited:
                visit(step_name)
        
        self.step_order = order
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete pipeline"""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now()
        
        try:
            logger.info(f"Starting pipeline execution: {self.name} ({self.pipeline_id})")
            
            for step_name in self.step_order:
                step = self.steps[step_name]
                logger.info(f"Executing step: {step_name}")
                
                # Prepare step parameters
                step_params = parameters.copy()
                step_params.update(self.results)  # Include results from previous steps
                
                # Submit job for this step
                job_id = await job_manager.submit_job(
                    step.job_type,
                    step_params,
                    parent_job_id=self.pipeline_id
                )
                
                # Wait for job completion
                result = await self._wait_for_job(job_id)
                
                if result["status"] == JobStatus.FAILED:
                    raise Exception(f"Step {step_name} failed: {result.get('error', 'Unknown error')}")
                
                # Store step result
                self.results[step_name] = result.get("result", {})
                logger.info(f"Step {step_name} completed successfully")
            
            self.status = JobStatus.COMPLETED
            self.completed_at = datetime.now()
            
            logger.info(f"Pipeline {self.name} completed successfully")
            return {
                "status": "success",
                "results": self.results,
                "processing_time": (self.completed_at - self.started_at).total_seconds()
            }
            
        except Exception as e:
            self.status = JobStatus.FAILED
            self.completed_at = datetime.now()
            self.error_message = str(e)
            
            logger.error(f"Pipeline {self.name} failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "results": self.results
            }
    
    async def _wait_for_job(self, job_id: str, timeout: int = 3600) -> Dict[str, Any]:
        """Wait for a job to complete"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            job = job_manager.get_job(job_id)
            
            if not job:
                raise Exception(f"Job {job_id} not found")
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return {
                    "status": job.status,
                    "result": job.result,
                    "error": job.error
                }
            
            await asyncio.sleep(1)  # Poll every second
        
        raise Exception(f"Job {job_id} timed out after {timeout} seconds")

class PipelineManager:
    """Manages data processing pipelines"""
    
    def __init__(self):
        self.pipelines: Dict[str, DataPipeline] = {}
        self.templates: Dict[str, Dict[str, Any]] = {}
        self._register_default_templates()
    
    def _register_default_templates(self):
        """Register default pipeline templates"""
        # Complete data generation pipeline
        self.templates["complete_generation"] = {
            "name": "Complete Data Generation Pipeline",
            "description": "Full pipeline: seed generation -> synthetic generation -> evaluation",
            "steps": [
                {
                    "name": "seed_generation",
                    "job_type": JobType.SEED_GENERATION,
                    "depends_on": []
                },
                {
                    "name": "synthetic_generation",
                    "job_type": JobType.SYNTHETIC_GENERATION,
                    "depends_on": ["seed_generation"]
                },
                {
                    "name": "evaluation",
                    "job_type": JobType.DATA_EVALUATION,
                    "depends_on": ["synthetic_generation"]
                }
            ]
        }
        
        # Quick generation pipeline
        self.templates["quick_generation"] = {
            "name": "Quick Synthetic Generation",
            "description": "Fast pipeline: seed generation -> synthetic generation",
            "steps": [
                {
                    "name": "seed_generation",
                    "job_type": JobType.SEED_GENERATION,
                    "depends_on": []
                },
                {
                    "name": "synthetic_generation",
                    "job_type": JobType.SYNTHETIC_GENERATION,
                    "depends_on": ["seed_generation"]
                }
            ]
        }
        
        # Evaluation only pipeline
        self.templates["evaluation_only"] = {
            "name": "Data Quality Evaluation",
            "description": "Evaluate existing real and synthetic data",
            "steps": [
                {
                    "name": "evaluation",
                    "job_type": JobType.DATA_EVALUATION,
                    "depends_on": []
                }
            ]
        }
    
    def create_pipeline_from_template(self, 
                                    template_name: str,
                                    pipeline_name: Optional[str] = None) -> str:
        """Create pipeline from template"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        pipeline_id = str(uuid.uuid4())
        name = pipeline_name or template["name"]
        
        pipeline = DataPipeline(pipeline_id, name)
        
        # Add steps from template
        for step_config in template["steps"]:
            # Get handler for job type (would need to be registered)
            handler = self._get_job_handler(JobType(step_config["job_type"]))
            
            step = PipelineStep(
                name=step_config["name"],
                job_type=JobType(step_config["job_type"]),
                handler=handler,
                depends_on=step_config.get("depends_on", [])
            )
            pipeline.add_step(step)
        
        self.pipelines[pipeline_id] = pipeline
        logger.info(f"Created pipeline '{name}' from template '{template_name}' with ID: {pipeline_id}")
        
        return pipeline_id
    
    def _get_job_handler(self, job_type: JobType) -> Callable:
        """Get job handler for job type"""
        # This would return the appropriate handler function
        # For now, return a placeholder
        handlers = {
            JobType.SEED_GENERATION: self._seed_generation_handler,
            JobType.SYNTHETIC_GENERATION: self._synthetic_generation_handler,
            JobType.DATA_EVALUATION: self._evaluation_handler
        }
        return handlers.get(job_type, self._default_handler)
    
    def _seed_generation_handler(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for seed data generation"""
        # Import here to avoid circular imports
        from seed_data_generator import create_seed_data_from_schema
        
        schema_path = parameters.get("schema_path")
        output_dir = parameters.get("output_dir", "seed_data")
        base_rows = parameters.get("base_rows", 10)
        
        success = create_seed_data_from_schema(schema_path, output_dir, base_rows)
        
        return {
            "success": success,
            "output_directory": output_dir,
            "base_rows": base_rows
        }
    
    def _synthetic_generation_handler(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for synthetic data generation"""
        # Import here to avoid circular imports
        from sdv_synthetic_generator import generate_synthetic_data_from_schema
        
        schema_path = parameters.get("schema_path")
        seed_data_dir = parameters.get("seed_data_dir", "seed_data")
        output_dir = parameters.get("output_dir", "synthetic_data")
        scale = parameters.get("scale", 2.0)
        synthesizer_type = parameters.get("synthesizer_type", "HMA")
        
        success = generate_synthetic_data_from_schema(
            schema_path, seed_data_dir, output_dir, scale, synthesizer_type
        )
        
        return {
            "success": success,
            "output_directory": output_dir,
            "scale_factor": scale,
            "synthesizer_type": synthesizer_type
        }
    
    def _evaluation_handler(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for data evaluation"""
        # Import here to avoid circular imports
        from data_evaluator import evaluate_synthetic_data_quality
        
        real_data_dir = parameters.get("real_data_dir", "seed_data")
        synthetic_data_dir = parameters.get("synthetic_data_dir", "synthetic_data")
        output_report = parameters.get("output_report", "evaluation_report.json")
        
        success = evaluate_synthetic_data_quality(real_data_dir, synthetic_data_dir, output_report)
        
        return {
            "success": success,
            "report_path": output_report,
            "real_data_dir": real_data_dir,
            "synthetic_data_dir": synthetic_data_dir
        }
    
    def _default_handler(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Default handler for unknown job types"""
        return {"success": False, "error": "No handler available"}
    
    async def execute_pipeline(self, 
                              pipeline_id: str, 
                              parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a pipeline"""
        if pipeline_id not in self.pipelines:
            raise ValueError(f"Pipeline '{pipeline_id}' not found")
        
        pipeline = self.pipelines[pipeline_id]
        result = await pipeline.execute(parameters)
        
        # Save pipeline result
        self._save_pipeline_result(pipeline_id, result)
        
        return result
    
    def _save_pipeline_result(self, pipeline_id: str, result: Dict[str, Any]):
        """Save pipeline execution result"""
        try:
            result_file = file_manager.reports_dir / f"pipeline_{pipeline_id}_result.json"
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "pipeline_id": pipeline_id,
                    "executed_at": datetime.now().isoformat(),
                    "result": result
                }, f, indent=2)
            
            logger.info(f"Pipeline result saved: {result_file}")
            
        except Exception as e:
            logger.error(f"Failed to save pipeline result: {e}")
    
    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get pipeline status"""
        if pipeline_id not in self.pipelines:
            return {"error": f"Pipeline '{pipeline_id}' not found"}
        
        pipeline = self.pipelines[pipeline_id]
        
        return {
            "pipeline_id": pipeline_id,
            "name": pipeline.name,
            "status": pipeline.status.value,
            "created_at": pipeline.created_at.isoformat(),
            "started_at": pipeline.started_at.isoformat() if pipeline.started_at else None,
            "completed_at": pipeline.completed_at.isoformat() if pipeline.completed_at else None,
            "steps": list(pipeline.steps.keys()),
            "results": pipeline.results,
            "error_message": pipeline.error_message
        }
    
    def list_pipelines(self) -> List[Dict[str, Any]]:
        """List all pipelines"""
        pipelines = []
        
        for pipeline_id, pipeline in self.pipelines.items():
            pipelines.append({
                "pipeline_id": pipeline_id,
                "name": pipeline.name,
                "status": pipeline.status.value,
                "created_at": pipeline.created_at.isoformat(),
                "step_count": len(pipeline.steps)
            })
        
        return sorted(pipelines, key=lambda x: x["created_at"], reverse=True)
    
    def get_templates(self) -> Dict[str, Any]:
        """Get available pipeline templates"""
        return self.templates
    
    def add_template(self, name: str, template: Dict[str, Any]):
        """Add custom pipeline template"""
        self.templates[name] = template
        logger.info(f"Added pipeline template: {name}")

# Global pipeline manager instance
pipeline_manager = PipelineManager()