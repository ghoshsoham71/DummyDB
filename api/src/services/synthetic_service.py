import logging
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel
from src.services.job_service import job_manager, JobType
from src.services.schema_store import get_schema_by_id

logger = logging.getLogger(__name__)

class GenerateRequest(BaseModel):
    schema_id: str
    scale_factor: float = 2.0
    num_rows: Optional[Dict[str, int]] = None
    synthesizer_type: str = "HMA"
    output_format: str = "csv"
    seed: Optional[int] = None

def synthetic_generation_handler(params: Dict[str, Any], cb=None) -> Dict[str, Any]:
    """Handler for synthetic data generation jobs."""
    try:
        schema = _load_generate_schema(params, cb)
        out_dir = params.get("output_dir", f"synthetic_data/{params['schema_id']}")
        res_data = _run_mock_gen(schema, params, cb)
        from src.utils.mock_data_generator import save_mock_data_csv
        paths = save_mock_data_csv(res_data, out_dir)
        if cb: cb(100, "Complete!")
        return _format_synth_resp(res_data, out_dir, paths, params)
    except Exception as e:
        logger.error(f"Generation failed: {e}"); raise

def _load_generate_schema(params: dict, cb) -> dict:
    if cb: cb(10, "Loading schema...")
    s_data = get_schema_by_id(params["schema_id"])
    if not s_data: raise Exception("Schema not found")
    return s_data["schema"]

def _run_mock_gen(schema: dict, params: dict, cb) -> dict:
    s_id = params["schema_id"]
    s_dir = params.get("seed_data_dir", f"seed_data/{s_id}")
    has_seed = Path(s_dir).exists() and any(Path(s_dir).glob("*.csv"))
    if cb: cb(20, "Generating..." if not has_seed else "Using seeds...")
    from src.utils.mock_data_generator import generate_mock_data
    return generate_mock_data(schema=schema, num_rows=params.get("num_rows", {}), skip_rate_limit=has_seed)

def _format_synth_resp(data: dict, out_dir: str, paths: list, params: dict) -> dict:
    summary = {t: {"rows": len(r), "columns": len(r[0]) if r else 0} for t, r in data.items()}
    return {
        "success": True, "output_directory": out_dir, "file_paths": paths,
        "generation_summary": summary, "synthesizer_type": "groq-llm",
        "scale_factor": params.get("scale_factor", 2.0)
    }

def register_synthetic_handler():
    """Register the synthetic generation handler with job manager"""
    job_manager.register_handler(JobType.SYNTHETIC_GENERATION, synthetic_generation_handler)
