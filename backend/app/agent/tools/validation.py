"""
SatQuery AI — Input validation tools (single image, temporal pair, optical-SAR pair).
"""
from pathlib import Path
from typing import Any, Callable, Dict
import numpy as np
from PIL import Image
from backend.app.agent.state import AgentState
from backend.app.geo.raster import RasterInspector
from backend.app.geo import validation as geo_validation
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
from backend.app.agent.tools.raster import inspect_raster


@register_tool("validate_single_image")
def validate_single_image(state: AgentState) -> None:
    if not state.metadata:
        inspect_raster(state)
    geo_validation.validate_single_image(state.metadata[0])


@register_tool("validate_temporal_pair")
def validate_temporal_pair(state: AgentState) -> None:
    if len(state.metadata) < 2:
        inspect_raster(state)
    mod1 = state.modalities[0] if len(state.modalities) > 0 else "unknown"
    mod2 = state.modalities[1] if len(state.modalities) > 1 else "unknown"
    align = geo_validation.validate_temporal_pair(state.metadata[0], state.metadata[1], mod1, mod2)
    if align.warnings:
        state.warnings.extend(align.warnings)


@register_tool("validate_optical_sar_pair")
def validate_optical_sar_pair(state: AgentState) -> None:
    if len(state.metadata) < 2:
        inspect_raster(state)
    mod1 = state.modalities[0] if len(state.modalities) > 0 else "unknown"
    mod2 = state.modalities[1] if len(state.modalities) > 1 else "unknown"
    _, _, align = geo_validation.validate_optical_sar_pair(state.metadata[0], state.metadata[1], mod1, mod2)
    if align.warnings:
        state.warnings.extend(align.warnings)
