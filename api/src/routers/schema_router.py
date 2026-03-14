"""
Schema Router — CRUD endpoints for managing parsed schemas.
"""

import os
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, Query, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..services.schema_store import PARSED_SCHEMAS, get_user_schemas
from ..lib.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Schemas"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/schemas")
@limiter.limit("50/minute")
async def list_schemas(
    request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"), sort_order: str = Query("desc"),
    search: Optional[str] = Query(None), user=Depends(get_current_user),
):
    """List schemas with pagination, sorting, and search (user-scoped)."""
    items = _filter_and_sort_schemas(get_user_schemas(user.id), search, sort_by, sort_order)
    paginated = items[offset:offset + limit]
    return {
        "schemas": _format_paginated_schemas(paginated), "total": len(items),
        "pagination": {"offset": offset, "limit": limit, "has_more": offset + limit < len(items)},
    }

def _filter_and_sort_schemas(user_schemas, search, sort_by, sort_order) -> list:
    filtered = user_schemas
    if search:
        filtered = {k: v for k, v in user_schemas.items() if search.lower() in v["filename"].lower()}
    sort_map = {
        "created_at": lambda x: x[1]["created_at"],
        "filename": lambda x: x[1]["filename"].lower(),
        "file_size": lambda x: x[1]["file_size"],
    }
    key_func = sort_map.get(sort_by, lambda x: x[0])
    return sorted(filtered.items(), key=key_func, reverse=(sort_order == "desc"))

def _format_paginated_schemas(items: list) -> list:
    return [{
        "schema_id": sid, "filename": s["filename"], "created_at": s["created_at"],
        "file_size": s["file_size"], "content_hash": s.get("content_hash", ""),
        "table_count": sum(len(db.get("tables", [])) for db in s["schema"].get("databases", [])),
        "metadata": s.get("metadata", {}),
    } for sid, s in items]


@router.get("/schemas/{schema_id}")
@limiter.limit("50/minute")
async def get_schema(
    request: Request,
    schema_id: str,
    include_metadata: bool = Query(True),
    format_output: bool = Query(False),
    user=Depends(get_current_user),
):
    """Get specific schema by ID (user-scoped)."""
    if schema_id not in PARSED_SCHEMAS:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' not found")
    sdata = PARSED_SCHEMAS[schema_id]
    if sdata.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' not found")
    response: Dict[str, Any] = {"schema_id": schema_id, "schema": sdata["schema"]}

    if include_metadata:
        response["metadata"] = {
            "filename": sdata["filename"],
            "created_at": sdata["created_at"],
            "file_size": sdata["file_size"],
            "content_hash": sdata.get("content_hash", ""),
            "file_path": sdata.get("file_path"),
            **sdata.get("metadata", {}),
        }

    if format_output:
        databases = sdata["schema"].get("databases", [])
        response["summary"] = {
            "total_databases": len(databases),
            "database_details": [
                {
                    "name": db["name"],
                    "table_count": len(db.get("tables", [])),
                    "tables": [
                        {
                            "name": t["name"],
                            "column_count": len(t.get("attributes", [])),
                            "primary_keys": [
                                a["name"] for a in t.get("attributes", [])
                                if "PRIMARY_KEY" in a.get("constraints", [])
                            ],
                        }
                        for t in db.get("tables", [])
                    ],
                }
                for db in databases
            ],
        }

    return response


@router.delete("/schemas/{schema_id}")
@limiter.limit("20/minute")
async def delete_schema(request: Request, schema_id: str, user=Depends(get_current_user)):
    """Delete schema from memory by ID (user-scoped)."""
    if schema_id not in PARSED_SCHEMAS:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' not found")
    if PARSED_SCHEMAS[schema_id].get("user_id") != user.id:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' not found")

    deleted = PARSED_SCHEMAS.pop(schema_id)
    file_path = deleted.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path}: {e}")

    return {
        "message": f"Schema '{schema_id}' deleted",
        "deleted_schema_info": {
            "filename": deleted["filename"],
            "created_at": deleted["created_at"],
            "content_hash": deleted.get("content_hash"),
        },
    }


@router.post("/schemas/bulk-delete")
@limiter.limit("10/minute")
async def bulk_delete_schemas(
    request: Request,
    schema_ids: List[str],
    delete_files: bool = Query(False),
    user=Depends(get_current_user),
):
    """Delete multiple schemas at once (user-scoped)."""
    deleted_list = []
    not_found = []

    for sid in schema_ids:
        if sid in PARSED_SCHEMAS and PARSED_SCHEMAS[sid].get("user_id") == user.id:
            removed = PARSED_SCHEMAS.pop(sid)
            deleted_list.append({"schema_id": sid, "filename": removed["filename"]})
            if delete_files:
                fp = removed.get("file_path")
                if fp and os.path.exists(fp):
                    try:
                        os.unlink(fp)
                    except Exception:
                        pass
        else:
            not_found.append(sid)

    return {
        "deleted_count": len(deleted_list),
        "deleted_schemas": deleted_list,
        "not_found_schemas": not_found,
        "message": f"Deleted {len(deleted_list)} schemas",
    }


@router.get("/schemas/{schema_id}/tables/{table_name}")
@limiter.limit("50/minute")
async def get_table_details(request: Request, schema_id: str, table_name: str, user=Depends(get_current_user)):
    """Get detailed information about a specific table (user-scoped)."""
    if schema_id not in PARSED_SCHEMAS or PARSED_SCHEMAS[schema_id].get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Schema not found")
    table, db_name = _find_table_in_schema(PARSED_SCHEMAS[schema_id]["schema"], table_name)
    if not table: raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    return {
        "schema_id": schema_id, "database": db_name, "table": table,
        "analysis": _analyze_table_constraints(table.get("attributes", []))
    }

def _find_table_in_schema(schema: dict, table_name: str):
    for db in schema.get("databases", []):
        for t in db.get("tables", []):
            if t["name"].lower() == table_name.lower():
                return t, db["name"]
    return None, None

def _analyze_table_constraints(attributes: list) -> dict:
    fks = []
    for a in attributes:
        for c in a.get("constraints", []):
            if c.startswith("FOREIGN_KEY_REFERENCES_"):
                ref = c.replace("FOREIGN_KEY_REFERENCES_", "").split(".")
                if len(ref) == 2: fks.append({"column": a["name"], "references_table": ref[0], "references_column": ref[1]})
    return {
        "total_columns": len(attributes),
        "primary_keys": [a["name"] for a in attributes if "PRIMARY_KEY" in a.get("constraints", [])],
        "foreign_keys": fks,
        "unique_columns": [a["name"] for a in attributes if "UNIQUE" in a.get("constraints", [])],
        "nullable_columns": [a["name"] for a in attributes if "NOT_NULL" not in a.get("constraints", [])]
    }
