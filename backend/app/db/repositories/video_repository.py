"""
SatQuery AI — VideoRepository
Encapsulates database operations for videos, video frames, and event flags.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.video import VideoRecord, VideoFrameRecord, VideoFlagRecord
from backend.app.schemas.video import VideoMetadata, VideoFlag
from backend.app.logging import logger


class VideoRepository:
    """Repository for managing video files, keyframes, and flagged events in PostgreSQL."""

    @staticmethod
    async def create_or_update_video(
        session: AsyncSession,
        job_id: str,
        filename: str,
        file_path: str,
        metadata: VideoMetadata,
        video_id: Optional[str] = None
    ) -> VideoRecord:
        """Creates or updates a VideoRecord for a given job."""
        stmt = select(VideoRecord).where(VideoRecord.job_id == job_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            record = VideoRecord(
                id=video_id or job_id,
                job_id=job_id,
                filename=filename,
                file_path=file_path,
                duration_sec=metadata.duration_sec,
                fps=metadata.fps,
                width=metadata.width,
                height=metadata.height,
                frame_count=metadata.frame_count,
                codec=metadata.codec
            )
            session.add(record)
        else:
            record.filename = filename
            record.file_path = file_path
            record.duration_sec = metadata.duration_sec
            record.fps = metadata.fps
            record.width = metadata.width
            record.height = metadata.height
            record.frame_count = metadata.frame_count
            record.codec = metadata.codec

        await session.flush()
        return record

    @staticmethod
    async def save_video_frames(
        session: AsyncSession,
        video_id: str,
        frames: List[Dict[str, Any]]
    ) -> List[VideoFrameRecord]:
        """Saves sampled and representative keyframes for a video."""
        # Remove existing frames for this video to ensure clean update
        await session.execute(delete(VideoFrameRecord).where(VideoFrameRecord.video_id == video_id))

        records: List[VideoFrameRecord] = []
        for f in frames:
            rec = VideoFrameRecord(
                video_id=video_id,
                frame_index=f["frame_index"],
                timestamp_sec=f["timestamp_sec"],
                is_keyframe=f.get("is_keyframe", False),
                image_path=f["image_path"]
            )
            session.add(rec)
            records.append(rec)

        await session.flush()
        return records

    @staticmethod
    async def save_video_flags(
        session: AsyncSession,
        video_id: str,
        flags: List[VideoFlag]
    ) -> List[VideoFlagRecord]:
        """Saves flagged important-moment events."""
        await session.execute(delete(VideoFlagRecord).where(VideoFlagRecord.video_id == video_id))

        records: List[VideoFlagRecord] = []
        for flag in flags:
            rec = VideoFlagRecord(
                video_id=video_id,
                flag_id=flag.flag_id,
                start_timestamp=flag.start_timestamp,
                end_timestamp=flag.end_timestamp,
                start_frame=flag.start_frame,
                end_frame=flag.end_frame,
                peak_frame=flag.peak_frame,
                label=flag.label,
                reason=flag.reason,
                event_score=flag.event_score,
                keyframe_path=flag.keyframe_url,
                overlay_path=flag.overlay_url,
                mask_path=flag.mask_url,
                box_2d=flag.box_2d,
                model_scores=flag.model_scores,
                metadata_json=flag.metadata
            )
            session.add(rec)
            records.append(rec)

        await session.flush()
        return records

    @staticmethod
    async def get_video_by_job_id(
        session: AsyncSession,
        job_id: str
    ) -> Optional[VideoRecord]:
        """Retrieves a VideoRecord with its associated frames and flags."""
        stmt = (
            select(VideoRecord)
            .where(VideoRecord.job_id == job_id)
            .options(
                selectinload(VideoRecord.frames),
                selectinload(VideoRecord.flags)
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
