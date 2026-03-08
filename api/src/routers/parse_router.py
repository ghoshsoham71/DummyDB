"""
Parse Router — endpoints for parsing schemas from SQL files, Supabase,
MongoDB, and Neo4j connections.
"""

import json
import time
import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.lib.schemas import (
    ParseResponse, HealthResponse, SupabaseParseRequest,
    MongoDBParseRequest, Neo4jParseRequest,
)
from src.utils.schema_parse import SQLSchemaParser
from src.utils.supabase_extractor import SupabaseExtractor
from src.utils.mongodb_extractor import MongoDBExtractor
from src.utils.neo4j_extractor import Neo4jExtractor
from src.lib.database import insert_schema, check_schema_exists_by_hash
from src.services.schema_store import (
    PARSED_SCHEMAS, MAX_FILE_SIZE, schema_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Schema Parser"])
limiter = Limiter(key_func=get_remote_address)
parser_instance = SQLSchemaParser()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_stats(schema: Dict[str, Any], extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return standard statistics dict for a parsed schema."""
    databases = schema.get("databases", [])
    stats: Dict[str, Any] = {
        "databases": len(databases),
        "tables": sum(len(db.get("tables", [])) for db in databases),
        "columns": sum(
            len(t.get("attributes", []))
            for db in databases for t in db.get("tables", [])
        ),
    }
    if extra:
        stats.update(extra)
    return stats


def _store_schema(
    schema: Dict[str, Any],
    schema_id: str,
    content_hash: str,
    filename: str,
    content_bytes: bytes,
    source: str,
    save_to_disk: bool,
    extra_metadata: Dict[str, Any] | None = None,
) -> str | None:
    """Persist schema in memory and optionally to disk. Returns file_path."""
    schema_manager.cleanup_old_schemas()

    schema_data: Dict[str, Any] = {
        "schema": schema,
        "filename": filename,
        "created_at": time.time(),
        "file_size": len(content_bytes),
        "content_hash": content_hash,
        "metadata": {
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            **(extra_metadata or {}),
        },
    }

    json_file_path = None
    if save_to_disk:
        schemas_dir = Path("./schemas")
        schemas_dir.mkdir(parents=True, exist_ok=True)
        json_file_path = schemas_dir / f"schema_{content_hash}.json"
        try:
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False, default=str)
            schema_data["file_path"] = str(json_file_path)
        except Exception as e:
            logger.warning(f"Failed to save schema to disk: {e}")
            json_file_path = None

    PARSED_SCHEMAS[schema_id] = schema_data

    # Best-effort database insertion
    try:
        insert_schema(
            schema_data=schema,
            filename=filename,
            content_hash=content_hash,
            file_size=len(content_bytes),
        )
    except Exception as db_err:
        logger.error(f"DB insert failed: {db_err}")

    return str(json_file_path) if json_file_path else None


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    total_size = sum(d.get("file_size", 0) for d in PARSED_SCHEMAS.values())
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        schemas_in_memory=len(PARSED_SCHEMAS),
        additional_info={
            "max_schemas_limit": 100,
            "total_storage_bytes": total_size,
            "max_file_size": MAX_FILE_SIZE,
        },
    )


# ── SQL Parse ─────────────────────────────────────────────────────────────────

@router.post("/parse", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_sql_schema(
    request: Request,
    file: UploadFile = File(..., description="SQL file to parse"),
    save_to_disk: bool = Query(True),
    overwrite_existing: bool = Query(False),
) -> ParseResponse:
    """Parse uploaded SQL file and store schema."""
    start_time = time.time()

    if not file.filename or not file.filename.endswith(".sql"):
        raise HTTPException(status_code=400, detail="File must have .sql extension")

    try:
        content: bytes = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File size exceeds limit")

        try:
            sql_content = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                sql_content = content.decode("latin-1")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Unsupported encoding")

        content_hash = schema_manager.generate_content_hash(sql_content)
        schema_id = schema_manager.generate_schema_id(sql_content)

        # Deduplicate — database
        try:
            if check_schema_exists_by_hash(content_hash) and not overwrite_existing:
                return ParseResponse(
                    success=True, schema_id=schema_id,
                    message="Schema already exists in database.",
                    processing_time=time.time() - start_time,
                    statistics={"content_hash": content_hash, "duplicate": True},
                    file_path=None,
                )
        except Exception:
            pass

        # Deduplicate — memory
        if schema_id in PARSED_SCHEMAS and not overwrite_existing:
            return ParseResponse(
                success=True, schema_id=schema_id,
                message="Schema already exists in memory.",
                processing_time=time.time() - start_time,
                statistics={"duplicate": True},
                file_path=PARSED_SCHEMAS[schema_id].get("file_path"),
            )

        # Parse
        parser_instance.databases = {}
        parser_instance.current_database = None
        schema = parser_instance._parse_sql_content(sql_content)

        if not schema_manager.validate_schema_content(schema):
            raise ValueError("Invalid schema structure")

        file_path = _store_schema(
            schema, schema_id, content_hash,
            file.filename, content, "sql_upload", save_to_disk,
        )

        stats = _compute_stats(schema, {
            "file_size": len(content), "schema_id": schema_id,
            "content_hash": content_hash, "duplicate": False,
        })

        return ParseResponse(
            success=True, schema_id=schema_id,
            message=f"Schema parsed successfully. ID: {schema_id}",
            processing_time=time.time() - start_time,
            statistics=stats,
            data=json.dumps(schema),
            file_path=file_path,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL parse failed: {e}")
        return ParseResponse(
            success=False, schema_id=None,
            message=f"Failed: {e}",
            processing_time=time.time() - start_time,
            statistics={}, file_path=None,
        )


# ── Supabase Parse ────────────────────────────────────────────────────────────

@router.post("/parse/supabase", response_model=ParseResponse)
@limiter.limit("5/minute")
async def parse_supabase_schema(request: Request, payload: SupabaseParseRequest) -> ParseResponse:
    """Connect to Supabase and extract schema."""
    start_time = time.time()
    try:
        extractor = SupabaseExtractor(payload.connection_string)
        schema = extractor.extract_schema()

        if not schema_manager.validate_schema_content(schema):
            raise ValueError("Invalid schema from Supabase")

        schema_json = json.dumps(schema, sort_keys=True)
        content_hash = schema_manager.generate_content_hash(schema_json)
        schema_id = schema_manager.generate_schema_id(schema_json)

        try:
            if check_schema_exists_by_hash(content_hash) and not payload.overwrite_existing:
                return ParseResponse(
                    success=True, schema_id=schema_id,
                    message="Schema already exists.",
                    processing_time=time.time() - start_time,
                    statistics={"duplicate": True}, file_path=None,
                )
        except Exception:
            pass

        if schema_id in PARSED_SCHEMAS and not payload.overwrite_existing:
            return ParseResponse(
                success=True, schema_id=schema_id,
                message="Schema already in memory.",
                processing_time=time.time() - start_time,
                statistics={"duplicate": True}, file_path=None,
            )

        content_bytes = schema_json.encode("utf-8")
        file_path = _store_schema(
            schema, schema_id, content_hash,
            "supabase_extracted_schema.json", content_bytes,
            "supabase_extractor", payload.save_to_disk,
            {"connection": "**REDACTED**"},
        )

        stats = _compute_stats(schema, {
            "schema_id": schema_id, "content_hash": content_hash, "duplicate": False,
        })

        return ParseResponse(
            success=True, schema_id=schema_id,
            message=f"Supabase schema extracted. ID: {schema_id}",
            processing_time=time.time() - start_time,
            statistics=stats,
            data=json.dumps(schema),
            file_path=file_path,
        )
    except Exception as e:
        logger.error(f"Supabase extraction failed: {e}")
        return ParseResponse(
            success=False, schema_id=None,
            message=f"Failed: {e}",
            processing_time=time.time() - start_time,
            statistics={}, file_path=None,
        )


# ── MongoDB Parse ─────────────────────────────────────────────────────────────

@router.post("/parse/mongodb", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_mongodb_schema(request: Request, payload: MongoDBParseRequest):
    """Extract schema from a MongoDB instance."""
    start_time = time.time()
    try:
        extractor = MongoDBExtractor(
            connection_string=payload.connection_string,
            database_name=payload.database_name,
        )
        schema = extractor.extract_schema(sample_size=payload.sample_size)

        schema_json = json.dumps(schema, default=str)
        content_hash = schema_manager.generate_content_hash(schema_json)
        schema_id = f"schema_{content_hash}"

        if schema_id in PARSED_SCHEMAS and not payload.overwrite_existing:
            return ParseResponse(
                success=True, schema_id=schema_id,
                message="Identical MongoDB schema already in memory.",
                processing_time=time.time() - start_time,
                statistics={"duplicate": True}, file_path=None,
            )

        content_bytes = schema_json.encode("utf-8")
        file_path = _store_schema(
            schema, schema_id, content_hash,
            "mongodb_extracted_schema.json", content_bytes,
            "mongodb_extractor", payload.save_to_disk,
        )

        stats = _compute_stats(schema, {
            "schema_id": schema_id, "content_hash": content_hash, "duplicate": False,
        })

        return ParseResponse(
            success=True, schema_id=schema_id,
            message=f"MongoDB schema extracted. ID: {schema_id}",
            processing_time=time.time() - start_time,
            statistics=stats,
            data=json.dumps(schema, default=str),
            file_path=file_path,
        )
    except Exception as e:
        logger.error(f"MongoDB extraction failed: {e}")
        return ParseResponse(
            success=False, schema_id=None,
            message=f"Failed: {e}",
            processing_time=time.time() - start_time,
            statistics={}, file_path=None,
        )


# ── Neo4j Parse ───────────────────────────────────────────────────────────────

@router.post("/parse/neo4j", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_neo4j_schema(request: Request, payload: Neo4jParseRequest):
    """Extract schema from Neo4j via bolt protocol (default bolt://localhost:7687)."""
    start_time = time.time()
    try:
        extractor = Neo4jExtractor(
            uri=payload.uri, username=payload.username,
            password=payload.password, database=payload.database,
        )
        schema = extractor.extract_schema()

        schema_json = json.dumps(schema, default=str)
        content_hash = schema_manager.generate_content_hash(schema_json)
        schema_id = f"schema_{content_hash}"

        if schema_id in PARSED_SCHEMAS and not payload.overwrite_existing:
            return ParseResponse(
                success=True, schema_id=schema_id,
                message="Identical Neo4j schema already in memory.",
                processing_time=time.time() - start_time,
                statistics={"duplicate": True}, file_path=None,
            )

        content_bytes = schema_json.encode("utf-8")
        neo4j_browser = schema.get("connection", {}).get("http_browser", "http://localhost:7474")
        file_path = _store_schema(
            schema, schema_id, content_hash,
            "neo4j_extracted_schema.json", content_bytes,
            "neo4j_extractor", payload.save_to_disk,
            {"neo4j_browser": neo4j_browser},
        )

        databases = schema.get("databases", [])
        nodes = [t for db in databases for t in db.get("tables", []) if t.get("node_type") == "node"]
        rels = [t for db in databases for t in db.get("tables", []) if t.get("node_type") == "relationship"]

        stats: Dict[str, Any] = {
            "node_labels": len(nodes),
            "relationship_types": len(rels),
            "properties": sum(len(t.get("attributes", [])) for t in nodes + rels),
            "schema_id": schema_id, "content_hash": content_hash,
            "neo4j_browser": neo4j_browser, "duplicate": False,
        }

        return ParseResponse(
            success=True, schema_id=schema_id,
            message=f"Neo4j schema extracted. ID: {schema_id}",
            processing_time=time.time() - start_time,
            statistics=stats,
            data=json.dumps(schema, default=str),
            file_path=file_path,
        )
    except Exception as e:
        logger.error(f"Neo4j extraction failed: {e}")
        return ParseResponse(
            success=False, schema_id=None,
            message=f"Failed: {e}",
            processing_time=time.time() - start_time,
            statistics={}, file_path=None,
        )
