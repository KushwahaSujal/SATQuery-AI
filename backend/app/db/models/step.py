"""
SatQuery AI — ExecutionStep Model
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True
    )

    # Back-reference
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="execution_steps")
