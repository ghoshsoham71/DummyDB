"""
Schema Router — CRUD endpoints for managing parsed schemas.
"""

import os
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, Query, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.services.schema_store import PARSED_SCHEMAS, get_user_schemas
from src.lib.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Schemas"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/schemas")
@limiter.limit("50/minute")
async def list_schemas(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    search: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    """List schemas with pagination, sorting, and search (user-scoped)."""
    user_schemas = get_user_schemas(user.id)
    filtered = user_schemas
    if search:
        filtered = {
            k: v for k, v in user_schemas.items()
            if search.lower() in v["filename"].lower()
        }

    sort_map = {
        "created_at": lambda x: x[1]["created_at"],
        "filename": lambda x: x[1]["filename"].lower(),
        "file_size": lambda x: x[1]["file_size"],
    }

    if sort_by in sort_map:
        sorted_items = sorted(filtered.items(), key=sort_map[sort_by], reverse=(sort_order == "desc"))
    else:
        sorted_items = list(filtered.items())

    paginated: List[Any] = sorted_items[offset:offset + limit]

    schema_list = []
    for sid, sdata in paginated:
        schema_list.append({
            "schema_id": sid,
            "filename": sdata["filename"],
            "created_at": sdata["created_at"],
            "file_size": sdata["file_size"],
            "content_hash": sdata.get("content_hash", ""),
            "table_count": sum(len(db.get("tables", [])) for db in sdata["schema"].get("databases", [])),
            "metadata": sdata.get("metadata", {}),
        })

    return {
        "schemas": schema_list,
        "total": len(filtered),
        "pagination": {
            "offset": offset, "limit": limit,
            "has_more": offset + limit < len(filtered),
        },
    }


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
    if schema_id not in PARSED_SCHEMAS:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' not found")
    if PARSED_SCHEMAS[schema_id].get("user_id") != user.id:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' not found")

    schema = PARSED_SCHEMAS[schema_id]["schema"]
    found_table = None
    found_database = None

    for database in schema.get("databases", []):
        for table in database.get("tables", []):
            if table["name"].lower() == table_name.lower():
                found_table = table
                found_database = database["name"]
                break
        if found_table:
            break

    if not found_table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    attributes: List[Dict[str, Any]] = found_table.get("attributes", [])
    primary_keys = [a["name"] for a in attributes if "PRIMARY_KEY" in a.get("constraints", [])]
    unique_cols = [a["name"] for a in attributes if "UNIQUE" in a.get("constraints", [])]
    nullable_cols = [a["name"] for a in attributes if "NOT_NULL" not in a.get("constraints", [])]

    foreign_keys = []
    for attr in attributes:
        for c in attr.get("constraints", []):
            if c.startswith("FOREIGN_KEY_REFERENCES_"):
                ref = c.replace("FOREIGN_KEY_REFERENCES_", "").split(".")
                if len(ref) == 2:
                    foreign_keys.append({
                        "column": attr["name"],
                        "references_table": ref[0],
                        "references_column": ref[1],
                    })

    return {
        "schema_id": schema_id,
        "database": found_database,
        "table": found_table,
        "analysis": {
            "total_columns": len(attributes),
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "unique_columns": unique_cols,
            "nullable_columns": nullable_cols,
        },
    }
