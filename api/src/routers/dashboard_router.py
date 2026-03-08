"""
Dashboard Router
Aggregated analytics and activity endpoints for the DummyDB dashboard.
"""
import logging
import time
from typing import Dict, Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.utils.job_manager import job_manager, JobType
from src.utils.file_manager import file_manager

# Re-use the in-memory schema store from schema_parse_router
from src.routers.schema_parse_router import PARSED_SCHEMAS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"], prefix="/dashboard")

limiter = Limiter(key_func=get_remote_address)


@router.get("/overview")
@limiter.limit("60/minute")
async def dashboard_overview(request: Request):
    """Aggregated dashboard overview with schema, job, and storage stats."""
    try:
        # --- Schema stats ---
        total_schemas = len(PARSED_SCHEMAS)
        sources: Dict[str, int] = {}
        total_tables = 0
        for _sid, sdata in PARSED_SCHEMAS.items():
            src = (sdata.get("metadata") or {}).get("source", "sql_upload")
            sources[src] = sources.get(src, 0) + 1
            schema_obj = sdata.get("schema", {})
            for db in schema_obj.get("databases", []):
                total_tables += len(db.get("tables", []))

        # --- Job stats ---
        job_stats = job_manager.get_job_stats()

        # --- Storage stats ---
        try:
            storage_stats = file_manager.get_storage_stats()
        except Exception:
            storage_stats = {}

        synthetic_files: list[Dict[str, Any]] = []
        try:
            synthetic_files = file_manager.list_files("synthetic_data", "*.csv", recursive=True)
        except Exception:
            pass

        return {
            "schemas": {
                "total": total_schemas,
                "total_tables": total_tables,
                "by_source": sources,
            },
            "jobs": job_stats,
            "storage": storage_stats,
            "synthetic_files": {
                "total": len(synthetic_files),
                "total_size": sum(f.get("size", 0) for f in synthetic_files),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Dashboard overview failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.get("/activity")
@limiter.limit("60/minute")
async def dashboard_activity(request: Request, limit: int = 20):
    """Recent activity timeline across schemas and jobs."""
    events: List[Dict[str, Any]] = []

    # Schema creation events
    for sid, sdata in PARSED_SCHEMAS.items():
        created = sdata.get("created_at")
        source = (sdata.get("metadata") or {}).get("source", "sql_upload")
        events.append({
            "type": "schema_parsed",
            "id": sid,
            "source": source,
            "filename": sdata.get("filename", ""),
            "timestamp": created,
        })

    # Job events
    try:
        jobs_list = job_manager.get_job_list(limit=100)
        for j in jobs_list:
            events.append({
                "type": f"job_{j.get('status', 'unknown')}",
                "id": j.get("job_id", ""),
                "source": "synthetic_generation",
                "timestamp": j.get("created_at"),
                "message": j.get("message", ""),
            })
    except Exception:
        pass

    # Sort newest first and limit
    events.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
    events = events[:limit]

    return {"events": events, "total": len(events)}


@router.get("/schema-stats")
@limiter.limit("60/minute")
async def dashboard_schema_stats(request: Request):
    """Detailed schema-level analytics."""
    schemas_info: List[Dict[str, Any]] = []

    for sid, sdata in PARSED_SCHEMAS.items():
        schema_obj = sdata.get("schema", {})
        databases = schema_obj.get("databases", [])
        table_count = sum(len(db.get("tables", [])) for db in databases)
        column_count = sum(
            len(t.get("attributes", []))
            for db in databases for t in db.get("tables", [])
        )

        constraint_counts: Dict[str, int] = {}
        for db in databases:
            for t in db.get("tables", []):
                for attr in t.get("attributes", []):
                    for c in attr.get("constraints", []):
                        constraint_counts[c] = constraint_counts.get(c, 0) + 1

        source = (sdata.get("metadata") or {}).get("source", "sql_upload")

        schemas_info.append({
            "schema_id": sid,
            "filename": sdata.get("filename", ""),
            "source": source,
            "database_count": len(databases),
            "table_count": table_count,
            "column_count": column_count,
            "constraints": constraint_counts,
            "file_size": sdata.get("file_size", 0),
            "created_at": sdata.get("created_at"),
        })

    # Distribution stats
    table_counts = [s["table_count"] for s in schemas_info]
    return {
        "schemas": schemas_info,
        "total_schemas": len(schemas_info),
        "distribution": {
            "avg_tables": sum(table_counts) / max(len(table_counts), 1),
            "max_tables": max(table_counts, default=0),
            "min_tables": min(table_counts, default=0),
        },
    }
