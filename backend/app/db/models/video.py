"""
SatQuery AI — Video Database Models (videos, video_frames, video_flags)
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class VideoRecord(Base):
    """Stores metadata and file location for an uploaded video file."""
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_sec: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fps: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    codec: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    # Relationships
    frames: Mapped[List["VideoFrameRecord"]] = relationship(
        "VideoFrameRecord",
        back_populates="video",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    flags: Mapped[List["VideoFlagRecord"]] = relationship(
        "VideoFlagRecord",
        back_populates="video",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class VideoFrameRecord(Base):
    """Stores sampled and representative keyframe metadata."""
    __tablename__ = "video_frames"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_sec: Mapped[float] = mapped_column(Float, nullable=False)
    is_keyframe: Mapped[bool] = mapped_column(Boolean, default=False)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    video: Mapped["VideoRecord"] = relationship("VideoRecord", back_populates="frames")


class VideoFlagRecord(Base):
    """Stores flagged important-moment events, time intervals, and visual evidence paths."""
    __tablename__ = "video_flags"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    flag_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    start_timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    end_timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    start_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    end_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    peak_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    event_score: Mapped[float] = mapped_column(Float, nullable=False)
    keyframe_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overlay_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mask_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    box_2d: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    model_scores: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    video: Mapped["VideoRecord"] = relationship("VideoRecord", back_populates="flags")
