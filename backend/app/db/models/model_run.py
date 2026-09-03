"""
SatQuery AI — ModelRun Model
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    device: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Back-reference
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="model_runs")
