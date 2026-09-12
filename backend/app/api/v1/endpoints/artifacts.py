"""
SatQuery AI — Static artifact file serving for a job workspace.

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
