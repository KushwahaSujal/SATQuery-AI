"""
SatQuery AI — Raster inspection tools.
"""
from pathlib import Path
from typing import Any, Callable, Dict
import numpy as np
from PIL import Image
from backend.app.agent.state import AgentState
from backend.app.geo.raster import RasterInspector
from backend.app.geo.validation import (
    validate_single_image,
    validate_temporal_pair,
    validate_optical_sar_pair,
)
from backend.app.ml.registry import model_registry
from backend.app.evidence.boxes import normalize_box
from backend.app.evidence.masks import save_mask_as_geotiff
from backend.app.evidence.polygons import mask_to_geojson, save_geojson
from backend.app.evidence.statistics import calculate_area_statistics
from backend.app.schemas.evidence import AreaStatistics
from backend.app.evidence.confidence import ConfidenceEvaluator
from backend.app.evidence.consistency import ConsistencyChecker
from backend.app.evidence.fusion import EvidenceFusionEngine
from backend.app.evidence.report import PDFReportGenerator
from backend.app.artifacts.manager import artifact_manager
from backend.app.geo.rendering import create_change_overlay, save_image
from backend.app.geo.optical_preprocessing import to_pil_rgb
from backend.app.logging import logger
from backend.app.agent.tools.base import register_tool


@register_tool("inspect_raster")
def inspect_raster(state: AgentState) -> None:
    state.metadata.clear()
    for p in state.image_paths:
        meta = RasterInspector.inspect(p)
        state.metadata.append(meta)
