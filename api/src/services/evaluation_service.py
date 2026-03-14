import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from .job_service import job_manager, JobType

logger = logging.getLogger(__name__)

class EvaluateRequest(BaseModel):
    real_data_dir: str
    synthetic_data_dir: str
    evaluation_type: str = "comprehensive"
    output_report: Optional[str] = None

def data_evaluation_handler(params: Dict[str, Any], cb=None) -> Dict[str, Any]:
    """Handler for data evaluation jobs"""
    try:
        report_name = params.get("output_report", f"eval_{datetime.now().strftime('%Y%m%d_%H')}.json")
        res = _run_eval_job(params, report_name, cb)
        return _format_eval_resp(res, report_name, params)
    except Exception as e:
        logger.error(f"Eval failed: {e}")
        return {"success": False, "error": str(e)}

def _run_eval_job(params: dict, report: str, cb) -> dict:
    if cb: cb(10, "Loading...")
    from src.utils.evaluation.evaluator import DataQualityEvaluator
    ev = DataQualityEvaluator()
    if cb: cb(20, "Loading data...")
    if not ev.load_datasets(params["real_data_dir"], params["synthetic_data_dir"]):
        raise Exception("Load failed")
    if cb: cb(40, "Testing...")
    res = ev.evaluate_all_tables()
    if cb: cb(80, "Saving...")
    ev.save_evaluation_report(report)
    if cb: cb(100, "Done")
    return res

def _format_eval_resp(res: dict, report: str, params: dict) -> dict:
    sum_info = res.get("overall_summary", {})
    scores = {t: e.get("quality_score", {}).get("overall_score") for t, e in res.get("table_evaluations", {}).items() if e.get("quality_score", {}).get("overall_score") is not None}
    return {
        "success": True, "evaluation_results": res, "report_path": report,
        "overall_quality_score": sum_info.get("average_quality_score"),
        "table_scores": scores, "summary": sum_info,
        "evaluation_type": params.get("evaluation_type", "comprehensive")
    }

def register_evaluation_handler():
    """Register the data evaluation handler with job manager"""
    job_manager.register_handler(JobType.DATA_EVALUATION, data_evaluation_handler)
