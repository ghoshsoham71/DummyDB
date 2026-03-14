# api/src/lib/schemas.py (Enhanced version)

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

class ConstraintType(str, Enum):
    PRIMARY_KEY = "PRIMARY_KEY"
    FOREIGN_KEY = "FOREIGN_KEY"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    NOT_NULL = "NOT_NULL"
    DEFAULT = "DEFAULT"
    AUTO_INCREMENT = "AUTO_INCREMENT"

class DataType(str, Enum):
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    DECIMAL = "DECIMAL"
    NUMERIC = "NUMERIC"
    REAL = "REAL"
    DOUBLE = "DOUBLE"
    FLOAT = "FLOAT"
    VARCHAR = "VARCHAR"
    CHAR = "CHAR"
    TEXT = "TEXT"
    DATE = "DATE"
    TIME = "TIME"
    TIMESTAMP = "TIMESTAMP"
    BOOLEAN = "BOOLEAN"
    BLOB = "BLOB"
    JSON = "JSON"
    UUID = "UUID"
    ENUM = "ENUM"

# Schema Parser Schemas
class ParseRequest(BaseModel):
    sql_content: str
    database_name: Optional[str] = None

class SupabaseParseRequest(BaseModel):
    connection_string: str
    save_to_disk: bool = True
    overwrite_existing: bool = False

class MongoDBParseRequest(BaseModel):
    connection_string: str
    database_name: Optional[str] = None
    sample_size: int = Field(default=100, ge=1, le=10000)
    save_to_disk: bool = True
    overwrite_existing: bool = False

class Neo4jParseRequest(BaseModel):
    uri: str = Field(default="bolt://localhost:7687")
    username: str = Field(default="neo4j")
    password: str = Field(default="")
    database: Optional[str] = None
    save_to_disk: bool = True
    overwrite_existing: bool = False

class ParseResponse(BaseModel):
    success: bool
    schema_id: Optional[str] = None
    message: str
    processing_time: float
    statistics: Dict[str, Any] = Field(default_factory=dict)
    data: Optional[str] = None
    file_path: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    schemas_in_memory: int
    additional_info: Optional[Dict[str, Any]] = None

# SyntheticGenerationResponse used by synthetic_router.py
class SyntheticGenerationResponse(BaseModel):
    success: bool
    generation_id: Optional[str] = None
    message: str
    processing_time: float
    statistics: Dict[str, Any] = Field(default_factory=dict)
    file_paths: List[str] = Field(default_factory=list)
    quality_score: Optional[float] = None

# SeedDataResponse used by seed_data_router.py
class SeedDataResponse(BaseModel):
    success: bool
    seed_id: Optional[str] = None
    message: str
    processing_time: float
    statistics: Dict[str, Any] = Field(default_factory=dict)
    file_paths: List[str] = Field(default_factory=list)

# Data Evaluation Schemas
class EvaluationRequest(BaseModel):
    real_data_dir: str
    synthetic_data_dir: str
    evaluation_type: str = Field(default="comprehensive", pattern="^(basic|comprehensive|advanced)$")
    output_report: Optional[str] = None

class EvaluationResponse(BaseModel):
    success: bool
    evaluation_id: Optional[str] = None
    message: str
    processing_time: float
    overall_quality_score: Optional[float] = None
    table_scores: Dict[str, float] = Field(default_factory=dict)
    report_path: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)

# PipelineResponse kept if referenced elsewhere, but request removed
class PipelineResponse(BaseModel):
    success: bool
    pipeline_id: Optional[str] = None
    message: str
    total_processing_time: float
    step_results: List[Dict[str, Any]] = Field(default_factory=list)
    final_outputs: Dict[str, Any] = Field(default_factory=dict)

# File Management Schemas
class FileInfo(BaseModel):
    filename: str
    file_path: str
    file_size: int
    created_at: datetime
    content_hash: str
    file_type: str

class FileListResponse(BaseModel):
    success: bool
    files: List[FileInfo] = Field(default_factory=list)
    total_files: int
    total_size: int

# Error Response Schema
class ErrorResponse(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    error: str
    details: Optional[str] = None
    code: int
    timestamp: datetime = Field(default_factory=datetime.now)

# Configuration Schemas
class GeneratorConfig(BaseModel):
    type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True

class QualityMetrics(BaseModel):
    overall_score: float = Field(ge=0.0, le=1.0)
    distribution_similarity: float = Field(ge=0.0, le=1.0)
    correlation_preservation: float = Field(ge=0.0, le=1.0)
    privacy_score: Optional[float] = Field(None, ge=0.0, le=1.0)

# Batch processing and system stats removed

# Statistics and Monitoring Schemas
class SystemStats(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    uptime: float

class JobStatus(BaseModel):
    job_id: str
    status: str = Field(pattern="^(pending|running|completed|failed|cancelled)$")
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None