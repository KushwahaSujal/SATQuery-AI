"""
SatQuery AI — Model inference tools — each dispatches to an ml/ adapter.
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


def _scene_adapter():
    for key in ("scene_vlm", "general_rs_vlm"):
        if model_registry.is_model_available(key):
            return key, model_registry.get_adapter(key)
    return None, None


def _run_scene_model(state: AgentState, question: str, unavailable_msg: str) -> None:
    key, adapter = _scene_adapter()
    if adapter is None:
        state.warnings.append("No scene model (Qwen3-VL or BLIP) is configured on this deployment.")
        state.answer = unavailable_msg
        state.confidence = None
        return
    arr, _ = RasterInspector.read_as_array(state.image_paths[0])
    res = adapter.predict({"image_pil": to_pil_rgb(arr), "query": question})
    state.model_results.append(res)
    state.answer = res.answer
    state.confidence = res.confidence
    if key not in state.selected_models:
        state.selected_models.append(key)
    if res.warnings:
        state.warnings.extend(res.warnings)


@register_tool("run_vqa")
def run_vqa(state: AgentState) -> None:
    _run_scene_model(state, state.query, (
        "Scene question answering is currently NOT_CONFIGURED on this deployment. "
        "Grounding DINO + SAM 2 remain active for detection and segmentation; ChangeFormer and CDVQA for change."
    ))


@register_tool("run_caption")
def run_caption(state: AgentState) -> None:
    _run_scene_model(state, "Describe this image: land cover, main objects and how they are laid out.", (
        "Scene captioning is currently NOT_CONFIGURED on this deployment. "
        "Grounding DINO + SAM 2 remain active for detection and segmentation; ChangeFormer and CDVQA for change."
    ))


@register_tool("run_grounding")
def run_grounding(state: AgentState) -> None:
    """
    Executes production grounding workflow:
    Grounding DINO -> V4 Reasoning -> SAM2 -> Evidence Engine
    """
    from backend.app.workflows.grounding import run_grounding_pipeline
    from backend.app.schemas.models import ModelResult

    meta = state.metadata[0] if state.metadata else None
    # Use "auto" mode: GroundingDINO first, LocateAnything fallback when empty.
    grounding_model = "auto"
    if "locate_anything" in state.selected_models:
        grounding_model = "locate_anything"
    pipeline_res = run_grounding_pipeline(
        image=state.image_paths[0],
        query=state.query,
        grounding_model=grounding_model,
        aoi_mask=state.aoi.mask if state.aoi is not None else None
    )

    state.answer = pipeline_res.get("answer")
    grounding_confidence = pipeline_res.get("sam2_score") or pipeline_res.get("grounding_score")
    state.confidence = grounding_confidence
    deliberation = pipeline_res.get("agent_deliberation") or {}
    if deliberation.get("decision") == "accepted_disputed":
        state.warnings.append("The verification agent disputes the detected category; treat the result as doubtful.")
    elif deliberation.get("decision") == "accepted_unconfirmed":
        state.warnings.append("Detection not confirmed by the verification agent; treat the result as unconfirmed.")
    elif deliberation.get("decision") == "not_found":
        state.warnings.append("Verification agent contradicted every detector candidate; nothing was segmented.")
    ev_dict = pipeline_res.get("evidence", {})

    # Append to model_results so controller doesn't overwrite confidence
    used_model = pipeline_res.get("detector", "grounding_dino")
    state.model_results.append(ModelResult(
        model_name=used_model,
        task="grounding",
        answer=state.answer,
        confidence=grounding_confidence,
        metadata={"sam2_score": pipeline_res.get("sam2_score"), "grounding_score": pipeline_res.get("grounding_score")}
    ))

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
        instance_boxes=pipeline_res.get("instance_boxes"),
        instance_scores=[i.get("detector_confidence") for i in ev_dict.get("instances", [])],
        extra_metadata={
            "strategy": pipeline_res.get("strategy"),
            "instance_count": ev_dict.get("instance_count"),
            "reasoning_scores": ev_dict.get("reasoning_scores"),
            "reference_evidence": ev_dict.get("reference_evidence"),
            "candidate_boxes": [c["xyxy"] for c in ev_dict.get("all_candidates", [])],
            "candidate_scores": [c["score"] for c in ev_dict.get("all_candidates", [])],
            "query": state.query,
            "agent_deliberation": pipeline_res.get("agent_deliberation"),
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


@register_tool("run_segmentation")
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


@register_tool("run_change_detection")
def run_change_detection(state: AgentState) -> None:
    adapter = model_registry.get_adapter("changeformer")
    arr1, meta1 = RasterInspector.read_as_array(state.image_paths[0])
    arr2, meta2 = RasterInspector.read_as_array(state.image_paths[1])
    from backend.app.geo.optical_preprocessing import joint_rgb8_pair
    rgb1, rgb2, conversion_note = joint_rgb8_pair(arr1, arr2)
    if conversion_note:
        state.warnings.append(conversion_note)
    res = adapter.predict({"arr1": rgb1, "arr2": rgb2})
    # Inference mode changes the result materially (LEVIR scene 100: native 118,997 changed px, 512-px windows
    # 114,001, 256-px windows 111,556), so it is reported, and an out-of-memory fallback is a warning (Q-014).
    mode = res.metadata.get("inference_mode")
    recovery = res.metadata.get("oom_recovery")
    state.evidence.metadata["change_inference"] = {"inference_mode": mode, "oom_recovery": recovery,
                                                   "max_native_side": res.metadata.get("max_native_side")}
    if recovery and str(recovery.get("resolved_by", "")).startswith("windowed"):
        state.warnings.append(
            f"GPU memory was insufficient for full-resolution change detection even after releasing other models; "
            f"ran in {recovery['resolved_by'].split('_')[1]}-pixel windows, which lowers accuracy (IoU 0.8086 native vs "
            f"0.7997 at 512 px and 0.7872 at 256 px on a LEVIR-CD 1024 scene)."
        )
    elif recovery:
        state.warnings.append(f"Released GPU memory held by {recovery.get('released_models')} to run change detection at full resolution.")
    if state.aoi is not None and res.masks:
        # Restrict the change result to the requested area of interest. Full-scene masks are kept
        # alongside so nothing computed is discarded; counts, GeoJSON and statistics use the clipped ones.
        aoi_mask = state.aoi.mask
        m0 = res.masks[0]
        for key in ("binary_mask", "raw_mask", "filtered_mask"):
            if m0.get(key) is not None and m0[key].shape == aoi_mask.shape:
                m0[f"{key}_full_scene"] = m0[key]
                m0[key] = (m0[key] > 0).astype(np.uint8) & aoi_mask.astype(np.uint8)
        in_aoi = int(m0["binary_mask"].sum())
        res.metadata["aoi_applied"] = True
        res.metadata["change_pixel_count_full_scene"] = res.metadata.get("change_pixel_count")
        res.metadata["change_pixel_count"] = in_aoi
        res.metadata["aoi_pixel_count"] = state.aoi.pixel_count
        res.metadata["change_ratio_pct"] = 100.0 * in_aoi / max(1, state.aoi.pixel_count)
        res.answer = (
            f"Bi-temporal change detection within the area of interest: {in_aoi:,} of {state.aoi.pixel_count:,} "
            f"AOI pixels changed ({res.metadata['change_ratio_pct']:.2f}% of the AOI; "
            f"{res.metadata['change_pixel_count_full_scene']:,} px across the full scene)."
        )
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
        save_mask_as_geotiff(filtered_mask, mask_path, metadata=meta1)
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
            if state.aoi is not None:
                from backend.app.geo.aoi import draw_aoi_outline
                overlay_img = draw_aoi_outline(overlay_img, state.aoi.mask)
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


@register_tool("run_change_vqa")
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

    # Second agent on the same question: ChangeFormer's building-change evidence (Q-012).
    changeformer_res = next((m for m in state.model_results if m.task == "change_detection"), None)
    if changeformer_res is None:
        state.warnings.append("CDVQA answer not cross-checked: no ChangeFormer result in this run.")
        return
    from backend.app.evidence.adjudicator import EvidenceAdjudicator
    inputs_identical = arr1.shape == arr2.shape and bool(np.array_equal(arr1, arr2))
    # Counterfactual probe: the same question with no change at all (first image twice).
    identity_res = adapter.predict({"image1": img1, "image2": img1, "query": state.query})
    verdict = EvidenceAdjudicator.adjudicate_change_vqa(
        state.query, changeformer_res, res, job_id=state.request_id,
        cdvqa_identity_result=identity_res, inputs_identical=inputs_identical)
    state.answer = verdict.adjudicated_answer
    state.confidence = verdict.confidence
    state.confidence_final = True
    state.evidence.metadata["change_adjudication"] = verdict.model_dump()
    state.add_trace(
        step_name=f"Change adjudication: {verdict.adjudication_status}",
        status="warning" if verdict.conflict_details and verdict.conflict_details.has_conflict else "success",
        tool="EvidenceAdjudicator",
        details=(f"rule={verdict.applied_rule}; question_type={verdict.provenance.get('question_type')}; "
                 f"CDVQA '{res.metadata.get('raw_answer')}' conf={res.confidence}; "
                 f"ChangeFormer building change ratio={verdict.contributing_evidence[0]['building_change_ratio']} "
                 f"conf={changeformer_res.confidence}"),
    )
    if verdict.adjudication_status in ("CONFLICT", "CDVQA_ANSWER_TYPE_MISMATCH", "CDVQA_UNINFORMATIVE", "INPUTS_IDENTICAL") \
            and verdict.conflict_details and verdict.conflict_details.has_conflict:
        state.warnings.append(f"Change agents disagree ({verdict.adjudication_status}): {verdict.conflict_details.description}")
        if state.quality_status == "PASS":
            state.quality_status = "REVIEW_REQUIRED"


@register_tool("run_optical_sar")
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
    if res.warnings:
        for w in res.warnings:
            if w not in state.warnings:
                state.warnings.append(w)
    if "dofa" not in state.selected_models:
        state.selected_models.append("dofa")
    if "satquery_optical_sar_fusion" not in state.selected_models:
        state.selected_models.append("satquery_optical_sar_fusion")
