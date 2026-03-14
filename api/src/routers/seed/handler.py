import logging
from pathlib import Path
from src.services.schema_store import get_schema_by_id

logger = logging.getLogger(__name__)

def seed_handler(params, progress=None):
    try:
        if progress: progress(10, "Loading schema...")
        schema = get_schema_by_id(params["schema_id"])
        if not schema: raise Exception("Schema not found")
        from src.utils.seed.generator import SeedDataGenerator
        gen = SeedDataGenerator(schema["schema"], params.get("locale", "en_US"))
        if progress: progress(40, "Generating...")
        dists = gen.generate_all_seed_data(params["output_dir"], params.get("base_rows", 10))
        if progress: progress(100, "Done!")
        p = Path(params["output_dir"])
        return {"success": True, "output_directory": params["output_dir"], "file_paths": [str(f) for f in p.glob("*.csv")] if p.exists() else [], "datasets_generated": len(dists)}
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        return {"success": False, "error": str(e)}
