import json
import os
import time
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.lib.schemas import ParseResponse, HealthResponse, ParseRequest
from src.utils.schema_parse import SQLSchemaParser

# Global storage for parsed schemas
PARSED_SCHEMAS: Dict[str, Any] = {}
SCHEMA_COUNTER = 0

# Create router
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize parser instance
parser_instance = SQLSchemaParser()

@router.get("/health", response_model=HealthResponse)
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint with schema storage info"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        schemas_in_memory=len(PARSED_SCHEMAS)
    )

@router.post("/parse", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_sql_schema(
    request: Request,
    file: UploadFile = File(..., description="SQL file to parse (.sql extension required)")
) -> ParseResponse:
    """
    Parse uploaded SQL file and store schema in local JSON file and memory
    
    - **file**: SQL file to parse (.sql extension required)
    
    Returns:
    - Schema ID for accessing the parsed schema
    - File path where JSON schema is saved
    - Processing statistics
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
        # Read file content
        content = await file.read()
        sql_content = content.decode('utf-8')
        
        # Create temporary SQL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_sql_file:
            temp_sql_file.write(sql_content)
            temp_sql_path = temp_sql_file.name
        
        try:
            # Parse the SQL file
            schema = parser_instance.parse_sql_file(temp_sql_path, output_dir="./schemas")
            
            # Generate unique schema ID
            SCHEMA_COUNTER += 1
            schema_id = f"schema_{SCHEMA_COUNTER}_{int(time.time())}"
            
            # Store schema in memory for global access
            PARSED_SCHEMAS[schema_id] = {
                "schema": schema,
                "filename": file.filename,
                "created_at": time.time(),
                "file_size": len(content)
            }
            
            # Determine JSON file path
            base_filename = Path(file.filename).stem
            json_filename = f"{base_filename}_schema.json"
            
            # Ensure schemas directory exists
            os.makedirs("./schemas", exist_ok=True)
            json_file_path = os.path.join("./schemas", json_filename)
            
            # Save schema to local JSON file
            with open(json_file_path, 'w', encoding='utf-8') as json_file:
                json.dump(schema, json_file, indent=2)
            
            processing_time = time.time() - start_time
            
            # Calculate statistics
            stats = {
                "databases": len(schema.get("databases", [])),
                "tables": sum(len(db.get("tables", [])) for db in schema.get("databases", [])),
                "columns": sum(
                    len(table.get("attributes", []))
                    for db in schema.get("databases", [])
                    for table in db.get("tables", [])
                ),
                "file_size": len(content),
                "schema_id": schema_id
            }
            
            return ParseResponse(
                success=True,
                schema_id=schema_id,
                message=f"Schema parsed and saved successfully. Access via schema ID: {schema_id}",
                processing_time=processing_time,
                statistics=stats,
                file_path=json_file_path
            )
            
        finally:
            # Clean up temporary SQL file
            if os.path.exists(temp_sql_path):
                os.unlink(temp_sql_path)
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be valid UTF-8 encoded text"
        )
    except Exception as e:
        processing_time = time.time() - start_time
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
async def list_schemas(request: Request):
    """List all schemas stored in memory"""
    schema_list = []
    
    for schema_id, schema_data in PARSED_SCHEMAS.items():
        schema_info = {
            "schema_id": schema_id,
            "filename": schema_data["filename"],
            "created_at": schema_data["created_at"],
            "file_size": schema_data["file_size"],
            "databases": len(schema_data["schema"].get("databases", [])),
            "tables": sum(len(db.get("tables", [])) for db in schema_data["schema"].get("databases", []))
        }
        schema_list.append(schema_info)
    
    return {
        "schemas": schema_list,
        "total_schemas": len(schema_list)
    }

@router.get("/schemas/{schema_id}")
@limiter.limit("50/minute")
async def get_schema(request: Request, schema_id: str):
    """Get specific schema by ID"""
    if schema_id not in PARSED_SCHEMAS:
        raise HTTPException(
            status_code=404,
            detail=f"Schema with ID '{schema_id}' not found"
        )
    
    schema_data = PARSED_SCHEMAS[schema_id]
    return {
        "schema_id": schema_id,
        "schema": schema_data["schema"],
        "metadata": {
            "filename": schema_data["filename"],
            "created_at": schema_data["created_at"],
            "file_size": schema_data["file_size"]
        }
    }

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
    
    return {
        "message": f"Schema '{schema_id}' deleted successfully",
        "deleted_schema_info": {
            "filename": deleted_schema["filename"],
            "created_at": deleted_schema["created_at"]
        }
    }

# Utility functions for accessing schemas throughout the codebase

def get_schema_by_id(schema_id: str) -> Optional[Dict[str, Any]]:
    """
    Get schema by ID - can be used throughout the codebase
    
    Args:
        schema_id: The schema identifier
        
    Returns:
        Schema dictionary or None if not found
    """
    schema_data = PARSED_SCHEMAS.get(schema_id)
    return schema_data["schema"] if schema_data else None

def get_all_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Get all schemas - can be used throughout the codebase
    
    Returns:
        Dictionary mapping schema IDs to schema data
    """
    return PARSED_SCHEMAS.copy()

def get_latest_schema() -> Optional[Dict[str, Any]]:
    """
    Get the most recently parsed schema
    
    Returns:
        Latest schema dictionary or None if no schemas exist
    """
    if not PARSED_SCHEMAS:
        return None
    
    # Find schema with highest timestamp
    latest_id = max(PARSED_SCHEMAS.keys(), key=lambda x: PARSED_SCHEMAS[x]["created_at"])
    return PARSED_SCHEMAS[latest_id]["schema"]

def search_schemas_by_table(table_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Search for schemas containing a specific table name
    
    Args:
        table_name: Name of the table to search for
        
    Returns:
        Dictionary of matching schemas
    """
    matching_schemas = {}
    
    for schema_id, schema_data in PARSED_SCHEMAS.items():
        schema = schema_data["schema"]
        
        # Check if any database contains the table
        for db in schema.get("databases", []):
            for table in db.get("tables", []):
                if table.get("name", "").lower() == table_name.lower():
                    matching_schemas[schema_id] = schema_data
                    break
            
            if schema_id in matching_schemas:
                break
    
    return matching_schemas

def get_schema_statistics() -> Dict[str, Any]:
    """
    Get overall statistics for all stored schemas
    
    Returns:
        Dictionary containing aggregate statistics
    """
    if not PARSED_SCHEMAS:
        return {
            "total_schemas": 0,
            "total_databases": 0,
            "total_tables": 0,
            "total_attributes": 0
        }
    
    total_databases = 0
    total_tables = 0
    total_attributes = 0
    
    for schema_data in PARSED_SCHEMAS.values():
        schema = schema_data["schema"]
        databases = schema.get("databases", [])
        
        total_databases += len(databases)
        
        for db in databases:
            tables = db.get("tables", [])
            total_tables += len(tables)
            
            for table in tables:
                total_attributes += len(table.get("attributes", []))
    
    return {
        "total_schemas": len(PARSED_SCHEMAS),
        "total_databases": total_databases,
        "total_tables": total_tables,
        "total_attributes": total_attributes
    }