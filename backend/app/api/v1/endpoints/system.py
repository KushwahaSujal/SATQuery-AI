"""
SatQuery AI — Service health and model-registry endpoints.

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
