# api/src/lib/schemas.py (Enhanced version)

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Dict, List, Optional, Any, Union
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

# Synthetic Data Generation Schemas
class SyntheticGenerationRequest(BaseModel):
    schema_id: str
    scale_factor: float = Field(default=2.0, ge=0.1, le=100.0)
    num_rows: Optional[Dict[str, int]] = None
    synthesizer_type: str = Field(default="HMA", regex="^(HMA|GAUSSIAN|CTGAN)$")
    output_format: str = Field(default="csv", regex="^(csv|json|parquet)$")
    seed: Optional[int] = None

class SyntheticGenerationResponse(BaseModel):
    success: bool
    generation_id: Optional[str] = None
    message: str
    processing_time: float
    statistics: Dict[str, Any] = Field(default_factory=dict)
    file_paths: List[str] = Field(default_factory=list)
    quality_score: Optional[float] = None

# Seed Data Generation Schemas
class SeedDataRequest(BaseModel):
    schema_id: str
    base_rows: int = Field(default=10, ge=1, le=10000)
    locale: str = Field(default="en_US")
    custom_generators: Optional[Dict[str, Dict[str, Any]]] = None
    output_format: str = Field(default="csv", regex="^(csv|json)$")

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
    evaluation_type: str = Field(default="comprehensive", regex="^(basic|comprehensive|advanced)$")
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

# Data Pipeline Schemas
class PipelineRequest(BaseModel):
    schema_id: str
    pipeline_name: str
    steps: List[str] = Field(default=["seed_generation", "synthetic_generation", "evaluation"])
    config: Dict[str, Any] = Field(default_factory=dict)

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

# Batch Processing Schemas
class BatchProcessRequest(BaseModel):
    schema_ids: List[str]
    operation_type: str = Field(regex="^(seed|synthetic|evaluate|pipeline)$")
    config: Dict[str, Any] = Field(default_factory=dict)
    parallel: bool = True
    max_workers: int = Field(default=4, ge=1, le=10)

class BatchProcessResponse(BaseModel):
    success: bool
    batch_id: str
    message: str
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    job_results: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time: float

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
    status: str = Field(regex="^(pending|running|completed|failed|cancelled)$")
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None