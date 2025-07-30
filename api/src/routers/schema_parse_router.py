import json
import os
import time
import tempfile
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Query, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.lib.schemas import ParseResponse, HealthResponse, ParseRequest
from src.utils.schema_parse import SQLSchemaParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for parsed schemas with enhanced structure
PARSED_SCHEMAS: Dict[str, Dict[str, Any]] = {}
SCHEMA_COUNTER = 0
MAX_SCHEMAS_IN_MEMORY = 100  # Configurable limit
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

# Create router with tags for better API documentation
router = APIRouter(tags=["Schema Parser"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize parser instance
parser_instance = SQLSchemaParser()

class SchemaManager:
    """Enhanced schema management with cleanup and validation"""
    
    @staticmethod
    def generate_schema_id(filename: str, content: str) -> str:
        """Generate deterministic schema ID based on content hash"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        return f"schema_{content_hash}_{timestamp}"
    
    @staticmethod
    def cleanup_old_schemas():
        """Remove oldest schemas if memory limit exceeded"""
        if len(PARSED_SCHEMAS) >= MAX_SCHEMAS_IN_MEMORY:
            # Sort by creation time and remove oldest
            sorted_schemas = sorted(
                PARSED_SCHEMAS.items(),
                key=lambda x: x[1]["created_at"]
            )
            
            # Remove oldest 20% when limit reached
            remove_count = max(1, len(sorted_schemas) // 5)
            for i in range(remove_count):
                schema_id = sorted_schemas[i][0]
                removed = PARSED_SCHEMAS.pop(schema_id, None)
                if removed:
                    logger.info(f"Removed old schema: {schema_id}")
    
    @staticmethod
    def validate_schema_content(schema: Dict[str, Any]) -> bool:
        """Validate schema structure"""
        if not isinstance(schema, dict):
            return False
        
        databases = schema.get("databases", [])
        if not isinstance(databases, list):
            return False
        
        for db in databases:
            if not isinstance(db, dict) or "name" not in db:
                return False
            
            tables = db.get("tables", [])
            if not isinstance(tables, list):
                return False
            
            for table in tables:
                if not isinstance(table, dict) or "name" not in table:
                    return False
        
        return True

schema_manager = SchemaManager()

@router.get("/health", response_model=HealthResponse)
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint with enhanced schema storage info"""
    total_size = sum(
        data.get("file_size", 0) for data in PARSED_SCHEMAS.values()
    )
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        schemas_in_memory=len(PARSED_SCHEMAS),
        additional_info={
            "max_schemas_limit": MAX_SCHEMAS_IN_MEMORY,
            "total_storage_bytes": total_size,
            "max_file_size": MAX_FILE_SIZE
        }
    )

@router.post("/parse", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_sql_schema(
    request: Request,
    file: UploadFile = File(..., description="SQL file to parse (.sql extension required)"),
    save_to_disk: bool = Query(True, description="Whether to save JSON schema to disk"),
    overwrite_existing: bool = Query(False, description="Overwrite existing schema with same content hash")
) -> ParseResponse:
    """
    Parse uploaded SQL file and store schema in local JSON file and memory
    
    Enhanced with:
    - File size validation
    - Content deduplication
    - Better error handling
    - Optional disk saving
    - Schema validation
    """
    global SCHEMA_COUNTER
    start_time = time.time()
    
    # Validate file type
    if not file.filename or not file.filename.endswith('.sql'):
        raise HTTPException(
            status_code=400,
            detail="File must have .sql extension"
        )
    
    try:
        # Read and validate file content
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE} bytes"
            )
        
        # Decode content
        try:
            sql_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                sql_content = content.decode('latin-1')
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="File must be valid UTF-8 or Latin-1 encoded text"
                )
        
        # Generate schema ID and check for duplicates
        schema_id = schema_manager.generate_schema_id(file.filename, sql_content)
        
        if schema_id in PARSED_SCHEMAS and not overwrite_existing:
            existing_schema = PARSED_SCHEMAS[schema_id]
            return ParseResponse(
                success=True,
                schema_id=schema_id,
                message=f"Schema already exists (duplicate content). Use overwrite_existing=true to replace.",
                processing_time=time.time() - start_time,
                statistics={
                    "databases": len(existing_schema["schema"].get("databases", [])),
                    "tables": sum(len(db.get("tables", [])) for db in existing_schema["schema"].get("databases", [])),
                    "columns": sum(
                        len(table.get("attributes", []))
                        for db in existing_schema["schema"].get("databases", [])
                        for table in db.get("tables", [])
                    ),
                    "file_size": existing_schema["file_size"],
                    "schema_id": schema_id,
                    "duplicate": True
                },
                file_path=existing_schema.get("file_path")
            )
        
        # Clean up old schemas if needed
        schema_manager.cleanup_old_schemas()
        
        # Parse the SQL content
        parser_instance.databases = {}
        parser_instance.current_database = None
        schema = parser_instance._parse_sql_content(sql_content)
        
        # Validate parsed schema
        if not schema_manager.validate_schema_content(schema):
            raise ValueError("Invalid schema structure generated from SQL content")
        
        # Prepare schema data
        schema_data = {
            "schema": schema,
            "filename": file.filename,
            "created_at": time.time(),
            "file_size": len(content),
            "content_hash": hashlib.md5(sql_content.encode()).hexdigest(),
            "metadata": {
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "file_extension": Path(file.filename).suffix,
                "original_filename": file.filename
            }
        }
        
        json_file_path = None
        
        # Save to disk if requested
        if save_to_disk:
            schemas_dir = Path("./schemas")
            schemas_dir.mkdir(parents=True, exist_ok=True)
            
            base_filename = Path(file.filename).stem
            json_filename = f"{base_filename}_schema_{int(time.time())}.json"
            json_file_path = schemas_dir / json_filename
            
            try:
                with open(json_file_path, 'w', encoding='utf-8') as json_file:
                    json.dump(schema, json_file, indent=2, ensure_ascii=False)
                
                schema_data["file_path"] = str(json_file_path)
                logger.info(f"Schema saved to disk: {json_file_path}")
                
            except Exception as e:
                logger.warning(f"Failed to save schema to disk: {e}")
                json_file_path = None
        
        # Store schema in memory
        PARSED_SCHEMAS[schema_id] = schema_data
        SCHEMA_COUNTER += 1
        
        processing_time = time.time() - start_time
        
        # Calculate enhanced statistics
        databases = schema.get("databases", [])
        stats = {
            "databases": len(databases),
            "tables": sum(len(db.get("tables", [])) for db in databases),
            "columns": sum(
                len(table.get("attributes", []))
                for db in databases
                for table in db.get("tables", [])
            ),
            "file_size": len(content),
            "schema_id": schema_id,
            "content_hash": schema_data["content_hash"],
            "duplicate": False
        }
        
        # Add constraint statistics
        constraint_counts = {}
        for db in databases:
            for table in db.get("tables", []):
                for attr in table.get("attributes", []):
                    for constraint in attr.get("constraints", []):
                        constraint_counts[constraint] = constraint_counts.get(constraint, 0) + 1
        
        stats["constraint_summary"] = constraint_counts
        
        logger.info(f"Successfully parsed schema {schema_id} in {processing_time:.2f}s")
        
        return ParseResponse(
            success=True,
            schema_id=schema_id,
            message=f"Schema parsed and stored successfully. Schema ID: {schema_id}",
            processing_time=processing_time,
            statistics=stats,
            file_path=str(json_file_path) if json_file_path else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Schema parsing failed: {str(e)}")
        
        return ParseResponse(
            success=False,
            schema_id=None,
            message=f"Failed to parse schema: {str(e)}",
            processing_time=processing_time,
            statistics={},
            file_path=None
        )

@router.get("/schemas")
@limiter.limit("50/minute")
async def list_schemas(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of schemas to return"),
    offset: int = Query(0, ge=0, description="Number of schemas to skip"),
    sort_by: str = Query("created_at", description="Sort field: created_at, filename, file_size"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    search: Optional[str] = Query(None, description="Search in filenames")
):
    """List schemas with pagination, sorting, and search"""
    
    # Filter schemas
    filtered_schemas = PARSED_SCHEMAS
    if search:
        filtered_schemas = {
            k: v for k, v in PARSED_SCHEMAS.items()
            if search.lower() in v["filename"].lower()
        }
    
    # Sort schemas
    sort_key_map = {
        "created_at": lambda x: x[1]["created_at"],
        "filename": lambda x: x[1]["filename"].lower(),
        "file_size": lambda x: x[1]["file_size"]
    }
    
    if sort_by in sort_key_map:
        sorted_items = sorted(
            filtered_schemas.items(),
            key=sort_key_map[sort_by],
            reverse=(sort_order == "desc")
        )
    else:
        sorted_items = list(filtered_schemas.items())
    
    # Apply pagination
    paginated_items = sorted_items[offset:offset + limit]
    
    schema_list = []
    for schema_id, schema_data in paginated_items:
        schema_info = {
            "schema_id": schema_id,
            "filename": schema_data["filename"],
            "created_at": schema_data["created_at"],
            "file_size": schema_data["file_size"],
            "content_hash": schema_data.get("content_hash", ""),
            "databases": len(schema_data["schema"].get("databases", [])),
            "tables": sum(len(db.get("tables", [])) for db in schema_data["schema"].get("databases", [])),
            "metadata": schema_data.get("metadata", {})
        }
        schema_list.append(schema_info)
    
    return {
        "schemas": schema_list,
        "pagination": {
            "total_schemas": len(filtered_schemas),
            "returned_count": len(schema_list),
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < len(filtered_schemas)
        },
        "filters": {
            "search": search,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
    }

@router.get("/schemas/{schema_id}")
@limiter.limit("50/minute")
async def get_schema(
    request: Request, 
    schema_id: str,
    include_metadata: bool = Query(True, description="Include additional metadata"),
    format_output: bool = Query(False, description="Format output for better readability")
):
    """Get specific schema by ID with enhanced options"""
    if schema_id not in PARSED_SCHEMAS:
        raise HTTPException(
            status_code=404,
            detail=f"Schema with ID '{schema_id}' not found"
        )
    
    schema_data = PARSED_SCHEMAS[schema_id]
    
    response = {
        "schema_id": schema_id,
        "schema": schema_data["schema"]
    }
    
    if include_metadata:
        response["metadata"] = {
            "filename": schema_data["filename"],
            "created_at": schema_data["created_at"],
            "file_size": schema_data["file_size"],
            "content_hash": schema_data.get("content_hash", ""),
            "file_path": schema_data.get("file_path"),
            **schema_data.get("metadata", {})
        }
    
    if format_output:
        # Add formatted summary
        schema = schema_data["schema"]
        databases = schema.get("databases", [])
        
        response["summary"] = {
            "total_databases": len(databases),
            "database_details": [
                {
                    "name": db["name"],
                    "table_count": len(db.get("tables", [])),
                    "tables": [
                        {
                            "name": table["name"],
                            "column_count": len(table.get("attributes", [])),
                            "primary_keys": [
                                attr["name"] for attr in table.get("attributes", [])
                                if "PRIMARY_KEY" in attr.get("constraints", [])
                            ],
                            "foreign_keys": [
                                {
                                    "column": attr["name"],
                                    "references": [c for c in attr.get("constraints", []) if c.startswith("FOREIGN_KEY")]
                                }
                                for attr in table.get("attributes", [])
                                if any(c.startswith("FOREIGN_KEY") for c in attr.get("constraints", []))
                            ]
                        }
                        for table in db.get("tables", [])
                    ]
                }
                for db in databases
            ]
        }
    
    return response

@router.delete("/schemas/{schema_id}")
@limiter.limit("20/minute")
async def delete_schema(request: Request, schema_id: str):
    """Delete schema from memory by ID"""
    if schema_id not in PARSED_SCHEMAS:
        raise HTTPException(
            status_code=404,
            detail=f"Schema with ID '{schema_id}' not found"
        )
    
    deleted_schema = PARSED_SCHEMAS.pop(schema_id)
    
    # Optionally delete file from disk
    file_path = deleted_schema.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
            logger.info(f"Deleted schema file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete schema file {file_path}: {e}")
    
    return {
        "message": f"Schema '{schema_id}' deleted successfully",
        "deleted_schema_info": {
            "filename": deleted_schema["filename"],
            "created_at": deleted_schema["created_at"],
            "file_path": file_path
        }
    }

@router.post("/schemas/bulk-delete")
@limiter.limit("10/minute")
async def bulk_delete_schemas(
    request: Request,
    schema_ids: List[str],
    delete_files: bool = Query(False, description="Delete associated files from disk")
):
    """Delete multiple schemas at once"""
    deleted_schemas = []
    not_found_schemas = []
    
    for schema_id in schema_ids:
        if schema_id in PARSED_SCHEMAS:
            deleted_schema = PARSED_SCHEMAS.pop(schema_id)
            deleted_schemas.append({
                "schema_id": schema_id,
                "filename": deleted_schema["filename"]
            })
            
            # Optionally delete file from disk
            if delete_files:
                file_path = deleted_schema.get("file_path")
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                        logger.info(f"Deleted schema file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete schema file {file_path}: {e}")
        else:
            not_found_schemas.append(schema_id)
    
    return {
        "deleted_count": len(deleted_schemas),
        "deleted_schemas": deleted_schemas,
        "not_found_schemas": not_found_schemas,
        "message": f"Successfully deleted {len(deleted_schemas)} schemas"
    }

@router.get("/schemas/{schema_id}/tables/{table_name}")
@limiter.limit("50/minute")
async def get_table_details(request: Request, schema_id: str, table_name: str):
    """Get detailed information about a specific table"""
    if schema_id not in PARSED_SCHEMAS:
        raise HTTPException(
            status_code=404,
            detail=f"Schema with ID '{schema_id}' not found"
        )
    
    schema = PARSED_SCHEMAS[schema_id]["schema"]
    
    # Find the table
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
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' not found in schema '{schema_id}'"
        )
    
    # Analyze table structure
    attributes = found_table.get("attributes", [])
    primary_keys = [attr["name"] for attr in attributes if "PRIMARY_KEY" in attr.get("constraints", [])]
    foreign_keys = []
    unique_columns = [attr["name"] for attr in attributes if "UNIQUE" in attr.get("constraints", [])]
    nullable_columns = [attr["name"] for attr in attributes if "NOT_NULL" not in attr.get("constraints", [])]
    
    for attr in attributes:
        for constraint in attr.get("constraints", []):
            if constraint.startswith("FOREIGN_KEY_REFERENCES_"):
                ref_info = constraint.replace("FOREIGN_KEY_REFERENCES_", "").split(".")
                if len(ref_info) == 2:
                    foreign_keys.append({
                        "column": attr["name"],
                        "references_table": ref_info[0],
                        "references_column": ref_info[1]
                    })
    
    return {
        "schema_id": schema_id,
        "database": found_database,
        "table": found_table,
        "analysis": {
            "total_columns": len(attributes),
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "unique_columns": unique_columns,
            "nullable_columns": nullable_columns,
            "data_types": {attr["type"]: sum(1 for a in attributes if a["type"] == attr["type"]) for attr in attributes}
        }
    }

# Enhanced utility functions with better error handling and logging

def get_schema_by_id(schema_id: str) -> Optional[Dict[str, Any]]:
    """Get schema by ID with logging"""
    schema_data = PARSED_SCHEMAS.get(schema_id)
    if schema_data:
        logger.debug(f"Retrieved schema: {schema_id}")
        return schema_data["schema"]
    else:
        logger.warning(f"Schema not found: {schema_id}")
        return None

def get_all_schemas() -> Dict[str, Dict[str, Any]]:
    """Get all schemas with deep copy to prevent modification"""
    return {k: v.copy() for k, v in PARSED_SCHEMAS.items()}

def get_latest_schema() -> Optional[Dict[str, Any]]:
    """Get the most recently parsed schema"""
    if not PARSED_SCHEMAS:
        return None
    
    latest_id = max(PARSED_SCHEMAS.keys(), key=lambda x: PARSED_SCHEMAS[x]["created_at"])
    return PARSED_SCHEMAS[latest_id]["schema"]

def search_schemas_by_table(table_name: str) -> Dict[str, Dict[str, Any]]:
    """Search for schemas containing a specific table name (case-insensitive)"""
    matching_schemas = {}
    
    for schema_id, schema_data in PARSED_SCHEMAS.items():
        schema = schema_data["schema"]
        
        for db in schema.get("databases", []):
            for table in db.get("tables", []):
                if table.get("name", "").lower() == table_name.lower():
                    matching_schemas[schema_id] = schema_data
                    break
            
            if schema_id in matching_schemas:
                break
    
    logger.info(f"Found {len(matching_schemas)} schemas containing table '{table_name}'")
    return matching_schemas

def search_schemas_by_column(column_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Search for schemas containing a specific column name"""
    matching_results = {}
    
    for schema_id, schema_data in PARSED_SCHEMAS.items():
        schema = schema_data["schema"]
        matches = []
        
        for db in schema.get("databases", []):
            for table in db.get("tables", []):
                for attr in table.get("attributes", []):
                    if attr.get("name", "").lower() == column_name.lower():
                        matches.append({
                            "database": db["name"],
                            "table": table["name"],
                            "column": attr
                        })
        
        if matches:
            matching_results[schema_id] = matches
    
    logger.info(f"Found column '{column_name}' in {len(matching_results)} schemas")
    return matching_results

def get_schema_statistics() -> Dict[str, Any]:
    """Get comprehensive statistics for all stored schemas"""
    if not PARSED_SCHEMAS:
        return {
            "total_schemas": 0,
            "total_databases": 0,
            "total_tables": 0,
            "total_attributes": 0,
            "total_storage_bytes": 0
        }
    
    total_databases = 0
    total_tables = 0
    total_attributes = 0
    total_storage = 0
    constraint_stats = {}
    data_type_stats = {}
    
    for schema_data in PARSED_SCHEMAS.values():
        schema = schema_data["schema"]
        databases = schema.get("databases", [])
        total_storage += schema_data.get("file_size", 0)
        
        total_databases += len(databases)
        
        for db in databases:
            tables = db.get("tables", [])
            total_tables += len(tables)
            
            for table in tables:
                attributes = table.get("attributes", [])
                total_attributes += len(attributes)
                
                for attr in attributes:
                    # Count data types
                    data_type = attr.get("type", "UNKNOWN")
                    data_type_stats[data_type] = data_type_stats.get(data_type, 0) + 1
                    
                    # Count constraints
                    for constraint in attr.get("constraints", []):
                        constraint_stats[constraint] = constraint_stats.get(constraint, 0) + 1
    
    return {
        "total_schemas": len(PARSED_SCHEMAS),
        "total_databases": total_databases,
        "total_tables": total_tables,
        "total_attributes": total_attributes,
        "total_storage_bytes": total_storage,
        "constraint_distribution": constraint_stats,
        "data_type_distribution": data_type_stats,
        "memory_usage": {
            "current_schemas": len(PARSED_SCHEMAS),
            "max_schemas_limit": MAX_SCHEMAS_IN_MEMORY,
            "usage_percentage": (len(PARSED_SCHEMAS) / MAX_SCHEMAS_IN_MEMORY) * 100
        }
    }