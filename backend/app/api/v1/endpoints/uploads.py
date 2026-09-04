"""
SatQuery AI — Raster upload, validation and metadata inspection.

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

router = APIRouter(tags=["SatQuery AI"])


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
