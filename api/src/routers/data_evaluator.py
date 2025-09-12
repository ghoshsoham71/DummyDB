import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

from src.lib.schemas import (
    EvaluationRequest,
    EvaluationResponse,
    ErrorResponse
)
from src.utils.job_manager import job_manager, JobType
from src.utils.file_manager import file_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Data Quality Evaluation"], prefix="/evaluation")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

class EvaluateRequest(BaseModel):
    real_data_dir: str
    synthetic_data_dir: str
    evaluation_type: str = "comprehensive"
    output_report: Optional[str] = None

def data_evaluation_handler(parameters: Dict[str, Any], 
                           progress_callback=None) -> Dict[str, Any]:
    """Handler for data evaluation jobs"""
    try:
        if progress_callback:
            progress_callback(10, "Loading evaluation system...")
        
        # Import data evaluator
        from data_evaluator import DataQualityEvaluator
        
        # Initialize evaluator
        evaluator = DataQualityEvaluator()
        
        if progress_callback:
            progress_callback(20, "Loading datasets...")
        
        # Load datasets
        real_data_dir = parameters["real_data_dir"]
        synthetic_data_dir = parameters["synthetic_data_dir"]
        
        success = evaluator.load_datasets(real_data_dir, synthetic_data_dir)
        if not success:
            raise Exception("Failed to load datasets for evaluation")
        
        if progress_callback:
            progress_callback(40, "Running statistical tests...")
        
        # Run evaluation
        evaluation_results = evaluator.evaluate_all_tables()
        
        if progress_callback:
            progress_callback(80, "Generating report...")
        
        # Save evaluation report
        output_report = parameters.get("output_report", "evaluation_report.json")
        evaluator.save_evaluation_report(output_report)
        
        if progress_callback:
            progress_callback(100, "Evaluation complete!")
        
        # Extract summary information
        summary = evaluation_results.get("overall_summary", {})
        table_scores = {}
        
        for table_name, table_eval in evaluation_results.get("table_evaluations", {}).items():
            quality_score = table_eval.get("quality_score", {})
            overall_score = quality_score.get("overall_score")
            if overall_score is not None:
                table_scores[table_name] = overall_score
        
        return {
            "success": True,
            "evaluation_results": evaluation_results,
            "report_path": output_report,
            "overall_quality_score": summary.get("average_quality_score"),
            "table_scores": table_scores,
            "summary": summary,
            "evaluation_type": parameters.get("evaluation_type", "comprehensive")
        }
        
    except Exception as e:
        logger.error(f"Data evaluation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Register handler
job_manager.register_handler(JobType.DATA_EVALUATION, data_evaluation_handler)

@router.post("/evaluate", response_model=EvaluationResponse)
@limiter.limit("5/minute")
async def evaluate_data_quality(
    request: Request,
    evaluate_request: EvaluateRequest,
    background_tasks: BackgroundTasks
):
    """
    Evaluate synthetic data quality against real data
    
    This endpoint creates a background job to perform comprehensive
    quality evaluation of synthetic data.
    """
    try:
        logger.info(f"Starting data quality evaluation")
        
        # Validate directories exist
        real_path = Path(evaluate_request.real_data_dir)
        synthetic_path = Path(evaluate_request.synthetic_data_dir)
        
        if not real_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Real data directory not found: {evaluate_request.real_data_dir}"
            )
        
        if not synthetic_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Synthetic data directory not found: {evaluate_request.synthetic_data_dir}"
            )
        
        # Prepare job parameters
        job_params = {
            "real_data_dir": evaluate_request.real_data_dir,
            "synthetic_data_dir": evaluate_request.synthetic_data_dir,
            "evaluation_type": evaluate_request.evaluation_type,
            "output_report": evaluate_request.output_report or f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }
        
        # Submit job
        job_id = await job_manager.submit_job(
            JobType.DATA_EVALUATION,
            job_params
        )
        
        return EvaluationResponse(
            success=True,
            evaluation_id=job_id,
            message=f"Data evaluation job submitted with ID: {job_id}",
            processing_time=0.0,
            summary={"job_id": job_id, "evaluation_type": evaluate_request.evaluation_type}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit evaluation job: {e}")
        return EvaluationResponse(
            success=False,
            evaluation_id=None,
            message=f"Failed to submit evaluation job: {str(e)}",
            processing_time=0.0
        )

@router.get("/jobs/{job_id}/status")
@limiter.limit("50/minute")
async def get_evaluation_status(request: Request, job_id: str):
    """Get status of data evaluation job"""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    response_data = {
        "job_id": job_id,
        "status": job.status.value,
        "progress": job.progress,
        "message": job.message,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error
    }
    
    # Add evaluation-specific results if completed
    if job.result and job.status.value == "completed":
        response_data.update({
            "overall_quality_score": job.result.get("overall_quality_score"),
            "table_scores": job.result.get("table_scores", {}),
            "report_path": job.result.get("report_path"),
            "summary": job.result.get("summary", {})
        })
    
    return response_data

@router.get("/jobs")
@limiter.limit("50/minute")
async def list_evaluation_jobs(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List data evaluation jobs"""
    jobs = job_manager.get_job_list(
        job_type=JobType.DATA_EVALUATION,
        limit=limit,
        offset=offset
    )
    
    return {
        "jobs": jobs,
        "total_jobs": len(jobs),
        "limit": limit,
        "offset": offset
    }

@router.delete("/jobs/{job_id}")
@limiter.limit("10/minute")
async def cancel_evaluation_job(request: Request, job_id: str):
    """Cancel a data evaluation job"""
    success = job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or cannot be cancelled"
        )
    
    return {
        "message": f"Job {job_id} cancelled successfully",
        "job_id": job_id
    }

@router.get("/download/{evaluation_id}")
@limiter.limit("20/minute")
async def download_evaluation_report(request: Request, evaluation_id: str):
    """Download evaluation report"""
    try:
        # Get job result
        job = job_manager.get_job(evaluation_id)
        
        if not job or not job.result:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation {evaluation_id} not found or not completed"
            )
        
        # Get report path from job result
        report_path = job.result.get("report_path")
        
        if not report_path or not Path(report_path).exists():
            raise HTTPException(
                status_code=404,
                detail="Evaluation report not found"
            )
        
        return FileResponse(
            path=report_path,
            filename=f"evaluation_report_{evaluation_id}.json",
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download evaluation report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download report: {str(e)}"
        )

@router.get("/metrics")
@limiter.limit("50/minute")
async def get_evaluation_metrics(request: Request):
    """Get available evaluation metrics and their descriptions"""
    metrics = {
        "statistical_tests": {
            "kolmogorov_smirnov": {
                "name": "Kolmogorov-Smirnov Test",
                "description": "Tests if two samples come from the same distribution",
                "applies_to": "numerical_columns",
                "interpretation": "p-value > 0.05 indicates similar distributions"
            },
            "chi_square": {
                "name": "Chi-Square Test",
                "description": "Tests independence between categorical variables",
                "applies_to": "categorical_columns", 
                "interpretation": "p-value > 0.05 indicates similar distributions"
            },
            "anderson_darling": {
                "name": "Anderson-Darling Test",
                "description": "Tests if samples come from a specified distribution",
                "applies_to": "numerical_columns",
                "interpretation": "p-value > 0.05 indicates similar distributions"
            }
        },
        "correlation_analysis": {
            "correlation_preservation": {
                "name": "Correlation Preservation",
                "description": "Measures how well correlations are maintained",
                "range": "0.0 - 1.0",
                "interpretation": "Higher values indicate better correlation preservation"
            },
            "covariance_similarity": {
                "name": "Covariance Similarity",
                "description": "Measures similarity of covariance matrices",
                "range": "0.0 - 1.0",
                "interpretation": "Higher values indicate better covariance preservation"
            }
        },
        "statistical_similarity": {
            "mean_difference": {
                "name": "Mean Difference",
                "description": "Absolute difference between means",
                "range": "0.0 - infinity",
                "interpretation": "Lower values indicate better similarity"
            },
            "variance_ratio": {
                "name": "Variance Ratio",
                "description": "Ratio of variances between datasets",
                "range": "0.0 - infinity",
                "interpretation": "Values closer to 1.0 indicate better similarity"
            },
            "distribution_similarity": {
                "name": "Distribution Similarity",
                "description": "Overall similarity of distributions",
                "range": "0.0 - 1.0",
                "interpretation": "Higher values indicate better similarity"
            }
        },
        "privacy_metrics": {
            "k_anonymity": {
                "name": "K-Anonymity",
                "description": "Measures privacy preservation through anonymization",
                "range": "1 - infinity",
                "interpretation": "Higher values indicate better privacy protection"
            },
            "l_diversity": {
                "name": "L-Diversity",
                "description": "Measures diversity within equivalence classes",
                "range": "1 - infinity",
                "interpretation": "Higher values indicate better privacy protection"
            }
        },
        "utility_metrics": {
            "classification_accuracy": {
                "name": "Classification Accuracy",
                "description": "ML model performance on synthetic vs real data",
                "range": "0.0 - 1.0",
                "interpretation": "Values closer to 1.0 indicate better utility"
            },
            "regression_r2": {
                "name": "Regression R²",
                "description": "R² score for regression models",
                "range": "0.0 - 1.0",
                "interpretation": "Higher values indicate better utility"
            }
        }
    }
    
    return {
        "metrics": metrics,
        "total_categories": len(metrics),
        "total_metrics": sum(len(category) for category in metrics.values())
    }

@router.post("/compare")
@limiter.limit("10/minute")
async def compare_evaluations(
    request: Request,
    evaluation_ids: List[str]
):
    """Compare multiple evaluation results"""
    try:
        if len(evaluation_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 evaluation IDs are required for comparison"
            )
        
        comparisons = []
        
        for eval_id in evaluation_ids:
            job = job_manager.get_job(eval_id)
            
            if not job or not job.result or job.status.value != "completed":
                raise HTTPException(
                    status_code=404,
                    detail=f"Evaluation {eval_id} not found or not completed"
                )
            
            comparisons.append({
                "evaluation_id": eval_id,
                "overall_quality_score": job.result.get("overall_quality_score"),
                "table_scores": job.result.get("table_scores", {}),
                "evaluation_type": job.result.get("evaluation_type"),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            })
        
        # Calculate comparison metrics
        quality_scores = [comp.get("overall_quality_score") for comp in comparisons if comp.get("overall_quality_score")]
        
        comparison_summary = {
            "best_evaluation": max(comparisons, key=lambda x: x.get("overall_quality_score", 0)),
            "worst_evaluation": min(comparisons, key=lambda x: x.get("overall_quality_score", 0)),
            "average_quality": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            "quality_range": max(quality_scores) - min(quality_scores) if len(quality_scores) > 1 else 0
        }
        
        return {
            "comparisons": comparisons,
            "summary": comparison_summary,
            "total_evaluations": len(comparisons)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evaluation comparison failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation comparison failed: {str(e)}"
        )

@router.get("/health")
@limiter.limit("100/minute")
async def evaluation_health_check(request: Request):
    """Health check for evaluation system"""
    try:
        health_status = {
            "status": "healthy",
            "job_queue_size": len(job_manager.get_job_list(job_type=JobType.DATA_EVALUATION, limit=1000)),
            "active_evaluations": len([j for j in job_manager.get_job_list(job_type=JobType.DATA_EVALUATION, limit=100) if j["status"] == "running"]),
            "available_metrics": len([m for category in (await get_evaluation_metrics(request))["metrics"].values() for m in category]),
            "system_resources": {
                "disk_space_available": file_manager.get_available_disk_space(),
                "temp_files_count": len(file_manager.list_files("temp", "*", recursive=True))
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }