"""
SatQuery AI — Video upload, analysis, keyframes and streaming.

Split out of the former monolithic api/routes.py (1246 lines).
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.requests import AnalyzeRequest
from backend.app.schemas.responses import (
    UploadResponse,
    AnalyzeResponse,
    HealthResponse,
    ModelsListResponse,
    RasterMetadataResponse,
)
from backend.app.schemas.agent import JobStatus
from backend.app.geo.raster import RasterInspector
from backend.app.geo.modality import ModalityDetector
from backend.app.geo.display import save_display_preview
from backend.app.agent.state import AgentState
from backend.app.agent.controller import agent_controller
from backend.app.ml.registry import model_registry
from backend.app.ml.device import get_device
from backend.app.artifacts.manager import artifact_manager
from backend.app.config import settings
from backend.app.exceptions import (
    SatQueryException,
    InvalidInputError,
    InvalidRequestError,
    UnsupportedFormatError,
    UnsupportedMediaError,
    PairValidationError,
    InvalidTemporalPairError,
    TemporalAlignmentRequiredError,
    ModelUnavailableError,
    ModelNotConfiguredError,
    InferenceError,
    ModelInferenceError,
    IndexNotAvailableError,
    VisualizationNotAvailableError,
    ArtifactNotFoundError,
    NoRelevantEventsFoundError,
    JobNotFoundError,
    DatabaseUnavailableError,
)
from backend.app.logging import logger
from backend.app.db.session import get_db, check_database_connection
from backend.app.db.repositories.job_repository import JobRepository
from backend.app.db.repositories.video_repository import VideoRepository
from backend.app.schemas.video import (
    VideoAnalysisRequest,
    VideoAnalysisResponse,
    VideoMetadata,
    VideoSamplingConfig,
    VideoFlagConfig,
)
from backend.app.workflows.video_analysis import VideoAnalysisWorkflow
from backend.app.video.decoder import VideoDecoder
from backend.app.visualization import (
    VisualizationRegistry,
    CompositeRenderer,
    SpectralIndexEngine,
    SARVisualizationEngine,
    HeatmapEngine,
    ComparisonEngine,
    InspectorEngine,
    ExportEngine,
    LayerProvenance,
    VisualizationType,
    LayerMetadata,
)
from backend.app.visualization.composites import _apply_percentile_stretch
from backend.app.db.repositories.visualization_repository import VisualizationRepository
from pydantic import BaseModel
from PIL import Image
import numpy as np

router = APIRouter(prefix="/api", tags=["SatQuery AI"])

router = APIRouter(tags=["SatQuery AI"])


@router.post("/video/upload")
async def upload_video(
    file: UploadFile = File(...),
    request_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Dedicated video footage upload endpoint.
    Accepts .mp4 or .mov video file.
    Validates file extension, initializes job workspace, decodes metadata,
    and initializes an AnalysisJob and VideoRecord in PostgreSQL.
    """
    orig_name = Path(file.filename).name
    ext = Path(orig_name).suffix.lower()

    if ext not in settings.video.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video format '{ext}'. Allowed formats: {settings.video.allowed_extensions}"
        )

    req_id = request_id or str(uuid.uuid4())
    dirs = artifact_manager.init_job_workspace(req_id)
    video_dir = dirs["root"] / "video"
    video_dir.mkdir(parents=True, exist_ok=True)

    dest_path = video_dir / orig_name
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        with VideoDecoder(dest_path) as decoder:
            meta = decoder.metadata
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decode uploaded video '{orig_name}': {e}"
        )

    # Persist job & video records
    try:
        await JobRepository.create_or_get_job(
            db,
            job_id=req_id,
            task_type="video_grounding",
            status="UPLOADED"
        )
        await VideoRepository.create_or_update_video(
            db,
            job_id=req_id,
            filename=orig_name,
            file_path=str(dest_path),
            metadata=meta,
            video_id=req_id
        )
    except Exception as e:
        logger.warning(f"Database persistence warning during video upload: {e}")

    return {
        "job_id": req_id,
        "filename": orig_name,
        "video_metadata": meta.model_dump(),
        "video_url": f"/api/video/{req_id}/stream"
    }


@router.post("/video/analyze", response_model=VideoAnalysisResponse)
async def analyze_video(
    file: Optional[UploadFile] = File(None),
    request_id: Optional[str] = Form(None),
    query: str = Form(...),
    sample_fps: Optional[float] = Form(None),
    max_frames: Optional[int] = Form(None),
    min_persistence_frames: Optional[int] = Form(None),
    min_event_score: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Dedicated video analysis endpoint.
    Processes video footage with natural-language query using Grounding DINO, V4 reasoning,
    SAM 2.1 video propagation, and temporal event flagging.
    Preserves all existing image endpoints.
    """
    req_id = request_id or str(uuid.uuid4())
    dirs = artifact_manager.init_job_workspace(req_id)
    video_dir = dirs["root"] / "video"
    video_dir.mkdir(parents=True, exist_ok=True)

    # Resolve video path
    video_path: Optional[Path] = None

    if file is not None and file.filename:
        orig_name = Path(file.filename).name
        ext = Path(orig_name).suffix.lower()
        if ext not in settings.video.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported video format '{ext}'. Allowed: {settings.video.allowed_extensions}"
            )
        dest_path = video_dir / orig_name
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        video_path = dest_path
    elif request_id:
        # Check existing video record or file in job directory
        candidates = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.mov"))
        if candidates:
            video_path = candidates[0]

    if video_path is None or not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No video footage provided. Upload a video file (.mp4, .mov) or specify a valid request_id with uploaded video."
        )

    # Configure sampling & flagging
    sampling_cfg = VideoSamplingConfig(
        sample_fps=sample_fps or settings.video.sampling.sample_fps,
        max_frames=max_frames or settings.video.sampling.max_frames,
        analysis_stride=settings.video.sampling.analysis_stride,
        event_refinement_window=settings.video.sampling.event_refinement_window
    )
    flagging_cfg = VideoFlagConfig(
        min_persistence_frames=min_persistence_frames or settings.video.flagging.min_persistence_frames,
        min_persistence_seconds=settings.video.flagging.min_persistence_seconds,
        max_gap_frames=settings.video.flagging.max_gap_frames,
        max_gap_seconds=settings.video.flagging.max_gap_seconds,
        min_event_score=min_event_score or settings.video.flagging.min_event_score
    )

    # Ensure job record is updated in DB
    try:
        await JobRepository.create_or_get_job(
            db,
            job_id=req_id,
            query=query,
            status="RUNNING"
        )
    except Exception as e:
        logger.warning(f"Database error updating job status: {e}")

    # Execute workflow
    response = await VideoAnalysisWorkflow.execute(
        video_path=video_path,
        query=query,
        job_id=req_id,
        sampling_config=sampling_cfg,
        flagging_config=flagging_cfg,
        db_session=db
    )

    return response


@router.get("/video/{job_id}", response_model=VideoAnalysisResponse)
@router.get("/video/{job_id}/status", response_model=VideoAnalysisResponse)
@router.get("/video/{job_id}/results", response_model=VideoAnalysisResponse)
@router.get("/video/{job_id}/events", response_model=VideoAnalysisResponse)
async def get_video_analysis_result(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves persisted video analysis result and event flags."""
    video_rec = await VideoRepository.get_video_by_job_id(db, job_id)
    if not video_rec:
        raise JobNotFoundError(
            job_id=job_id,
            message=f"Video analysis job '{job_id}' not found.",
            details={"job_id": job_id}
        )

    # Map database records to response schema
    meta = VideoMetadata(
        filename=video_rec.filename,
        duration_sec=video_rec.duration_sec,
        fps=video_rec.fps,
        width=video_rec.width,
        height=video_rec.height,
        frame_count=video_rec.frame_count,
        codec=video_rec.codec
    )

    flags: List[VideoFlag] = []
    for f in video_rec.flags:
        flags.append(VideoFlag(
            flag_id=f.flag_id,
            video_id=f.video_id,
            start_timestamp=f.start_timestamp,
            end_timestamp=f.end_timestamp,
            start_frame=f.start_frame,
            end_frame=f.end_frame,
            peak_frame=f.peak_frame,
            label=f.label,
            reason=f.reason,
            event_score=f.event_score,
            keyframe_url=f.keyframe_path,
            overlay_url=f.overlay_path,
            mask_url=f.mask_path,
            box_2d=f.box_2d,
            model_scores=f.model_scores or {},
            metadata=f.metadata_json or {}
        ))

    artifacts = artifact_manager.list_artifacts(job_id)

    return VideoAnalysisResponse(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        task=TaskType.VIDEO_GROUNDING,
        workflow_reason=f"Retrieved {len(flags)} persisted event flags from database.",
        video_metadata=meta,
        flags=flags,
        models_used=["grounding_dino", "sam2"],
        execution_trace=[],
        warnings=[],
        errors=[],
        artifacts=artifacts
    )


@router.get("/video/{job_id}/keyframes")
async def get_video_keyframes(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves representative keyframes for a video job."""
    video_rec = await VideoRepository.get_video_by_job_id(db, job_id)
    if not video_rec:
        raise JobNotFoundError(job_id=job_id, details={"job_id": job_id})
    return {
        "job_id": job_id,
        "keyframes": [
            {
                "frame_index": fr.frame_index,
                "timestamp_sec": fr.timestamp_sec,
                "is_keyframe": fr.is_keyframe,
                "image_path": fr.image_path
            }
            for fr in video_rec.frames if fr.is_keyframe
        ]
    }


@router.get("/video/{job_id}/stream")
async def stream_video(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Streams video footage with HTTP 206 Partial Content support for smooth browser timeline seeking.
    """
    video_path: Optional[Path] = None

    # Try DB lookup first
    try:
        v_rec = await VideoRepository.get_video_by_job_id(db, job_id)
        if v_rec and Path(v_rec.file_path).exists():
            video_path = Path(v_rec.file_path)
    except Exception as e:
        logger.debug(f"DB lookup for video stream: {e}")

    # Fallback to filesystem
    if not video_path or not video_path.exists():
        dirs = artifact_manager.get_job_dir(job_id)
        candidates = list((dirs / "video").glob("*.mp4")) + list((dirs / "video").glob("*.mov"))
        if candidates:
            video_path = candidates[0]

    if not video_path or not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found for job ID '{job_id}'."
        )

    media_type = "video/mp4" if video_path.suffix.lower() == ".mp4" else "video/quicktime"
    return FileResponse(path=str(video_path), media_type=media_type)
