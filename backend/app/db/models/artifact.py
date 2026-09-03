"""
SatQuery AI — Artifact Model
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filesystem_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Back-reference
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="artifacts")
