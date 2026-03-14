import json
import time
import logging
from fastapi import APIRouter, HTTPException, Request, Depends, Query, UploadFile, File
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.lib.schemas import ParseResponse, HealthResponse
from src.services.schema_store import PARSED_SCHEMAS, MAX_FILE_SIZE, schema_manager
from src.lib.auth import get_current_user
from src.utils.sql.parser import SQLSchemaParser
from .parse.helpers import compute_stats, store_schema

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Schema Parser"])
limiter = Limiter(key_func=get_remote_address)
parser = SQLSchemaParser()

@router.get("/health", response_model=HealthResponse)
@limiter.limit("100/minute")
async def health_check(request: Request):
    size = sum(d.get("file_size", 0) for d in PARSED_SCHEMAS.values())
    return HealthResponse(status="healthy", version="1.0.0", schemas_in_memory=len(PARSED_SCHEMAS), additional_info={"max_schemas_limit": 100, "total_storage_bytes": size, "max_file_size": MAX_FILE_SIZE})

@router.post("/parse", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_sql(request: Request, file: UploadFile = File(...), save_to_disk: bool = Query(True), user=Depends(get_current_user)) -> ParseResponse:
    start = time.time()
    if not file.filename.endswith(".sql"): raise HTTPException(400, "Invalid file")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE: raise HTTPException(413, "Too large")
    txt = content.decode("utf-8")
    h, sid = schema_manager.generate_content_hash(txt), schema_manager.generate_schema_id(txt)
    schema = parser._parse_sql_content(txt)
    path = store_schema(schema, sid, h, file.filename, content, "sql", save_to_disk, user_id=user.id)
    return ParseResponse(success=True, schema_id=sid, message="Success", processing_time=time.time()-start, statistics=compute_stats(schema, {"schema_id": sid}), data=json.dumps(schema), file_path=path)

@router.post("/parse/json", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_json(request: Request, payload: dict, save_to_disk: bool = Query(True), user=Depends(get_current_user)) -> ParseResponse:
    start = time.time()
    schema = payload.get("schema", payload)
    txt = json.dumps(schema)
    h, sid = schema_manager.generate_content_hash(txt), schema_manager.generate_schema_id(txt)
    path = store_schema(schema, sid, h, "editor.json", txt.encode(), "json", save_to_disk, user_id=user.id)
    return ParseResponse(success=True, schema_id=sid, message="Success", processing_time=time.time()-start, statistics=compute_stats(schema), data=txt, file_path=path)
