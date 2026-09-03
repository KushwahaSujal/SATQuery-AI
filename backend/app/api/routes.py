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
from backend.app.models.registry import model_registry
from backend.app.models.device import get_device
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


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Returns server health status, compute device, database connection status, and model availability."""
    device = get_device()
    models_avail = {k: model_registry.is_model_available(k) for k in settings.models.keys()}
    db_connected = await check_database_connection()

    return HealthResponse(
        status="ok",
        version=settings.app.version,
        environment=settings.app.environment,
        device=f"{device.type}:{device.index}" if device.index is not None else device.type,
        models_available=models_avail,
        database_connected=db_connected
    )


@router.get("/models", response_model=ModelsListResponse)
async def list_models():
    """Lists all registered models, their capabilities, tasks, required relationships, and checkpoint availability."""
    capabilities = model_registry.list_capabilities()
    return ModelsListResponse(models=capabilities)


@router.post("/upload", response_model=UploadResponse)
async def upload_rasters(
    files: List[UploadFile] = File(...),
    request_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure file upload endpoint.
    Accepts 1 or 2 GeoTIFF/TIFF/PNG/JPEG files.
    Performs filename sanitization, extension validation, workspace initialization,
    raster inspection, modality detection, and preview generation.
    Persists AnalysisJob and UploadedFile records in PostgreSQL.
    """
    if len(files) < 1 or len(files) > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SatQuery AI accepts between 1 and 2 raster images per analysis."
        )

    req_id = request_id or str(uuid.uuid4())
    dirs = artifact_manager.init_job_workspace(req_id)

    uploaded_filenames: List[str] = []
    metadata_responses: List[RasterMetadataResponse] = []
    db_files_payload: List[dict] = []

    for file in files:
        original_name = Path(file.filename).name
        ext = Path(original_name).suffix.lower()

        if ext not in settings.storage.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file extension '{ext}'. Allowed: {settings.storage.allowed_extensions}"
            )

        # Secure local destination
        dest_path = dirs["input"] / original_name
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Inspect raster
        try:
            meta = RasterInspector.inspect(dest_path)
            mod, conf, reason = ModalityDetector.detect(meta)

            # Generate RGB display preview
            arr, _ = RasterInspector.read_as_array(dest_path)
            preview_filename = f"{Path(original_name).stem}_preview.png"
            preview_path = dirs["overlays"] / preview_filename
            save_display_preview(arr, preview_path)

            uploaded_filenames.append(original_name)
            metadata_responses.append(
                RasterMetadataResponse(
                    filename=meta.filename,
                    format=meta.format,
                    width=meta.width,
                    height=meta.height,
                    bands=meta.bands,
                    dtype=meta.dtype,
                    crs=meta.crs,
                    bounds=meta.bounds,
                    transform=meta.transform,
                    resolution=meta.resolution,
                    nodata=meta.nodata,
                    band_descriptions=meta.band_descriptions,
                    tags=meta.tags,
                    detected_modality=mod,
                    modality_confidence=conf,
                    modality_reason=reason,
                    preview_url=f"/api/artifacts/{req_id}/overlays/{preview_filename}"
                )
            )

            db_files_payload.append({
                "original_filename": original_name,
                "stored_path": str(dest_path),
                "mime_type": f"image/{ext.lstrip('.')}",
                "file_size": dest_path.stat().st_size if dest_path.exists() else None,
                "width": meta.width,
                "height": meta.height,
                "band_count": meta.bands,
                "crs": meta.crs,
                "bounds": {"coordinates": meta.bounds} if meta.bounds else None,
            })

        except Exception as e:
            logger.error(f"Failed to inspect uploaded file '{original_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Error reading raster metadata from '{original_name}': {str(e)}"
            )

    # Persist in PostgreSQL
    try:
        await JobRepository.create_or_get_job(
            session=db,
            job_id=req_id,
            status="CREATED"
        )
        if db_files_payload:
            await JobRepository.save_uploaded_files(
                session=db,
                job_id=req_id,
                files_data=db_files_payload
            )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to persist uploaded files metadata to database: {e}")
        # Note: Non-blocking warning for upload if DB is temporarily unavailable,
        # but files are stored in workspace.

    return UploadResponse(
        request_id=req_id,
        uploaded_files=uploaded_filenames,
        metadata=metadata_responses
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_query(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """
    Primary analysis endpoint.
    Accepts user natural-language query and list of uploaded image filenames.
    Orchestrates deterministic routing, agent planning, tool execution, evidence fusion,
    visualization layer discovery, and PostgreSQL persistence.
    """
    req_id = request.request_id or str(uuid.uuid4())
    job_dir = artifact_manager.get_job_dir(req_id)
    input_dir = job_dir / "input"

    image_paths: List[str] = []
    for fname in request.image_filenames:
        clean_name = Path(fname).name
        fpath = input_dir / clean_name
        if not fpath.exists():
            raise ArtifactNotFoundError(
                artifact_name=clean_name,
                message=f"Image file '{clean_name}' not found in workspace for request '{req_id}'. Please upload it first.",
                details={"job_id": req_id, "missing_file": clean_name}
            )
        image_paths.append(str(fpath))

    state = AgentState(
        request_id=req_id,
        query=request.query,
        image_paths=image_paths,
        parameters=request.parameters
    )

    response = await agent_controller.run_pipeline(state)

    # Attach discovered visualization layers
    try:
        available_layers = VisualizationRegistry.discover_available_layers(
            request_id=req_id,
            input_paths=image_paths,
            metadata_list=state.metadata,
            models_used=state.selected_models,
            task=state.task.value if state.task else "unknown",
            evidence=state.evidence
        )
        response.visualizations = [l.model_dump() if hasattr(l, "model_dump") else l for l in available_layers]
    except Exception as e:
        logger.warning(f"Could not attach visualization layers: {e}")

    return response


@router.get("/jobs/{job_id}")
@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves current job status, execution steps, models used, and artifacts from PostgreSQL.
    Falls back to filesystem trace if database record is not yet present.
    """
    try:
        job = await JobRepository.get_job(db, job_id)
        if job:
            return {
                "request_id": job.id,
                "job_id": job.id,
                "status": job.status,
                "task": job.task_type,
                "query": job.query,
                "error_code": job.error_code,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "execution_steps": [
                    {
                        "id": s.id,
                        "step_name": s.step_name,
                        "status": s.status,
                        "model_name": s.model_name,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                        "duration_seconds": s.duration_seconds,
                        "metadata": s.metadata_json
                    }
                    for s in job.execution_steps
                ],
                "models_used": [m.model_name for m in job.model_runs],
                "result_available": len(job.analysis_results) > 0,
                "artifacts": [
                    {
                        "id": a.id,
                        "type": a.artifact_type,
                        "path": a.filesystem_path,
                        "created_at": a.created_at.isoformat() if a.created_at else None
                    }
                    for a in job.artifacts
                ]
            }
    except Exception as e:
        logger.warning(f"Database query failed for get_job_status: {e}")

    # Fallback to filesystem artifact manager if DB was unavailable or job not in DB
    trace = artifact_manager.load_trace_json(job_id)
    result = artifact_manager.load_result_json(job_id)

    if result:
        return {
            "request_id": job_id,
            "job_id": job_id,
            "status": result.get("status", JobStatus.COMPLETED.value),
            "trace": trace,
            "result_available": True,
            "result": result
        }
    if trace:
        return {
            "request_id": job_id,
            "job_id": job_id,
            "status": JobStatus.RUNNING.value,
            "trace": trace,
            "result_available": False
        }

    raise JobNotFoundError(job_id=job_id, details={"job_id": job_id})


@router.get("/results/{request_id}", response_model=AnalyzeResponse)
@router.get("/jobs/{request_id}/results", response_model=AnalyzeResponse)
async def get_job_results(request_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves full analysis result JSON from PostgreSQL.
    Falls back to filesystem result JSON if necessary.
    """
    try:
        res_rec = await JobRepository.get_analysis_result(db, request_id)
        if res_rec and res_rec.result_json:
            return AnalyzeResponse(**res_rec.result_json)
    except Exception as e:
        logger.warning(f"Database query failed for get_job_results: {e}")

    # Filesystem fallback
    data = artifact_manager.load_result_json(request_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No results found for request ID '{request_id}'."
        )
    return AnalyzeResponse(**data)


@router.get("/reports/{request_id}")
async def download_pdf_report(request_id: str, db: AsyncSession = Depends(get_db)):
    """
    Downloads the generated ReportLab PDF audit report using database-recorded path
    or filesystem resolution.
    """
    pdf_path = None

    # Check database-recorded artifact
    try:
        art = await JobRepository.get_artifact(db, request_id, "reports", ".pdf")
        if art and Path(art.filesystem_path).exists():
            pdf_path = Path(art.filesystem_path)
    except Exception as e:
        logger.debug(f"DB lookup for report artifact: {e}")

    # Filesystem fallback
    if not pdf_path or not pdf_path.exists():
        job_dir = artifact_manager.get_job_dir(request_id)
        fallback_path = job_dir / "reports" / f"{request_id}_audit_report.pdf"
        if fallback_path.exists():
            pdf_path = fallback_path

    if not pdf_path or not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF report not found for request ID '{request_id}'."
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"SatQuery_Report_{request_id}.pdf"
    )


@router.get("/trace/{job_id}")
async def get_job_trace(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves execution trace for a job from database or filesystem."""
    try:
        job = await JobRepository.get_job(db, job_id)
        if job and job.execution_steps:
            return {
                "job_id": job_id,
                "status": job.status,
                "execution_steps": [
                    {
                        "step_name": s.step_name,
                        "status": s.status,
                        "model_name": s.model_name,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                        "duration_seconds": s.duration_seconds,
                        "metadata": s.metadata_json
                    }
                    for s in job.execution_steps
                ]
            }
    except Exception as e:
        logger.warning(f"Database lookup for trace failed: {e}")

    trace = artifact_manager.load_trace_json(job_id)
    if trace is not None:
        return {"job_id": job_id, "execution_steps": trace}
    raise JobNotFoundError(job_id=job_id, details={"job_id": job_id})


@router.get("/artifacts/{request_id}/{artifact_type}/{filename}")
async def get_artifact_file(
    request_id: str,
    artifact_type: str,
    filename: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Serves generated overlays, GeoTIFF masks, GeoJSON, and previews using
    database-recorded paths or filesystem resolution.
    """
    clean_type = Path(artifact_type).name
    clean_file = Path(filename).name
    target = None

    # Check database-recorded artifact path
    try:
        art = await JobRepository.get_artifact(db, request_id, clean_type, clean_file)
        if art and Path(art.filesystem_path).exists():
            target = Path(art.filesystem_path)
    except Exception as e:
        logger.debug(f"DB lookup for artifact: {e}")

    # Filesystem fallback
    if not target or not target.exists():
        target = artifact_manager.get_artifact_path(request_id, clean_type, clean_file)

    if not target or not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{filename}' of type '{artifact_type}' not found."
        )

    # Determine media type
    ext = target.suffix.lower()
    media_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".geojson": "application/geo+json",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }
    media_type = media_map.get(ext, "application/octet-stream")
    return FileResponse(path=str(target), media_type=media_type)


# ============================================================
# VIDEO FOOTAGE ANALYSIS & IMPORTANT-MOMENT FLAGGING ENDPOINTS
# ============================================================

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


class PixelInspectRequest(BaseModel):
    col: Optional[int] = None
    row: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None


@router.get("/analysis/{job_id}/layers", response_model=List[LayerMetadata])
async def get_analysis_layers(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns all scientifically available visual analytics layers for the specified job.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    input_dir = job_dir / "input"

    input_files = []
    if input_dir.exists():
        input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")])

    if not input_files:
        job = await JobRepository.get_job_by_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    meta_list = []
    for f in input_files:
        try:
            m = RasterInspector.inspect(f)
            meta_list.append(m)
        except Exception as e:
            logger.debug(f"Could not inspect input file {f}: {e}")

    model_res = artifact_manager.load_result_json(job_id) or {}
    layers = VisualizationRegistry.discover_available_layers(meta_list, model_res)

    for layer in layers:
        layer.artifact_url = f"/api/analysis/{job_id}/visualizations/{layer.layer_id}"
        if layer.layer_type in [
            VisualizationType.SINGLE_BAND,
            VisualizationType.SPECTRAL_INDEX,
            VisualizationType.SAR_POLARIZATION,
            VisualizationType.PROBABILITY_HEATMAP
        ]:
            layer.legend_url = f"/api/analysis/{job_id}/visualizations/{layer.layer_id}/legend"

    return layers


@router.get("/analysis/{job_id}/visualizations/{layer_id}")
async def get_visualization_image(job_id: str, layer_id: str, db: AsyncSession = Depends(get_db)):
    """
    Renders or serves the cached visualization PNG for a specific layer.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    vis_dir = job_dir / "visualizations"
    vis_dir.mkdir(parents=True, exist_ok=True)
    out_file = vis_dir / f"{layer_id}.png"
    legend_file = vis_dir / f"{layer_id}_legend.png"

    if out_file.exists():
        return FileResponse(path=str(out_file), media_type="image/png")

    input_dir = job_dir / "input"
    input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
    if not input_files:
        raise ArtifactNotFoundError("input_imagery", message=f"No input imagery found for job '{job_id}'.", details={"job_id": job_id})

    arr, meta = RasterInspector.read_as_array(input_files[0])
    img: Optional[Image.Image] = None
    legend_img: Optional[Image.Image] = None

    if layer_id == "true_color":
        img, _ = CompositeRenderer.render_true_color(arr, meta)
    elif layer_id == "temporal_image_a":
        img, _ = CompositeRenderer.render_true_color(arr, meta)
    elif layer_id == "temporal_image_b":
        if len(input_files) >= 2:
            arr2, meta2 = RasterInspector.read_as_array(input_files[1])
            img, _ = CompositeRenderer.render_true_color(arr2, meta2)
        else:
            img, _ = CompositeRenderer.render_true_color(arr, meta)
    elif layer_id == "grayscale":
        norm, _, _, _ = _apply_percentile_stretch(arr[0] if arr.ndim == 3 else arr)
        img = Image.fromarray(norm, "L")
    elif layer_id.startswith("band_"):
        b_idx = int(layer_id.split("_")[1]) - 1
        img, legend_img, _ = CompositeRenderer.render_single_band(arr, b_idx, meta)
    elif layer_id == "false_color_nir":
        img, _ = CompositeRenderer.render_false_color(arr, meta)
    elif layer_id == "ndvi":
        res = SpectralIndexEngine.compute_ndvi(arr, meta)
        if not res.available:
            raise IndexNotAvailableError(index_name="ndvi", message=res.unavailability_reason, details={"job_id": job_id})
        img, legend_img = res.image, res.legend
    elif layer_id == "ndwi":
        res = SpectralIndexEngine.compute_ndwi(arr, meta)
        if not res.available:
            raise IndexNotAvailableError(index_name="ndwi", message=res.unavailability_reason, details={"job_id": job_id})
        img, legend_img = res.image, res.legend
    elif layer_id == "sar_vv":
        img, legend_img, _ = SARVisualizationEngine.render_polarization_layer(arr, "VV", meta)
    elif layer_id == "sar_vh":
        img, legend_img, _ = SARVisualizationEngine.render_polarization_layer(arr, "VH", meta)
    elif layer_id == "sar_dual_pol":
        img, _ = SARVisualizationEngine.render_dual_pol_composite(arr, meta)
    elif layer_id == "change_probability_heatmap":
        prob_arr = None
        prob_path = job_dir / "masks" / "change_probability.npy"
        if prob_path.exists():
            prob_arr = np.load(str(prob_path))
        else:
            mask_files = list((job_dir / "masks").glob("*.png"))
            if mask_files:
                m_img = Image.open(mask_files[0]).convert("L")
                prob_arr = (np.array(m_img) / 255.0).astype(np.float32)
            else:
                prob_arr = np.zeros((arr.shape[1], arr.shape[2]), dtype=np.float32)
        base_preview = Image.fromarray(arr[0] if arr.ndim == 3 else arr).convert("RGB")
        img, legend_img, _ = HeatmapEngine.render_probability_heatmap(prob_arr, base_preview)
    elif layer_id == "change_raw_mask":
        raw_file = job_dir / "masks" / "change_raw_mask.png"
        if raw_file.exists():
            return FileResponse(path=str(raw_file), media_type="image/png")
        mask_files = list((job_dir / "masks").glob("*.png"))
        if mask_files:
            return FileResponse(path=str(mask_files[0]), media_type="image/png")
        bin_mask = np.zeros((arr.shape[1], arr.shape[2]), dtype=np.uint8)
        img, _ = HeatmapEngine.render_binary_prediction_mask(bin_mask)
    elif layer_id in ["change_filtered_mask", "change_binary_mask"]:
        filt_file = job_dir / "masks" / "change_filtered_mask.png"
        if filt_file.exists():
            return FileResponse(path=str(filt_file), media_type="image/png")
        mask_file = job_dir / "masks" / "change_mask.png"
        if mask_file.exists():
            return FileResponse(path=str(mask_file), media_type="image/png")
        bin_mask = np.zeros((arr.shape[1], arr.shape[2]), dtype=np.uint8)
        img, _ = HeatmapEngine.render_binary_prediction_mask(bin_mask)
    elif layer_id == "change_overlay":
        overlay_file = job_dir / "overlays" / "change_overlay.png"
        if overlay_file.exists():
            return FileResponse(path=str(overlay_file), media_type="image/png")
        filt_file = job_dir / "masks" / "change_filtered_mask.png"
        if not filt_file.exists():
            filt_file = job_dir / "masks" / "change_mask.png"
        if filt_file.exists():
            m_arr = (np.array(Image.open(filt_file).convert("L")) > 0).astype(np.uint8)
            base_pil = Image.fromarray(arr[0] if arr.ndim == 3 else arr).convert("RGB")
            img = create_change_overlay(base_pil, m_arr, color=(239, 68, 68), alpha=0.45)
        else:
            raise VisualizationNotAvailableError(layer_id=layer_id, message="Change overlay not found.", details={"job_id": job_id})
    elif layer_id == "change_regions":
        import cv2
        filt_file = job_dir / "masks" / "change_filtered_mask.png"
        if not filt_file.exists():
            filt_file = job_dir / "masks" / "change_mask.png"
        if filt_file.exists():
            m_arr = (np.array(Image.open(filt_file).convert("L")) > 0).astype(np.uint8)
        else:
            m_arr = np.zeros((arr.shape[1], arr.shape[2]), dtype=np.uint8)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(m_arr, connectivity=8)
        np.random.seed(42)
        colors = np.random.randint(60, 255, size=(max(num_labels, 1), 3), dtype=np.uint8)
        colors[0] = [15, 23, 42]
        colored = colors[labels]
        img = Image.fromarray(colored, "RGB")
    elif layer_id in ["grounding_bboxes", "grounding_overlay"]:
        overlay_file = job_dir / "overlays" / "grounding_overlay.png"
        if overlay_file.exists():
            return FileResponse(path=str(overlay_file), media_type="image/png")
        overlay_files = list((job_dir / "overlays").glob("*.png"))
        if overlay_files:
            return FileResponse(path=str(overlay_files[0]), media_type="image/png")
        raise VisualizationNotAvailableError(layer_id=layer_id, message="Grounding overlay not found.", details={"job_id": job_id})
    elif layer_id == "sam2_segmentation_overlay":
        sam2_mask = job_dir / "masks" / "segmentation_mask.png"
        if sam2_mask.exists():
            return FileResponse(path=str(sam2_mask), media_type="image/png")
        overlay_files = list((job_dir / "overlays").glob("*.png"))
        if overlay_files:
            return FileResponse(path=str(overlay_files[0]), media_type="image/png")
        raise VisualizationNotAvailableError(layer_id=layer_id, message="SAM 2 overlay not found.", details={"job_id": job_id})
    else:
        raise VisualizationNotAvailableError(layer_id=layer_id, message=f"Unknown or unsupported layer ID '{layer_id}'.", details={"job_id": job_id})

    if img is not None:
        img.save(str(out_file), format="PNG", optimize=True)
    if legend_img is not None:
        legend_img.save(str(legend_file), format="PNG", optimize=True)

    return FileResponse(path=str(out_file), media_type="image/png")


@router.get("/analysis/{job_id}/visualizations/{layer_id}/legend")
async def get_visualization_legend(job_id: str, layer_id: str):
    """
    Serves the colorbar legend PNG for a layer.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    vis_dir = job_dir / "visualizations"
    legend_file = vis_dir / f"{layer_id}_legend.png"

    if not legend_file.exists():
        input_dir = job_dir / "input"
        input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
        if input_files:
            arr, meta = RasterInspector.read_as_array(input_files[0])
            if layer_id == "ndvi":
                res = SpectralIndexEngine.compute_ndvi(arr, meta)
                if res.available and res.legend:
                    res.legend.save(str(legend_file), format="PNG")
            elif layer_id == "ndwi":
                res = SpectralIndexEngine.compute_ndwi(arr, meta)
                if res.available and res.legend:
                    res.legend.save(str(legend_file), format="PNG")
            elif layer_id.startswith("band_"):
                b_idx = int(layer_id.split("_")[1]) - 1
                _, leg, _ = CompositeRenderer.render_single_band(arr, b_idx, meta)
                leg.save(str(legend_file), format="PNG")
            elif layer_id.startswith("sar_"):
                pol = "VV" if "vv" in layer_id else "VH"
                _, leg, _ = SARVisualizationEngine.render_polarization_layer(arr, pol, meta)
                leg.save(str(legend_file), format="PNG")
            elif "probability" in layer_id:
                leg = HeatmapEngine._generate_probability_legend()
                leg.save(str(legend_file), format="PNG")

    if legend_file.exists():
        return FileResponse(path=str(legend_file), media_type="image/png")

    raise VisualizationNotAvailableError(layer_id=layer_id, message=f"Legend not available for layer '{layer_id}'.", details={"job_id": job_id})


@router.post("/analysis/{job_id}/inspect-pixel")
async def inspect_pixel_at(
    job_id: str,
    body: PixelInspectRequest
):
    """
    Inspects scientific band DNs, geographic coordinates, derived index values, and model state for pixel (col, row).
    """
    col = body.col if body.col is not None else body.x
    row = body.row if body.row is not None else body.y
    if col is None or row is None:
        raise InvalidRequestError("Must provide 'col' and 'row' (or 'x' and 'y').", details={"job_id": job_id})

    job_dir = artifact_manager.get_job_dir(job_id)
    input_dir = job_dir / "input"
    input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
    if not input_files:
        raise ArtifactNotFoundError("input_imagery", message="No input imagery found for job.", details={"job_id": job_id})

    arr, meta = RasterInspector.read_as_array(input_files[0])

    derived_indices = {}
    mapping = SpectralIndexEngine.resolve_band_indices(arr, meta)
    if mapping.get("nir") is not None and mapping.get("red") is not None:
        if 0 <= row < arr.shape[1] and 0 <= col < arr.shape[2]:
            nir_val = float(arr[mapping["nir"], row, col])
            red_val = float(arr[mapping["red"], row, col])
            if (nir_val + red_val) != 0:
                derived_indices["NDVI"] = round((nir_val - red_val) / (nir_val + red_val), 4)

    prob_map = None
    prob_path = job_dir / "masks" / "change_probability.npy"
    if prob_path.exists():
        prob_map = np.load(str(prob_path))

    bin_mask = None
    mask_files = list((job_dir / "masks").glob("*.png"))
    if mask_files:
        m_img = Image.open(mask_files[0]).convert("L")
        bin_mask = (np.array(m_img) > 0).astype(np.uint8)

    try:
        inspection = InspectorEngine.inspect_pixel(
            arr=arr,
            col=col,
            row=row,
            metadata=meta,
            prob_map=prob_map,
            bin_mask=bin_mask,
            derived_indices=derived_indices
        )
        return inspection
    except ValueError as e:
        raise InvalidRequestError(str(e), details={"job_id": job_id})


@router.get("/analysis/{job_id}/histogram/{layer_id}")
async def get_layer_histogram(job_id: str, layer_id: str):
    """
    Returns 50-bin distribution histogram and percentiles for the layer.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    input_dir = job_dir / "input"
    input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
    if not input_files:
        raise ArtifactNotFoundError("input_imagery", message="No input imagery found.", details={"job_id": job_id})

    arr, meta = RasterInspector.read_as_array(input_files[0])

    data_2d = None
    units = "DN"

    if layer_id.startswith("band_"):
        b_idx = int(layer_id.split("_")[1]) - 1
        if b_idx < arr.shape[0]:
            data_2d = arr[b_idx]
    elif layer_id == "temporal_image_b" and len(input_files) >= 2:
        arr2, _ = RasterInspector.read_as_array(input_files[1])
        data_2d = arr2[0] if arr2.ndim == 3 else arr2
    elif layer_id == "ndvi":
        res = SpectralIndexEngine.compute_ndvi(arr, meta)
        if res.available and res.raw_array is not None:
            data_2d = res.raw_array
            units = "Index [-1, 1]"
    elif layer_id == "ndwi":
        res = SpectralIndexEngine.compute_ndwi(arr, meta)
        if res.available and res.raw_array is not None:
            data_2d = res.raw_array
            units = "Index [-1, 1]"
    elif layer_id == "change_probability_heatmap":
        prob_path = job_dir / "masks" / "change_probability.npy"
        if prob_path.exists():
            data_2d = np.load(str(prob_path))
            units = "Probability [0.0 - 1.0]"
    elif layer_id in ["change_raw_mask", "change_filtered_mask", "change_binary_mask"]:
        fname = "change_filtered_mask.png" if "filtered" in layer_id else ("change_raw_mask.png" if "raw" in layer_id else "change_mask.png")
        mask_file = job_dir / "masks" / fname
        if not mask_file.exists():
            mask_file = job_dir / "masks" / "change_mask.png"
        if mask_file.exists():
            data_2d = (np.array(Image.open(mask_file).convert("L")) > 0).astype(np.float32)
            units = "Discrete Binary State"

    if data_2d is None:
        data_2d = arr[0] if arr.ndim == 3 else arr

    hist = InspectorEngine.compute_histogram(data_2d, num_bins=50, units=units)
    return hist


@router.get("/analysis/{job_id}/export/{layer_id}")
async def export_layer(job_id: str, layer_id: str, format: str = "png"):
    """
    Exports visualization layer in PNG (with legend), GeoTIFF, or GeoJSON.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    vis_dir = job_dir / "visualizations"
    vis_dir.mkdir(parents=True, exist_ok=True)

    input_dir = job_dir / "input"
    input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
    if not input_files:
        raise ArtifactNotFoundError("input_imagery", message="No input imagery found for export.", details={"job_id": job_id})

    arr, meta = RasterInspector.read_as_array(input_files[0])

    if format.lower() == "png":
        layer_png = vis_dir / f"{layer_id}.png"
        legend_png = vis_dir / f"{layer_id}_legend.png"
        export_out = vis_dir / f"{job_id}_{layer_id}_export.png"

        if not layer_png.exists():
            await get_visualization_image(job_id, layer_id)

        layer_img = Image.open(layer_png)
        legend_img = Image.open(legend_png) if legend_png.exists() else None

        layer_meta = LayerMetadata(
            layer_id=layer_id,
            layer_type=VisualizationType.SINGLE_BAND,
            title=f"SatQuery Export — {layer_id.upper()}",
            provenance=LayerProvenance.DERIVED_INDEX if "nd" in layer_id else LayerProvenance.SOURCE_DATA,
            units="Scientific Units"
        )
        out_path = ExportEngine.export_png_with_legend(layer_img, layer_meta, legend_img, export_out)
        return FileResponse(
            path=str(out_path),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{job_id}_{layer_id}.png"'}
        )

    elif format.lower() in ["tif", "tiff", "geotiff"]:
        export_out = vis_dir / f"{job_id}_{layer_id}.tif"
        data_to_export = arr[0] if arr.ndim == 3 else arr
        if layer_id == "ndvi":
            res = SpectralIndexEngine.compute_ndvi(arr, meta)
            if res.available and res.raw_array is not None:
                data_to_export = res.raw_array
        out_path = ExportEngine.export_geotiff(data_to_export, meta, export_out)
        return FileResponse(
            path=str(out_path),
            media_type="image/tiff",
            headers={"Content-Disposition": f'attachment; filename="{job_id}_{layer_id}.tif"'}
        )

    elif format.lower() in ["geojson", "json"]:
        export_out = vis_dir / f"{job_id}_{layer_id}.geojson"
        mask_files = list((job_dir / "masks").glob("*.png"))
        if not mask_files:
            raise VisualizationNotAvailableError(layer_id=layer_id, message="GeoJSON export requires segmented polygon mask.", details={"job_id": job_id})
        m_img = Image.open(mask_files[0]).convert("L")
        bin_mask = (np.array(m_img) > 0).astype(np.uint8)
        out_path = ExportEngine.export_geojson_mask(bin_mask, meta, export_out)
        return FileResponse(
            path=str(out_path),
            media_type="application/geo+json",
            headers={"Content-Disposition": f'attachment; filename="{job_id}_{layer_id}.geojson"'}
        )
    else:
        raise InvalidRequestError(f"Unsupported export format '{format}'. Use 'png', 'geotiff', or 'geojson'.", details={"job_id": job_id})

