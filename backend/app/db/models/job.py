"""
SatQuery AI — AnalysisJob Model
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    status: Mapped[str] = mapped_column(String(32), index=True, default="CREATED")
    task_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    uploaded_files: Mapped[List["UploadedFile"]] = relationship(
        "UploadedFile",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    model_runs: Mapped[List["ModelRun"]] = relationship(
        "ModelRun",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    execution_steps: Mapped[List["ExecutionStep"]] = relationship(
        "ExecutionStep",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    analysis_results: Mapped[List["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
