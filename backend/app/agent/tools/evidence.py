"""
SatQuery AI — Evidence generation tools: statistics, overlays and the audit report.
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


@register_tool("calculate_statistics")
def calculate_statistics(state: AgentState) -> None:
    if state.evidence.spatial.has_mask and state.model_results:
        for r in state.model_results:
            if r.task == "change_detection" and r.masks:
                bin_mask = r.masks[0]["binary_mask"]
                raw_mask = r.masks[0].get("raw_mask", bin_mask)
                meta = state.metadata[0] if state.metadata else None
                stats = calculate_area_statistics(bin_mask, meta)
                stats.raw_changed_pixels = r.metadata.get("raw_change_pixel_count", int(np.sum(raw_mask > 0)))
                stats.region_count = r.metadata.get("region_count", 0)
                stats.quality_status = r.metadata.get("quality_status", "PASS")
                stats.diagnostic_flags = r.metadata.get("diagnostic_flags", [])
                stats.quality_warning = r.metadata.get("quality_warning")
                state.evidence.spatial.statistics = stats
                break

    if not state.answer and state.evidence.spatial.has_mask:
        stats = state.evidence.spatial.statistics
        if stats:
            changed_pixels = stats.changed_pixels if hasattr(stats, "changed_pixels") else stats.get("changed_pixels", stats.get("changed_pixel_count", 0))
            area_m2 = stats.estimated_area_sq_m if hasattr(stats, "estimated_area_sq_m") else stats.get("estimated_area_sq_m", stats.get("total_change_area_sq_meters"))
            ratio = stats.change_ratio if hasattr(stats, "change_ratio") else stats.get("change_ratio", 0.0)
            pct = (ratio * 100.0) if ratio <= 1.0 else ratio
        else:
            changed_pixels = 0
            area_m2 = None
            pct = 0.0

        if area_m2 is not None:
            state.answer = f"Change detection completed: {changed_pixels:,} pixels changed ({area_m2:,.1f} m², {pct:.2f}% of monitored area)."
        else:
            state.answer = f"Change detection completed: {changed_pixels:,} pixels changed ({pct:.2f}% of monitored area)."


@register_tool("generate_overlay")
def generate_overlay(state: AgentState) -> None:
    if len(state.image_paths) >= 1 and state.evidence.spatial.has_mask:
        dirs = artifact_manager.init_job_workspace(state.request_id)
        arr1, _ = RasterInspector.read_as_array(state.image_paths[0])
        bin_mask = None
        is_grounding = False

        for r in state.model_results:
            if r.task == "segmentation" and r.masks:
                bin_mask = r.masks[0]["binary_mask"]
                is_grounding = True
                break
            elif r.task == "change_detection" and r.masks:
                bin_mask = r.masks[0]["binary_mask"]
                break

        # Fallback to saved mask on disk if needed
        if bin_mask is None and state.evidence.spatial.mask_path:
            m_p = Path(state.evidence.spatial.mask_path)
            if m_p.exists():
                try:
                    m_img = Image.open(m_p)
                    bin_mask = (np.array(m_img) > 0).astype(np.uint8)
                    is_grounding = "grounding" in m_p.name
                except Exception:
                    pass

        if bin_mask is not None:
            color = (0, 230, 150) if is_grounding else (255, 59, 48)  # Cyan/Emerald for grounding, Red for change
            overlay_name = "grounding_overlay.png" if is_grounding else "change_overlay.png"
            overlay_img = create_change_overlay(arr1, bin_mask, color_rgb=color, alpha=0.5)
            out_p = dirs["overlays"] / overlay_name
            save_image(overlay_img, out_p)
            state.evidence.spatial.overlay_path = str(out_p)


@register_tool("generate_report")
def generate_report(state: AgentState) -> None:
    # Build AnalyzeResponse representation for report generator
    from backend.app.schemas.responses import AnalyzeResponse
    resp = AnalyzeResponse(
        request_id=state.request_id,
        status=state.status,
        task=state.task or "unsupported",
        workflow_id=state.workflow_id or "unknown",
        workflow_reason=state.reason or "None",
        answer=state.answer,
        confidence=state.confidence,
        models_used=state.selected_models,
        parameters=state.parameters,
        evidence=state.evidence,
        execution_trace=state.execution_trace,
        warnings=state.warnings,
        errors=state.errors,
        artifacts=artifact_manager.list_artifacts(state.request_id)
    )
    dirs = artifact_manager.init_job_workspace(state.request_id)
    pdf_path = dirs["reports"] / f"{state.request_id}_audit_report.pdf"
    PDFReportGenerator.generate(resp, pdf_path)
    state.artifacts = artifact_manager.list_artifacts(state.request_id)
