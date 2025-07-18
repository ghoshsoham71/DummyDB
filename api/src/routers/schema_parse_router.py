import asyncio
import json
import time
import os
import tempfile
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Response, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
from starlette.background import BackgroundTask
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.lib.schemas import ParseRequest, ParseResponse, ErrorResponse
from src.utils.schema_parse import SQLSchemaParser

# Create router
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Dependency to get parser
async def get_parser() -> SQLSchemaParser:
    # In the router, we'll get the parser from the app state
    # This will be initialized in the app.py lifespan function
    from src.app import parser_instance
    if parser_instance is None:
        raise HTTPException(status_code=500, detail="Parser not initialized")
    return parser_instance

@router.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

@router.post("/parse", response_model=ParseResponse)
@limiter.limit("10/minute")
async def parse_sql_schema(
    request: Request,
    parse_request: ParseRequest,
    parser: SQLSchemaParser = Depends(get_parser)
) -> ParseResponse:
    """
    Parse SQL DDL content and return structured schema
    
    - **sql_content**: SQL DDL content to parse
    - **database_name**: Optional database name override
    """
    start_time = time.time()
    
    try:
        schema_collection = await parser.parse_sql_content(
            parse_request.sql_content,
            parse_request.database_name
        )
        
        processing_time = time.time() - start_time
        
        # Calculate statistics
        stats = {
            "databases": len(schema_collection.databases),
            "tables": sum(len(db.tables) for db in schema_collection.databases.values()),
            "columns": sum(
                len(table.columns) 
                for db in schema_collection.databases.values()
                for table in db.tables.values()
            )
        }
        
        return ParseResponse(
            success=True,
            parse_schema=schema_collection,
            message="Schema parsed successfully",
            processing_time=processing_time,
            statistics=stats
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        return ParseResponse(
            success=False,
            parse_schema=None,
            message=f"Failed to parse schema: {str(e)}",
            processing_time=processing_time,
            statistics={}
        )

@router.post("/parse-file", response_model=ParseResponse)
@limiter.limit("5/minute")
async def parse_sql_file(
    request: Request,
    file: UploadFile = File(..., description="SQL file to parse"),
    database_name: Optional[str] = None,
    parser: SQLSchemaParser = Depends(get_parser)
) -> ParseResponse:
    """
    Parse SQL file and return structured schema
    
    - **file**: SQL file to parse (.sql extension required)
    - **database_name**: Optional database name override
    """
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
        
        schema_collection = await parser.parse_sql_content(sql_content, database_name)
        
        processing_time = time.time() - start_time
        
        # Calculate statistics
        stats = {
            "databases": len(schema_collection.databases),
            "tables": sum(len(db.tables) for db in schema_collection.databases.values()),
            "columns": sum(
                len(table.columns) 
                for db in schema_collection.databases.values()
                for table in db.tables.values()
            ),
            "file_size": len(content)
        }
        
        return ParseResponse(
            success=True,
            parse_schema=schema_collection,
            message=f"File '{file.filename}' parsed successfully",
            processing_time=processing_time,
            statistics=stats
        )
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be valid UTF-8 encoded text"
        )
    except Exception as e:
        processing_time = time.time() - start_time
        return ParseResponse(
            success=False,
            parse_schema=None,
            message=f"Failed to parse file: {str(e)}",
            processing_time=processing_time,
            statistics={}
        )

@router.post("/parse-to-json")
@limiter.limit("5/minute")
async def parse_to_json_file(
    request: Request,
    file: UploadFile = File(..., description="SQL file to parse"),
    database_name: Optional[str] = None,
    parser: SQLSchemaParser = Depends(get_parser)
) -> FileResponse:
    """
    Parse SQL file and return JSON schema file
    
    - **file**: SQL file to parse (.sql extension required)
    - **database_name**: Optional database name override
    
    Returns downloadable JSON file
    """
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
        
        schema_collection = await parser.parse_sql_content(sql_content, database_name)
        
        # Generate JSON filename
        base_filename = file.filename.replace('.sql', '') if file.filename else 'schema'
        json_filename = f"{base_filename}_schema.json"
        
        # Save to temporary file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(schema_collection.model_dump(), temp_file, indent=2)
            temp_filename = temp_file.name
        
        # Return file response
        from starlette.background import BackgroundTask
        return FileResponse(
            path=temp_filename,
            filename=json_filename,
            media_type='application/json',
            background=BackgroundTask(os.unlink, temp_filename)  # Cleanup after sending
        )
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be valid UTF-8 encoded text"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse file: {str(e)}"
        )
