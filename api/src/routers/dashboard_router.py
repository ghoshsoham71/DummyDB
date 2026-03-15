"""
Dashboard Router
Aggregated analytics and activity endpoints for the BurstDB dashboard.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..services.job_service import job_manager
from ..services.file_service import file_manager
from ..services.schema_store import get_user_schemas
from ..lib.auth import get_current_user
from ..db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"], prefix="/dashboard")

limiter = Limiter(key_func=get_remote_address)


@router.get("/overview")
@limiter.limit("60/minute")
async def dashboard_overview(
    request: Request, 
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Aggregated dashboard overview with schema, job, and storage stats (user-scoped)."""
    try:
        # --- Schema stats (user-scoped) ---
        user_schemas = get_user_schemas(user.id)
        total_schemas = len(user_schemas)
        sources: Dict[str, int] = {}
        total_tables = 0
        for _sid, sdata in user_schemas.items():
            src = (sdata.get("metadata") or {}).get("source", "sql_upload")
            sources[src] = sources.get(src, 0) + 1
            schema_obj = sdata.get("schema", {})
            for db_obj in schema_obj.get("databases", []):
                total_tables += len(db_obj.get("tables", []))

        # --- Job stats (await the async call) ---
        job_stats = await job_manager.get_job_stats(db)

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
async def dashboard_activity(
    request: Request, 
    limit: int = 20, 
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Recent activity timeline across schemas and jobs (user-scoped)."""
    events: List[Dict[str, Any]] = []

    # Schema creation events (user-scoped)
    user_schemas = get_user_schemas(user.id)
    for sid, sdata in user_schemas.items():
        created = sdata.get("created_at")
        source = (sdata.get("metadata") or {}).get("source", "sql_upload")
        events.append({
            "type": "schema_parsed",
            "id": sid,
            "source": source,
            "filename": sdata.get("filename", ""),
            "timestamp": created,
        })

    # Job events (await the async call)
    try:
        jobs_list = await job_manager.get_job_list(db, limit=100)
        for j in jobs_list:
            events.append({
                "type": f"job_{j.get('status', 'unknown')}",
                "id": j.get("job_id", ""),
                "source": "synthetic_generation",
                "timestamp": j.get("created_at"),
                "message": j.get("message", ""),
            })
    except Exception as e:
        logger.error(f"Failed to fetch jobs for activity: {e}")
        pass

    # Sort newest first and limit
    events.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
    events = events[:limit]

    return {"events": events, "total": len(events)}


@router.get("/schema-stats")
@limiter.limit("60/minute")
async def dashboard_schema_stats(request: Request, user=Depends(get_current_user)):
    """Detailed schema-level analytics (user-scoped)."""
    schemas_info: List[Dict[str, Any]] = []

    user_schemas = get_user_schemas(user.id)
    for sid, sdata in user_schemas.items():
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
