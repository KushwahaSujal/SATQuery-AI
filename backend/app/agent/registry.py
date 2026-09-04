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


class ToolRegistry:
    """
    Registry of strictly callable geospatial, model, and evidence generation tools.
    """
    @staticmethod
    def inspect_raster(state: AgentState) -> None:
        state.metadata.clear()
        for p in state.image_paths:
            meta = RasterInspector.inspect(p)
            state.metadata.append(meta)

    @staticmethod
    def validate_single_image_tool(state: AgentState) -> None:
        if not state.metadata:
            ToolRegistry.inspect_raster(state)
        validate_single_image(state.metadata[0])

    @staticmethod
    def validate_temporal_pair_tool(state: AgentState) -> None:
        if len(state.metadata) < 2:
            ToolRegistry.inspect_raster(state)
        mod1 = state.modalities[0] if len(state.modalities) > 0 else "unknown"
        mod2 = state.modalities[1] if len(state.modalities) > 1 else "unknown"
        align = validate_temporal_pair(state.metadata[0], state.metadata[1], mod1, mod2)
        if align.warnings:
            state.warnings.extend(align.warnings)

    @staticmethod
    def validate_optical_sar_pair_tool(state: AgentState) -> None:
        if len(state.metadata) < 2:
            ToolRegistry.inspect_raster(state)
        mod1 = state.modalities[0] if len(state.modalities) > 0 else "unknown"
        mod2 = state.modalities[1] if len(state.modalities) > 1 else "unknown"
        _, _, align = validate_optical_sar_pair(state.metadata[0], state.metadata[1], mod1, mod2)
        if align.warnings:
            state.warnings.extend(align.warnings)

    @staticmethod
    def run_vqa(state: AgentState) -> None:
        if not model_registry.is_model_available("general_rs_vlm"):
            msg = (
                "General Remote-Sensing VLM capability is currently NOT_CONFIGURED on this deployment. "
                "For single-image analysis, Grounding DINO + V4 Reasoner + SAM 2 are active for open-vocabulary spatial detection and segmentation. "
                "For bi-temporal analysis, ChangeFormer and CDVQA are active."
            )
            state.warnings.append("GENERAL_RS_VLM is not configured on this deployment.")
            state.answer = msg
            state.confidence = None
            return

        adapter = model_registry.get_adapter("general_rs_vlm")
        arr, _ = RasterInspector.read_as_array(state.image_paths[0])
        img_pil = to_pil_rgb(arr)
        res = adapter.predict({"image_pil": img_pil, "query": state.query})
        state.model_results.append(res)
        state.answer = res.answer
        state.confidence = res.confidence
        if "general_rs_vlm" not in state.selected_models:
            state.selected_models.append("general_rs_vlm")
        if res.warnings:
            state.warnings.extend(res.warnings)

    @staticmethod
    def run_caption(state: AgentState) -> None:
        if not model_registry.is_model_available("general_rs_vlm"):
            msg = (
                "General Remote-Sensing VLM scene captioning is currently NOT_CONFIGURED on this deployment. "
                "Active single-image models: Grounding DINO (open-vocabulary detection) and SAM 2 (high-precision segmentation). "
                "Active bi-temporal models: ChangeFormer and CDVQA."
            )
            state.warnings.append("GENERAL_RS_VLM is not configured on this deployment.")
            state.answer = msg
            state.confidence = None
            return

        adapter = model_registry.get_adapter("general_rs_vlm")
        arr, _ = RasterInspector.read_as_array(state.image_paths[0])
        img_pil = to_pil_rgb(arr)
        res = adapter.predict({"image_pil": img_pil, "query": "Provide a concise land-cover and scene caption."})
        state.model_results.append(res)
        state.answer = res.answer
        state.confidence = res.confidence
        if "general_rs_vlm" not in state.selected_models:
            state.selected_models.append("general_rs_vlm")

    @staticmethod
    def run_grounding(state: AgentState) -> None:
        """
        Executes production grounding workflow:
        Grounding DINO -> V4 Reasoning -> SAM2 -> Evidence Engine
        """
        from backend.app.workflows.grounding import run_grounding_pipeline

        meta = state.metadata[0] if state.metadata else None
        pipeline_res = run_grounding_pipeline(
            image=state.image_paths[0],
            query=state.query
        )

        state.answer = pipeline_res.get("answer")
        state.confidence = pipeline_res.get("sam2_score") or pipeline_res.get("grounding_score")
        ev_dict = pipeline_res.get("evidence", {})

        # Connect grounding workflow output to Evidence Engine
        state.evidence = EvidenceFusionEngine.build_grounding_evidence(
            selected_box=pipeline_res.get("selected_box"),
            segmentation_mask=pipeline_res.get("segmentation_mask"),
            metadata=meta,
            request_id=state.request_id,
            target_category=ev_dict.get("target_category", "detected_object"),
            grounding_score=pipeline_res.get("grounding_score"),
            sam2_score=pipeline_res.get("sam2_score"),
            summary=state.answer,
            extra_metadata={
                "strategy": pipeline_res.get("strategy"),
                "reasoning_scores": ev_dict.get("reasoning_scores"),
                "reference_evidence": ev_dict.get("reference_evidence"),
                "candidate_boxes": [c["xyxy"] for c in ev_dict.get("all_candidates", [])],
                "candidate_scores": [c["score"] for c in ev_dict.get("all_candidates", [])],
                "query": state.query,
            }
        )

        # Log observable trace steps into state
        for step in pipeline_res.get("trace", []):
            state.add_trace(
                step_name=step["step"],
                status=step["status"],
                tool=step.get("tool"),
                details=str(step.get("details"))
            )

    @staticmethod
    def run_segmentation(state: AgentState) -> None:
        """
        Refines segmentation if needed. If SAM2 was already executed as part of the
        grounding workflow, ensures mask and polygon evidence are validated.
        """
        if state.evidence.spatial.has_mask and state.evidence.spatial.mask_path:
            logger.info("SAM 2 mask already generated during unified grounding workflow.")
            return

        if not model_registry.is_model_available("sam2"):
            state.warnings.append("SAM 2 checkpoint is not configured. Returning grounding boxes without refined masks.")
            return

        if not state.evidence.spatial.boxes:
            logger.info("No bounding boxes detected for SAM 2 segmentation; skipping refinement.")
            return

        adapter = model_registry.get_adapter("sam2")
        arr, meta = RasterInspector.read_as_array(state.image_paths[0])
        img_pil = to_pil_rgb(arr)
        res = adapter.predict({"image_pil": img_pil, "boxes": [b.model_dump() for b in state.evidence.spatial.boxes]})
        state.model_results.append(res)

    @staticmethod
    def run_change_detection(state: AgentState) -> None:
        adapter = model_registry.get_adapter("changeformer")
        arr1, meta1 = RasterInspector.read_as_array(state.image_paths[0])
        arr2, meta2 = RasterInspector.read_as_array(state.image_paths[1])
        res = adapter.predict({"arr1": arr1, "arr2": arr2})
        state.model_results.append(res)

        if res.masks:
            mask_dict = res.masks[0]
            change_prob_map = mask_dict.get("change_prob_map")
            bin_mask = mask_dict.get("binary_mask")
            raw_mask = mask_dict.get("raw_mask", bin_mask)
            filtered_mask = mask_dict.get("filtered_mask", bin_mask)

            dirs = artifact_manager.init_job_workspace(state.request_id)

            # 1. Persist continuous probability map for heatmaps & radiometric inspection
            if change_prob_map is not None:
                np.save(str(dirs["masks"] / "change_probability.npy"), change_prob_map.astype(np.float32))

            # 2. Persist binary masks as GeoTIFF and PNG
            mask_path = dirs["masks"] / "change_mask.tif"
            save_mask_as_geotiff(filtered_mask, mask_path)
            Image.fromarray((filtered_mask * 255).astype(np.uint8)).save(str(dirs["masks"] / "change_mask.png"))
            Image.fromarray((filtered_mask * 255).astype(np.uint8)).save(str(dirs["masks"] / "change_filtered_mask.png"))
            if raw_mask is not None:
                Image.fromarray((raw_mask * 255).astype(np.uint8)).save(str(dirs["masks"] / "change_raw_mask.png"))

            state.evidence.spatial.has_mask = True
            state.evidence.spatial.mask_path = str(mask_path)

            # 3. Create and persist authentic visual change overlay
            try:
                base_pil = to_pil_rgb(arr1)
                overlay_img = create_change_overlay(base_pil, filtered_mask, color=(239, 68, 68), alpha=0.45)
                overlay_path = dirs["overlays"] / "change_overlay.png"
                save_image(overlay_img, overlay_path)
                state.evidence.spatial.overlay_path = str(overlay_path)
            except Exception as e:
                logger.warning(f"Could not generate change overlay: {e}")

            # 4. Generate GeoJSON polygons from filtered coherent regions
            geojson = mask_to_geojson(filtered_mask, meta1)
            geojson_path = dirs["vectors"] / "change.geojson"
            save_geojson(geojson, geojson_path)
            state.evidence.spatial.geojson_path = str(geojson_path)
            state.evidence.spatial.geojson_data = geojson

            # 5. Populate structured spatial statistics & diagnostic quality
            stats = calculate_area_statistics(filtered_mask, meta1)
            raw_cnt = res.metadata.get("raw_change_pixel_count", int(np.sum(raw_mask > 0)))
            reg_cnt = res.metadata.get("region_count", 0)
            q_status = res.metadata.get("quality_status", "PASS")
            diag_flags = res.metadata.get("diagnostic_flags", [])
            q_warn = res.metadata.get("quality_warning")

            if isinstance(stats, AreaStatistics):
                stats.raw_changed_pixels = raw_cnt
                stats.region_count = reg_cnt
                stats.quality_status = q_status
                stats.diagnostic_flags = diag_flags
                stats.quality_warning = q_warn
            elif isinstance(stats, dict):
                stats["raw_changed_pixels"] = raw_cnt
                stats["region_count"] = reg_cnt
                stats["quality_status"] = q_status
                stats["diagnostic_flags"] = diag_flags
                stats["quality_warning"] = q_warn
            state.evidence.spatial.statistics = stats

            if res.metadata.get("quality_warning"):
                state.warnings.append(res.metadata["quality_warning"])

    @staticmethod
    def run_change_vqa(state: AgentState) -> None:
        if not model_registry.is_model_available("cdvqa"):
            logger.warning("CDVQA model checkpoint unavailable. Answering change question from ChangeFormer spatial detection evidence.")
            state.warnings.append("CDVQA model checkpoint is not configured. Answering change question using ChangeFormer spatial change evidence.")
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

            if state.evidence.spatial.has_mask and changed_pixels > 0:
                if area_m2 is not None:
                    state.answer = (
                        f"Bi-temporal change analysis completed using ChangeFormer: "
                        f"Detected {changed_pixels:,} changed pixels covering approximately {area_m2:,.1f} m² "
                        f"({pct:.2f}% of monitored area). Spatial change mask and GeoJSON vectors generated."
                    )
                else:
                    state.answer = (
                        f"Bi-temporal change analysis completed using ChangeFormer: "
                        f"Detected {changed_pixels:,} changed pixels ({pct:.2f}% of monitored area). "
                        f"Spatial change mask and GeoJSON vectors generated."
                    )
            else:
                state.answer = "Bi-temporal change analysis completed using ChangeFormer: No significant structural or land-use changes detected between the two observation dates."
            return

        adapter = model_registry.get_adapter("cdvqa")
        arr1, _ = RasterInspector.read_as_array(state.image_paths[0])
        arr2, _ = RasterInspector.read_as_array(state.image_paths[1])
        img1 = to_pil_rgb(arr1)
        img2 = to_pil_rgb(arr2)
        res = adapter.predict({"image1": img1, "image2": img2, "query": state.query})
        state.model_results.append(res)
        state.answer = res.answer
        state.confidence = res.confidence
        if "cdvqa" not in state.selected_models:
            state.selected_models.append("cdvqa")

    @staticmethod
    def run_optical_sar(state: AgentState) -> None:
        dofa_adapter = model_registry.get_adapter("dofa")
        fusion_adapter = model_registry.get_adapter("satquery_optical_sar_fusion")
        
        arr1, meta1 = RasterInspector.read_as_array(state.image_paths[0])
        arr2, meta2 = RasterInspector.read_as_array(state.image_paths[1])
        
        mod1 = state.modalities[0]
        opt_arr = arr1 if mod1 in ["optical", "multispectral"] else arr2
        sar_arr = arr2 if mod1 in ["optical", "multispectral"] else arr1

        # Extract features and predict with fusion model
        feats = dofa_adapter.extract_features(opt_arr, sar_arr)
        res = fusion_adapter.predict(feats)
        state.model_results.append(res)
        state.answer = res.answer
        state.confidence = res.confidence
        if "dofa" not in state.selected_models:
            state.selected_models.append("dofa")
        if "satquery_optical_sar_fusion" not in state.selected_models:
            state.selected_models.append("satquery_optical_sar_fusion")

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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


TOOL_REGISTRY: Dict[str, Callable[[AgentState], None]] = {
    "inspect_raster": ToolRegistry.inspect_raster,
    "validate_single_image": ToolRegistry.validate_single_image_tool,
    "validate_temporal_pair": ToolRegistry.validate_temporal_pair_tool,
    "validate_optical_sar_pair": ToolRegistry.validate_optical_sar_pair_tool,
    "run_vqa": ToolRegistry.run_vqa,
    "run_caption": ToolRegistry.run_caption,
    "run_grounding": ToolRegistry.run_grounding,
    "run_segmentation": ToolRegistry.run_segmentation,
    "run_change_detection": ToolRegistry.run_change_detection,
    "run_change_vqa": ToolRegistry.run_change_vqa,
    "run_optical_sar": ToolRegistry.run_optical_sar,
    "calculate_statistics": ToolRegistry.calculate_statistics,
    "generate_overlay": ToolRegistry.generate_overlay,
    "generate_report": ToolRegistry.generate_report,
}
