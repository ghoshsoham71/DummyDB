from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any, Union
from enum import Enum

class ConstraintType(str, Enum):
    PRIMARY_KEY = "PRIMARY_KEY"
    FOREIGN_KEY = "FOREIGN_KEY"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    NOT_NULL = "NOT_NULL"
    DEFAULT = "DEFAULT"

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

class ColumnConstraint(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    type: ConstraintType
    definition: str
    referenced_table: Optional[str] = None
    referenced_column: Optional[str] = None

class ColumnAttribute(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str
    data_type: str
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    nullable: bool = True
    default_value: Optional[str] = None
    auto_increment: bool = False
    constraints: List[ColumnConstraint] = Field(default_factory=list)
    enum_values: Optional[List[str]] = None
    comment: Optional[str] = None

class TableSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str
    columns: Dict[str, ColumnAttribute]
    primary_keys: List[str] = Field(default_factory=list)
    foreign_keys: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    unique_constraints: List[List[str]] = Field(default_factory=list)
    check_constraints: List[str] = Field(default_factory=list)
    indexes: List[Dict[str, Any]] = Field(default_factory=list)
    comment: Optional[str] = None

class DatabaseSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str
    tables: Dict[str, TableSchema]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SchemaCollection(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    databases: Dict[str, DatabaseSchema]
    version: str = "1.0"
    generated_at: str
    total_databases: int
    total_tables: int

class ParseRequest(BaseModel):
    sql_content: str
    database_name: Optional[str] = None

class ParseResponse(BaseModel):
    success: bool
    schema_id: Optional[str] = None
    message: str
    processing_time: float
    statistics: Dict[str, Any] = {}
    file_path: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    schemas_in_memory: int

class ErrorResponse(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    error: str
    details: Optional[str] = None
    code: int
