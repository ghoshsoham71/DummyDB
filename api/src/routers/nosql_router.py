import json
import time
import logging
from fastapi import APIRouter, Depends
from src.lib.schemas import ParseResponse, MongoDBParseRequest, Neo4jParseRequest
from src.services.schema_store import schema_manager
from src.lib.auth import get_current_user
from src.utils.extractors.mongodb_extractor import MongoDBExtractor
from src.utils.extractors.neo4j_extractor import Neo4jExtractor
from .parse.helpers import compute_stats, store_schema

logger = logging.getLogger(__name__)
router = APIRouter(tags=["NoSQL Parser"], prefix="/parse")

@router.post("/mongodb", response_model=ParseResponse)
async def parse_mongodb(payload: MongoDBParseRequest, user=Depends(get_current_user)):
    start = time.time()
    ex = MongoDBExtractor(payload.connection_string, payload.database_name)
    schema = ex.extract_schema(sample_size=payload.sample_size)
    txt = json.dumps(schema, default=str)
    h, sid = schema_manager.generate_content_hash(txt), f"schema_{schema_manager.generate_content_hash(txt)}"
    path = store_schema(schema, sid, h, "mongodb.json", txt.encode(), "mongodb", payload.save_to_disk, user_id=user.id)
    return ParseResponse(success=True, schema_id=sid, message="Success", processing_time=time.time()-start, statistics=compute_stats(schema, {"schema_id": sid}), data=txt, file_path=path)

@router.post("/neo4j", response_model=ParseResponse)
async def parse_neo4j(payload: Neo4jParseRequest, user=Depends(get_current_user)):
    start = time.time()
    ex = Neo4jExtractor(payload.uri, payload.username, payload.password, payload.database)
    schema = ex.extract_schema()
    txt = json.dumps(schema, default=str)
    h, sid = schema_manager.generate_content_hash(txt), f"schema_{schema_manager.generate_content_hash(txt)}"
    path = store_schema(schema, sid, h, "neo4j.json", txt.encode(), "neo4j", payload.save_to_disk, user_id=user.id)
    return ParseResponse(success=True, schema_id=sid, message="Success", processing_time=time.time()-start, statistics=compute_stats(schema), data=txt, file_path=path)
