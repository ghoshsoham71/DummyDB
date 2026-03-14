import logging
import pandas as pd
from typing import Dict, Any, Optional
from .job_service import job_manager, JobType
from .schema_store import get_schema_by_id
from ..utils.seeding_engine import SeedingEngine, ConstraintGraph
from ..utils.ml.models import ModelRegistry
from ..utils.arrow_utils import save_data_arrow

logger = logging.getLogger(__name__)

def register_synthetic_handler():
    """Register synthetic generation handlers (currently handled directly in job_service)."""
    pass

def synthetic_generation_handler(params: Dict[str, Any], cb=None) -> Dict[str, Any]:
    """Modernized handler using ML pipeline and Arrow."""
    try:
        schema_id = params["schema_id"]
        s_data = get_schema_by_id(schema_id)
        if not s_data: raise Exception("Schema not found")
        schema = s_data["schema"]
        
        # 1. Build Constraint Graph & Get Order
        if cb: cb(10, "Building constraint graph...")
        cg = ConstraintGraph(schema)
        order = cg.get_generation_order()
        
        # 2. LLM Seeding
        if cb: cb(20, "Generating seed rows via LLM (DSPy)...")
        seeder = SeedingEngine()
        seed_data = {}
        for t_name in order:
            cols = next(t for db in schema["databases"] for t in db["tables"] if t["name"] == t_name)["attributes"]
            seed_data[t_name] = seeder.generate_seed_rows(t_name, cols, 50)
            
        # 3. Bulk Scaling via Generative ML
        if cb: cb(50, "Scaling data via Generative ML...")
        registry = ModelRegistry()
        final_data = {}
        scale_factor = params.get("scale_factor", 2.0)
        
        for t_name, seeds in seed_data.items():
            if not seeds: continue
            df_seeds = pd.DataFrame(seeds)
            model_type = registry.select_best_model(df_seeds)
            model = registry.get_model(model_type)
            
            model.train(df_seeds)
            num_rows = int(len(seeds) * scale_factor)
            final_data[t_name] = model.generate(num_rows).to_dict('records')
            
        # 4. Save via Arrow
        if cb: cb(90, "Finalizing and saving via Apache Arrow...")
        out_dir = f"synthetic_data/{schema_id}"
        paths = save_data_arrow(final_data, out_dir, format=params.get("output_format", "csv"))
        
        # 5. Quality & Privacy Audit
        from src.utils.quality_engine import QualityEngine, PrivacyEngine
        audit_results = {}
        qe = QualityEngine()
        pe = PrivacyEngine()
        
        for t_name, rows in final_data.items():
            if t_name in seed_data:
                df_real = pd.DataFrame(seed_data[t_name])
                df_synth = pd.DataFrame(rows)
                audit_results[t_name] = {
                    "quality": qe.audit_quality(df_real, df_synth),
                    "privacy": pe.audit_privacy(df_real, df_synth)
                }
        
        if cb: cb(100, "Generation & Audit complete!")
        return {
            "success": True,
            "output_directory": out_dir,
            "file_paths": paths,
            "order": order,
            "audit": audit_results
        }
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise
