import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.services.schema_store import PARSED_SCHEMAS, schema_manager
from src.lib.database import insert_schema

logger = logging.getLogger(__name__)

def compute_stats(schema: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    dbs = schema.get("databases", [])
    stats = {
        "databases": len(dbs),
        "tables": sum(len(db.get("tables", [])) for db in dbs),
        "columns": sum(len(t.get("attributes", [])) for db in dbs for t in db.get("tables", []))
    }
    if extra: stats.update(extra)
    return stats

def store_schema(schema: Dict[str, Any], schema_id: str, content_hash: str, filename: str, content_bytes: bytes, source: str, save_to_disk: bool, extra_m: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> Optional[str]:
    schema_manager.cleanup_old_schemas()
    data = {
        "schema": schema, "filename": filename, "created_at": time.time(), "file_size": len(content_bytes),
        "content_hash": content_hash, "user_id": user_id,
        "metadata": {"upload_timestamp": datetime.now(timezone.utc).isoformat(), "source": source, **(extra_m or {})}
    }
    path = None
    if save_to_disk:
        d = Path("./schemas")
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"schema_{content_hash}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False, default=str)
            data["file_path"] = str(path)
        except Exception as e: logger.warning(f"Disk save failed: {e}")
    PARSED_SCHEMAS[schema_id] = data
    try: insert_schema(schema_data=schema, filename=filename, content_hash=content_hash, file_size=len(content_bytes))
    except Exception as e: logger.error(f"DB failed: {e}")
    return str(path) if path else None
