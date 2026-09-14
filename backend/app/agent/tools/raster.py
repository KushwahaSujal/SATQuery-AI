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
    resolve_state_aoi(state)


def resolve_state_aoi(state: AgentState):
    """
    Rasterises the request's GeoJSON AOI (if any) against the first raster and stores it on the state.
    Raises AOIError (HTTP 422) if the AOI is invalid, the raster is not georeferenced, or they don't overlap:
    silently analysing the whole scene when the user asked about a specific area would be wrong.
    """
    from backend.app.geo.aoi import rasterize_aoi, resolve_request_aoi

    if state.aoi is not None or not (state.parameters.get("aoi_geojson") or state.parameters.get("aoi_filename")):
        return state.aoi
    if not state.metadata:
        for p in state.image_paths:
            state.metadata.append(RasterInspector.inspect(p))
    input_dir = artifact_manager.get_job_dir(state.request_id) / "input"
    aoi = resolve_request_aoi(state.parameters, input_dir)
    state.aoi = rasterize_aoi(aoi, state.metadata[0] if state.metadata else None)
    summary = state.aoi.summary()
    summary.update({"aoi_crs": aoi.crs, "feature_count": aoi.feature_count})
    state.evidence.metadata["aoi"] = summary
    state.add_trace("Area of interest applied", status="success",
                    details=f"{summary['aoi_pixel_count']:,} px, {summary['aoi_area_sq_km']} km², "
                            f"{summary['aoi_coverage_within_raster']:.1%} of the AOI inside the raster")
    if summary["aoi_coverage_within_raster"] < 0.999:
        state.warnings.append(
            f"Only {summary['aoi_coverage_within_raster']:.1%} of the area of interest lies inside the raster; "
            "results cover that part only."
        )
    return state.aoi
