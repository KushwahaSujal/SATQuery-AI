from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, timezone
import time
import numpy as np
from PIL import Image

from backend.app.workflows.grounding_reasoner import (
    parse_v4_query,
    run_v4_reasoning,
    detect_reference
)
from backend.app.ml.registry import model_registry
from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
from backend.app.ml.adapters.sam2 import SAM2Adapter
from backend.app.ml.adapters.locate_anything import LocateAnythingAdapter
from backend.app.agent.state import AgentState
from backend.app.schemas.agent import JobStatus, TaskType, ExecutionStep
from backend.app.schemas.responses import AnalyzeResponse
from backend.app.schemas.evidence import EvidencePackage, SpatialEvidence, BoundingBoxEvidence, AreaStatistics
from backend.app.evidence.fusion import EvidenceFusionEngine
from backend.app.exceptions import InvalidInputError, InferenceError
from backend.app.logging import logger


def _validate_image(image_input: Any) -> Tuple[Image.Image, np.ndarray, Tuple[int, int]]:
    """
    Validates input image exists, is readable, and has valid dimensions.
    Returns (PIL Image, uint8 RGB numpy array, (width, height)).
    """
    if image_input is None:
        raise InvalidInputError("Grounding workflow requires an input image.")

    if isinstance(image_input, Image.Image):
        pil_img = image_input.convert("RGB")
    elif isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.is_file():
            raise InvalidInputError(f"Image file does not exist at '{p}'.")
        pil_img = Image.open(p).convert("RGB")
    elif isinstance(image_input, np.ndarray):
        arr = image_input
        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)
        elif arr.ndim == 3 and arr.shape[0] in (1, 3, 4) and arr.shape[2] not in (1, 3, 4):
            arr = np.transpose(arr, (1, 2, 0))
        if arr.shape[2] == 4:
            arr = arr[:, :, :3]
        if arr.dtype != np.uint8:
            arr = arr.astype(np.uint8)
        pil_img = Image.fromarray(arr)
    else:
        raise InvalidInputError(f"Unsupported image input type: {type(image_input)}")

    w, h = pil_img.size
    if w <= 0 or h <= 0:
        raise InvalidInputError(f"Invalid image dimensions: {w}x{h}")

    arr_rgb = np.array(pil_img, dtype=np.uint8)
    return pil_img, arr_rgb, (w, h)


def run_grounding_pipeline(
    image: Any,
    query: str,
    box_threshold: float = 0.25,
    text_threshold: float = 0.25,
    iou_nms_threshold: float = 0.50,
    grounding_adapter: Optional[GroundingDINOAdapter] = None,
    grounding_model: str = "grounding_dino",
    sam2_adapter: Optional[SAM2Adapter] = None
) -> Dict[str, Any]:
    """
    Production Grounding Pipeline connecting Grounding DINO, V4 Multi-Attribute
    Reasoning, and SAM 2 promptable segmentation.

    Execution sequence:
    1. validate image;
    2. receive natural-language query;
    3. parse query;
    4. call GroundingDINOAdapter;
    5. obtain multiple candidate boxes;
    6. pass candidates to grounding_reasoner;
    7. select the target candidate;
    8. call SAM2Adapter with that REAL selected box;
    9. receive REAL segmentation mask;
    10. build visual evidence;
    11. build observable execution trace;
    12. return structured result.

    Returns:
        {
            "task": "grounding",
            "answer": ...,
            "selected_box": ...,
            "segmentation_mask": ...,
            "grounding_score": ...,
            "sam2_score": ...,
            "strategy": "V4_RELATIONAL",
            "evidence": ...,
            "trace": [...]
        }
    """
    trace: List[Dict[str, Any]] = []

    def record_step(step_name: str, status: str, tool: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        trace.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step_name,
            "status": status,
            "tool": tool,
            "details": details or {}
        })

    # Step 1: Validate image
    t0 = time.perf_counter()
    pil_img, arr_rgb, (w, h) = _validate_image(image)
    record_step("validate_image", "success", details={"dimensions": f"{w}x{h}"})

    # Step 2: Receive natural-language query
    if not query or not isinstance(query, str) or not query.strip():
        record_step("receive_query", "error", details={"reason": "empty_query"})
        raise InvalidInputError("Grounding workflow requires a non-empty natural-language query.")
    norm_query = query.strip()
    record_step("receive_query", "success", details={"query": norm_query})

    # Step 3: Parse query
    parsed = parse_v4_query(norm_query)
    target_category = parsed.get("category") or parsed.get("target_category", "object")
    clean_prompt = parsed.get("clean_prompt") or f"{target_category}."
    record_step("parse_query", "success", details={
        "target_category": target_category,
        "clean_prompt": clean_prompt,
        "modifiers": {k: v for k, v in parsed.items() if v and k not in ("category", "target_category", "raw_query", "clean_prompt")}
    })

    # Step 4: Call grounding adapter (GroundingDINO or LocateAnything)
    # When grounding_model is "auto", try GroundingDINO first and fall back
    # to LocateAnything if it returns zero candidates for this image/query.
    prompt = clean_prompt
    primary_model = grounding_model if grounding_model != "auto" else "grounding_dino"
    fallback_model = "locate_anything"
    used_model = primary_model

    def _run_detection(model_key: str, adapter: Optional[Any]) -> Tuple[str, Any, List[Dict[str, Any]]]:
        if model_key == "locate_anything":
            ad = adapter or model_registry.get_adapter("locate_anything")
            tool_name = "LocateAnythingAdapter"
        else:
            ad = adapter or model_registry.get_adapter("grounding_dino")
            tool_name = "GroundingDINOAdapter"
        record_step("call_grounding", "started", tool=tool_name, details={"model": model_key, "prompt": prompt})
        try:
            res = ad.predict(
                image_or_context=pil_img,
                prompt=prompt,
                box_threshold=box_threshold,
                text_threshold=text_threshold
            )
            record_step("call_grounding", "success", tool=tool_name, details={
                "raw_detections": len(res.get("boxes", []))
            })
            return tool_name, res, res.get("boxes", [])
        except Exception as e:
            record_step("call_grounding", "error", tool=tool_name, details={"error": str(e)})
            raise InferenceError(f"{tool_name} inference error: {e}", model_name=model_key) from e

    tool_name, det_result, raw_detections = _run_detection(primary_model, grounding_adapter)

    # Fallback to LocateAnything if primary returned no boxes
    if not raw_detections and primary_model != fallback_model:
        # Check if fallback model is available before attempting
        if model_registry.is_model_available(fallback_model):
            logger.info(f"{primary_model} returned 0 detections; falling back to {fallback_model}.")
            record_step("fallback_to_locate_anything", "started", details={"reason": "no_detections"})
            try:
                tool_name, det_result, raw_detections = _run_detection(fallback_model, None)
                used_model = fallback_model
                record_step("fallback_to_locate_anything", "success", details={
                    "raw_detections": len(raw_detections)
                })
            except InferenceError as e:
                logger.warning(f"Fallback to {fallback_model} failed: {e}. Returning empty detections.")
                record_step("fallback_to_locate_anything", "failed", details={"error": str(e)})
        else:
            logger.info(f"{primary_model} returned 0 detections but {fallback_model} is not available. Skipping fallback.")
            record_step("fallback_to_locate_anything", "skipped", details={"reason": "model_not_available"})

    # Step 5: Obtain multiple candidate boxes
    raw_candidates = det_result.get("boxes", [])
    candidates = []
    for c in raw_candidates:
        b = c.get("xyxy", [0, 0, 0, 0])
        box_w = max(0.0, float(b[2] - b[0]))
        box_h = max(0.0, float(b[3] - b[1]))
        box_area = box_w * box_h
        img_area = float(w * h)
        coverage = box_area / img_area if img_area > 0 else 0.0
        # Filter out edge-to-edge full-frame background fallback boxes (>85% coverage)
        # unless user query specifically asks for the entire image/scene/background
        if coverage > 0.85 and target_category not in ("scene", "image", "area", "background", "entire"):
            logger.info(f"Filtering out full-frame candidate box {b} (coverage: {coverage:.2%}) for discrete target '{target_category}'")
            continue
        candidates.append(c)

    record_step("obtain_candidate_boxes", "success", details={
        "candidate_count": len(candidates),
        "scores": [round(c.get("score", 0.0), 4) for c in candidates]
    })

    if not candidates:
        empty_evidence = {
            "target_category": target_category,
            "selected_box": None,
            "candidates_count": 0,
            "reasoning_strategy": "no_candidates_detected",
            "reference_evidence": {"reference_boxes": [], "reference_count": 0, "method": "none"}
        }
        record_step("select_target_candidate", "skipped", details={"reason": "no_detector_candidates"})
        return {
            "task": "grounding",
            "answer": f"No {target_category} detected in the satellite image matching '{norm_query}'.",
            "selected_box": None,
            "segmentation_mask": None,
            "grounding_score": None,
            "sam2_score": None,
            "strategy": "V4_RELATIONAL",
            "evidence": empty_evidence,
            "trace": trace
        }

    # Step 6: Pass candidates to grounding_reasoner
    record_step("run_grounding_reasoner", "started", tool="grounding_reasoner", details={
        "query": norm_query,
        "input_candidates": len(candidates)
    })
    reasoning_res = run_v4_reasoning(
        candidates=candidates,
        query=norm_query,
        img_shape=(h, w),
        image=pil_img,
        adapter=model_registry.get_adapter(used_model),
        iou_nms_threshold=iou_nms_threshold
    )
    record_step("run_grounding_reasoner", "success", tool="grounding_reasoner", details={
        "strategy": reasoning_res.get("strategy"),
        "reasoning_scores": reasoning_res.get("reasoning_scores", {})
    })

    # Step 7: Select the target candidate
    selected_cand = reasoning_res.get("selected_box")
    if not selected_cand:
        empty_evidence = {
            "target_category": target_category,
            "selected_box": None,
            "candidates_count": len(candidates),
            "reasoning_strategy": "reasoner_filtered_all",
            "reference_evidence": reasoning_res.get("reference_evidence", {})
        }
        record_step("select_target_candidate", "warning", details={"reason": "all_candidates_filtered"})
        return {
            "task": "grounding",
            "answer": f"Candidates detected but none satisfied the reasoning criteria for '{norm_query}'.",
            "selected_box": None,
            "segmentation_mask": None,
            "grounding_score": None,
            "sam2_score": None,
            "strategy": "V4_RELATIONAL",
            "evidence": empty_evidence,
            "trace": trace
        }

    selected_box = selected_cand["xyxy"]
    grounding_score = float(selected_cand.get("score", 0.0))
    record_step("select_target_candidate", "success", details={
        "selected_box": selected_box,
        "detector_score": round(grounding_score, 4),
        "reasoning_score": selected_cand.get("reasoning_score")
    })

    # Step 8: Call SAM2Adapter with that REAL selected box
    sam2 = sam2_adapter or model_registry.get_adapter("sam2")
    record_step("call_sam2", "started", tool="SAM2Adapter", details={"prompt_box": selected_box})

    try:
        sam2_res = sam2.predict(
            image_or_context=pil_img,
            box=selected_box,
            multimask_output=True
        )
        s_score = sam2_res.get("score") if isinstance(sam2_res, dict) else getattr(sam2_res, "score", 0.0)
        s_scores = sam2_res.get("scores") if isinstance(sam2_res, dict) else getattr(sam2_res, "scores", [s_score])
        record_step("call_sam2", "success", tool="SAM2Adapter", details={
            "selected_mask_score": s_score,
            "candidate_masks": len(s_scores)
        })
    except Exception as e:
        record_step("call_sam2", "error", tool="SAM2Adapter", details={"error": str(e)})
        raise InferenceError(f"SAM 2 refinement error: {e}", model_name="sam2") from e

    # Step 9: Receive REAL segmentation mask
    segmentation_mask = sam2_res.get("mask") if isinstance(sam2_res, dict) else getattr(sam2_res, "mask")
    sam2_score = float(s_score)
    mask_pixel_count = int(sam2_res.get("pixel_count") if isinstance(sam2_res, dict) else getattr(sam2_res, "pixel_count", np.sum(segmentation_mask > 0)))
    record_step("receive_segmentation_mask", "success", details={
        "mask_shape": list(segmentation_mask.shape),
        "pixel_count": mask_pixel_count,
        "sam2_score": round(sam2_score, 4)
    })

    # Step 10: Build visual evidence
    evidence = {
        "target_category": target_category,
        "selected_box": [round(float(c), 2) for c in selected_box],
        "box_2d": [
            round(selected_box[1] / h, 4),
            round(selected_box[0] / w, 4),
            round(selected_box[3] / h, 4),
            round(selected_box[2] / w, 4)
        ],
        "mask_pixel_count": mask_pixel_count,
        "mask_area_ratio": round(float(mask_pixel_count) / float(w * h), 6),
        "grounding_confidence": round(grounding_score, 4),
        "sam2_confidence": round(sam2_score, 4),
        "reasoning_scores": selected_cand.get("reasoning_scores", {}),
        "reference_evidence": reasoning_res.get("reference_evidence", {}),
        "all_candidates": [
            {
                "xyxy": [round(float(c), 2) for c in cand["xyxy"]],
                "score": round(float(cand.get("score", 0.0)), 4),
                "reasoning_score": cand.get("reasoning_score")
            }
            for cand in reasoning_res.get("candidates", [])
        ]
    }
    record_step("build_visual_evidence", "success", details={
        "mask_pixel_count": mask_pixel_count,
        "confidence": sam2_score
    })

    # Step 11: Build observable execution trace
    elapsed_total = round(time.perf_counter() - t0, 3)
    record_step("complete_pipeline", "success", details={"elapsed_seconds": elapsed_total})

    # Step 12: Return structured result
    answer = (
        f"Grounded and segmented {target_category} with high precision "
        f"at [{selected_box[0]:.1f}, {selected_box[1]:.1f}, {selected_box[2]:.1f}, {selected_box[3]:.1f}] "
        f"(detector confidence: {grounding_score:.4f}, SAM 2 score: {sam2_score:.4f}, area: {mask_pixel_count:,} pixels)."
    )

    return {
        "task": "grounding",
        "answer": answer,
        "selected_box": [round(float(c), 2) for c in selected_box],
        "segmentation_mask": segmentation_mask,
        "grounding_score": round(grounding_score, 4),
        "sam2_score": round(sam2_score, 4),
        "strategy": "V4_RELATIONAL",
        "evidence": evidence,
        "trace": trace
    }

