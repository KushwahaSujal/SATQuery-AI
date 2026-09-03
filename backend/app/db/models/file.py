"""
SatQuery AI — UploadedFile Model
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    band_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    crs: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    bounds: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Back-reference
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="uploaded_files")
