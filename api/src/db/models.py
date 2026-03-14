# api/src/db/models.py

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum

class Base(DeclarativeBase):
    pass

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(str, enum.Enum):
    SCHEMA_INFERENCE = "schema_inference"
    SEED_GENERATION = "seed_generation"
    SYNTHETIC_GENERATION = "synthetic_generation"
    QUALITY_AUDIT = "quality_audit"

class SchemaSpec(Base):
    __tablename__ = "schema_specs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    raw_content: Mapped[str] = mapped_column(Text)
    canonical_schema: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[Optional[str]] = mapped_column(String(255))

    jobs: Mapped[List["GenerationJob"]] = relationship(back_populates="schema")

class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schema_id: Mapped[str] = mapped_column(String(255))
    job_type: Mapped[JobType] = mapped_column(Enum(JobType))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    parameters: Mapped[dict] = mapped_column(JSON)
    result_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    schema: Mapped["SchemaSpec"] = relationship(back_populates="jobs")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="job")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generation_jobs.id"))
    step_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["GenerationJob"] = relationship(back_populates="audit_logs")
