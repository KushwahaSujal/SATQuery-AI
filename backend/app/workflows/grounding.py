from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, timezone
import re
import time
import numpy as np
from PIL import Image

from backend.app.workflows.grounding_reasoner import (
    parse_v4_query,
    relation_score,
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
from backend.app.config import settings
from backend.app.evidence.verifier import CONTRADICTED, UNVERIFIED, VERIFIED, DetectionVerifier
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


def _box_iou(a: List[float], b: List[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


MAX_INSTANCES = 50
_ALL_INSTANCES = re.compile(r"\b(all|every|each|mask|masks|masking|count|how\s+many)\b")
_SINGLE_TARGET = re.compile(r"\b(the\s+(largest|biggest|smallest|tallest|longest|nearest|closest|only)|a\s+single|one)\b")


def _wants_all_instances(query: str, strategy: str, parsed: Optional[Dict[str, Any]] = None) -> bool:
    """Category requests ("mask trees", "houses near cars") segment every instance; size, position and
    ordinal requests ("the largest building", "the second ship") keep the single reasoner choice."""
    if strategy.startswith("ordinal_"):
        return False
    if parsed is not None:
        if parsed.get("size") or parsed.get("position") or parsed.get("ordinal"):
            return False
    elif strategy == "multi_attribute_ranking":
        return False
    q = query.lower()
    if _SINGLE_TARGET.search(q):
        return False
    if _ALL_INSTANCES.search(q):
        return True
    # Plural nouns: "find trees", "segment the buildings".
    return any(t.endswith("s") and not t.endswith("ss") and len(t) > 3 for t in re.findall(r"[a-z]+", q)[1:])


def _satisfies_relation(box: List[float], reference_boxes: List[List[float]], relation: str,
                        img_w: int, img_h: int) -> bool:
    """Instance filter for plural relational queries. "near" uses the edge-to-edge gap, not the centre
    distance that relation_score ranks by, so a large house touching a car still counts as near it."""
    if not relation or not reference_boxes:
        return True
    if any(_box_iou(box, r) > 0.5 for r in reference_boxes):
        return False  # the candidate is the reference object itself
    if relation == "near":
        limit = 0.08 * (img_w ** 2 + img_h ** 2) ** 0.5
        for r in reference_boxes:
            gx = max(0.0, max(r[0] - box[2], box[0] - r[2]))
            gy = max(0.0, max(r[1] - box[3], box[1] - r[3]))
            if (gx * gx + gy * gy) ** 0.5 <= limit:
                return True
        return False
    return relation_score(box, reference_boxes, relation) >= 1.0


def run_grounding_pipeline(
    image: Any,
    query: str,
    box_threshold: float = 0.25,
    text_threshold: float = 0.25,
    iou_nms_threshold: float = 0.50,
    grounding_adapter: Optional[GroundingDINOAdapter] = None,
    grounding_model: str = "grounding_dino",
    sam2_adapter: Optional[SAM2Adapter] = None,
    verifier: Optional[DetectionVerifier] = None,
    aoi_mask: Optional[np.ndarray] = None
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

    # Steps 4-6. The primary detector is Grounding DINO (or LocateAnything when requested); when it
    # returns nothing and grounding_model is "auto", LocateAnything-3B is tried before giving up.
    prompt = clean_prompt
    primary_model = grounding_model if grounding_model != "auto" else "grounding_dino"
    fallback_model = "locate_anything"
    used_model = primary_model
    detector_adapters: Dict[str, Any] = {}

    def _run_detection(model_key: str, adapter: Optional[Any], threshold: float, attempt: str) -> Dict[str, Any]:
        tool_name = "LocateAnythingAdapter" if model_key == "locate_anything" else "GroundingDINOAdapter"
        step = f"call_{model_key}"
        ad = adapter or detector_adapters.get(model_key) or model_registry.get_adapter(model_key)
        detector_adapters[model_key] = ad
        record_step(step, "started", tool=tool_name, details={
            "model": model_key, "prompt": prompt, "box_threshold": threshold, "attempt": attempt
        })
        try:
            res = ad.predict(
                image_or_context=pil_img,
                prompt=prompt,
                box_threshold=threshold,
                text_threshold=text_threshold
            )
        except Exception as e:
            record_step(step, "error", tool=tool_name, details={"error": str(e)})
            raise InferenceError(f"{tool_name} inference error: {e}", model_name=model_key) from e
        record_step(step, "success", tool=tool_name, details={
            "raw_detections": len(res.get("boxes", [])), "attempt": attempt
        })
        return res

    def detect_and_rank(threshold: float, attempt: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Steps 4-6: detector proposals (with LocateAnything fallback) -> full-frame/AOI filter -> V4 reasoner ranking."""
        nonlocal used_model
        det_result = _run_detection(primary_model, grounding_adapter, threshold, attempt)
        used_model = primary_model
        if not det_result.get("boxes") and grounding_model == "auto" and primary_model != fallback_model:
            if model_registry.is_model_available(fallback_model):
                logger.info(f"{primary_model} returned 0 detections; falling back to {fallback_model}.")
                record_step("fallback_to_locate_anything", "started", details={"reason": "no_detections", "attempt": attempt})
                try:
                    det_result = _run_detection(fallback_model, None, threshold, attempt)
                    used_model = fallback_model
                    record_step("fallback_to_locate_anything", "success", details={
                        "raw_detections": len(det_result.get("boxes", []))
                    })
                except InferenceError as e:
                    logger.warning(f"Fallback to {fallback_model} failed: {e}. Returning empty detections.")
                    record_step("fallback_to_locate_anything", "failed", details={"error": str(e)})
            else:
                record_step("fallback_to_locate_anything", "skipped", details={"reason": "model_not_available"})

        found = []
        outside_aoi: List[List[float]] = []
        for c in det_result.get("boxes", []):
            b = c.get("xyxy", [0, 0, 0, 0])
            coverage = (max(0.0, float(b[2] - b[0])) * max(0.0, float(b[3] - b[1]))) / float(w * h)
            # Filter out edge-to-edge full-frame background fallback boxes (>85% coverage)
            # unless user query specifically asks for the entire image/scene/background
            if coverage > 0.85 and target_category not in ("scene", "image", "area", "background", "entire"):
                logger.info(f"Filtering out full-frame candidate box {b} (coverage: {coverage:.2%}) for discrete target '{target_category}'")
                continue
            if aoi_mask is not None and aoi_mask.shape == (h, w):
                from backend.app.geo.aoi import aoi_bbox_ratio
                centre_inside, _ = aoi_bbox_ratio(b, aoi_mask)
                if not centre_inside:
                    outside_aoi.append([round(float(v), 1) for v in b])
                    continue
            found.append(c)
        if outside_aoi:
            record_step("filter_area_of_interest", "success", details={
                "dropped_outside_aoi": len(outside_aoi), "attempt": attempt
            })
        record_step("obtain_candidate_boxes", "success", details={
            "candidate_count": len(found),
            "scores": [round(c.get("score", 0.0), 4) for c in found],
            "attempt": attempt
        })
        if not found:
            return [], {"selected_box": None, "strategy": "no_candidates_detected", "candidates": [],
                        "reference_evidence": {"reference_boxes": [], "reference_count": 0, "method": "none"}}

        record_step("run_grounding_reasoner", "started", tool="grounding_reasoner", details={
            "query": norm_query, "input_candidates": len(found), "attempt": attempt
        })
        res = run_v4_reasoning(
            candidates=found,
            query=norm_query,
            img_shape=(h, w),
            image=pil_img,
            adapter=detector_adapters[used_model],
            iou_nms_threshold=iou_nms_threshold
        )
        record_step("run_grounding_reasoner", "success", tool="grounding_reasoner", details={
            "strategy": res.get("strategy"), "detector": used_model,
            "reasoning_scores": res.get("reasoning_scores", {}),
            "attempt": attempt
        })
        return found, res

    candidates, reasoning_res = detect_and_rank(box_threshold, "initial")

    # Step 7: Two-agent deliberation — the reasoner ranks, the verification agent confirms,
    # contradicts (-> backtrack) or cannot confirm each candidate; all rejected -> re-evaluate.
    if verifier is None and settings.agent_verification.enabled:
        verifier = DetectionVerifier()
    use_verifier = verifier is not None and verifier.is_available()
    deliberation: Dict[str, Any] = {
        "agents": {
            "detector": "Grounding DINO (proposes boxes, detector confidence)",
            "reasoner": "V4 reasoner (ranks by query attributes)",
            "verifier": "RemoteCLIP contrastive verification" if use_verifier else None,
        },
        "verification_enabled": use_verifier,
        "attempts": [],
        "backtracks": 0,
        "re_evaluated": False,
        "decision": None,
    }

    def deliberate(res: Dict[str, Any], attempt: str, exclude: List[List[float]],
                   allow_unconfirmed: bool) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        ranked = list(res.get("candidates", []))
        first = res.get("selected_box")
        order = ([first] if first else []) + [c for c in ranked if first is None or c["xyxy"] != first["xyxy"]]
        strategy = str(res.get("strategy", ""))
        attribute_query = strategy == "multi_attribute_ranking" or strategy.startswith("ordinal_")
        if attribute_query:
            # Attribute queries ("the largest building", "white car bottom left", "second from left"):
            # the reasoner's choice encodes the attributes, which the verifier cannot judge, so another
            # box would answer a different question. The verifier labels the answer instead of replacing
            # it. Measured on 206 VRSBench attribute queries: backtracking cut R@0.5 from 48.1% to 41.3%;
            # labelling keeps 48.1% (agent_deliberation_rules_vrsbench_20260914.json, R3 vs R7).
            order = order[:1]
        deliberation["mode"] = "attribute_query_label_only" if attribute_query else "category_query_backtracking"
        order = [c for c in order if not any(_box_iou(c["xyxy"], x) > 0.5 for x in exclude)]
        order = order[: settings.agent_verification.max_candidates]

        fallback = None
        for rank_idx, cand in enumerate(order, start=1):
            entry = {
                "attempt": attempt,
                "reasoner_rank": rank_idx,
                "box": [round(float(v), 2) for v in cand["xyxy"]],
                "detector_confidence": round(float(cand.get("score", 0.0)), 4),
                "reasoning_score": cand.get("reasoning_score"),
            }
            if not use_verifier:
                entry.update(verifier_status="not_run", decision="accepted")
                deliberation["attempts"].append(entry)
                return cand, "unverified_no_verifier"
            v = verifier.verify(pil_img, cand["xyxy"], target_category)
            entry.update(
                verifier_status=v.status,
                verifier_confidence=v.target_probability,
                verifier_rank=v.target_rank,
                verifier_top_matches=v.as_dict()["top_alternatives"],
            )
            if v.status == VERIFIED:
                entry["decision"] = "accepted"
                deliberation["attempts"].append(entry)
                record_step("agent_deliberation", "success", tool="DetectionVerifier", details=entry)
                return cand, VERIFIED
            if v.status == CONTRADICTED and attribute_query:
                entry["decision"] = "accepted_disputed"
                deliberation["attempts"].append(entry)
                record_step("agent_deliberation", "warning", tool="DetectionVerifier", details=entry)
                return cand, CONTRADICTED
            if v.status == CONTRADICTED:
                entry["decision"] = "backtrack"
                deliberation["backtracks"] += 1
                exclude.append(cand["xyxy"])
                record_step("agent_deliberation", "warning", tool="DetectionVerifier", details=entry)
            elif allow_unconfirmed:
                entry["decision"] = "held_unconfirmed"
                record_step("agent_deliberation", "warning", tool="DetectionVerifier", details=entry)
                if fallback is None:
                    fallback = cand
            else:
                # Relaxed-threshold proposals are low-confidence by construction: only a candidate the
                # verification agent confirms is worth reporting. Measured: holding unconfirmed ones here
                # returned a box for 45.0% of absent-object queries vs 28.0% without, at identical
                # present-object recall (agent_deliberation_rules_vrsbench_20260914.json, R1 vs R3).
                entry["decision"] = "rejected_unconfirmed_after_relaxation"
                record_step("agent_deliberation", "warning", tool="DetectionVerifier", details=entry)
            deliberation["attempts"].append(entry)
        return (fallback, UNVERIFIED) if fallback is not None else (None, None)

    rejected: List[List[float]] = []
    selected_cand, verdict = deliberate(reasoning_res, "initial", rejected, allow_unconfirmed=True)

    relaxed = settings.agent_verification.relaxed_box_threshold
    if use_verifier and selected_cand is None and relaxed < box_threshold:
        deliberation["re_evaluated"] = True
        record_step("agent_re_evaluate", "started", details={
            "reason": "no candidate confirmed by both agents",
            "box_threshold": {"from": box_threshold, "to": relaxed}
        })
        relaxed_candidates, relaxed_res = detect_and_rank(relaxed, "re_evaluate")
        candidates = candidates or relaxed_candidates
        selected_cand, verdict = deliberate(relaxed_res, "re_evaluate", rejected, allow_unconfirmed=False)
        if selected_cand is not None:
            reasoning_res = relaxed_res
            candidates = relaxed_candidates

    deliberation["decision"] = {
        VERIFIED: "accepted_verified",
        UNVERIFIED: "accepted_unconfirmed",
        CONTRADICTED: "accepted_disputed",
        "unverified_no_verifier": "accepted_without_verification",
        None: "not_found",
    }[verdict]

    if selected_cand is None:
        contradicted_by = sorted({
            m["label"] for a in deliberation["attempts"] for m in a.get("verifier_top_matches", [])[:1]
        })
        reason = "all_candidates_contradicted_by_verifier" if deliberation["attempts"] else (
            "no_detector_candidates" if not candidates else "reasoner_filtered_all")
        record_step("select_target_candidate", "warning", details={"reason": reason})
        if deliberation["attempts"]:
            answer = (
                f"No {target_category} found for '{norm_query}'. The detector proposed "
                f"{len(deliberation['attempts'])} candidate(s)"
                f"{' including a relaxed re-evaluation' if deliberation['re_evaluated'] else ''}, "
                f"and the verification agent contradicted every one "
                f"(best matches instead: {', '.join(contradicted_by) or 'other categories'})."
            )
        elif not candidates:
            answer = f"No {target_category} detected in the satellite image matching '{norm_query}'."
        else:
            answer = f"Candidates detected but none satisfied the reasoning criteria for '{norm_query}'."
        return {
            "task": "grounding",
            "answer": answer,
            "selected_box": None,
            "segmentation_mask": None,
            "grounding_score": None,
            "sam2_score": None,
            "strategy": "V4_RELATIONAL",
            "evidence": {
                "target_category": target_category,
                "selected_box": None,
                "candidates_count": len(candidates),
                "reasoning_strategy": reason,
                "reference_evidence": reasoning_res.get("reference_evidence", {}),
                "agent_deliberation": deliberation,
            },
            "agent_deliberation": deliberation,
            "trace": trace
        }

    selected_box = selected_cand["xyxy"]
    grounding_score = float(selected_cand.get("score", 0.0))
    accepted_attempt = next((a for a in reversed(deliberation["attempts"]) if a["decision"] in ("accepted", "held_unconfirmed", "accepted_disputed")
                             and a["box"] == [round(float(v), 2) for v in selected_box]), {})
    record_step("select_target_candidate", "success", details={
        "selected_box": selected_box,
        "detector_score": round(grounding_score, 4),
        "reasoning_score": selected_cand.get("reasoning_score"),
        "decision": deliberation["decision"],
        "verifier_confidence": accepted_attempt.get("verifier_confidence"),
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

    # Step 9b: a category request ("mask trees", "segment all buildings") covers every instance, not only
    # the top-ranked one. Before Q-015 only selected_box reached SAM 2, so "mask trees" returned one tree.
    instances = [{"xyxy": [round(float(v), 2) for v in selected_box], "detector_confidence": round(grounding_score, 4),
                  "sam2_score": round(float(s_score), 4)}]
    multi_instance = _wants_all_instances(norm_query, str(reasoning_res.get("strategy", "")), parsed)
    reference_boxes = (reasoning_res.get("reference_evidence") or {}).get("reference_boxes") or []
    relation = parsed.get("relation") if reference_boxes else None
    dropped_by_relation = 0
    top_pixel_count = int(np.sum(np.squeeze(segmentation_mask) > 0)) if segmentation_mask is not None else 0
    if multi_instance and segmentation_mask is not None:
        combined = (np.squeeze(segmentation_mask) > 0)
        kept = [selected_box]
        for cand in reasoning_res.get("candidates", []):
            if len(kept) >= MAX_INSTANCES:
                break
            box = cand["xyxy"]
            if any(_box_iou(box, k) > iou_nms_threshold for k in kept):
                continue
            if any(_box_iou(box, r) > 0.5 for r in rejected):  # the verification agent contradicted it
                continue
            if relation and not _satisfies_relation(box, reference_boxes, relation, w, h):
                dropped_by_relation += 1
                continue
            try:
                inst = sam2.predict(image_or_context=pil_img, box=box, multimask_output=True)
            except Exception as e:
                record_step("call_sam2_instance", "error", tool="SAM2Adapter", details={"box": box, "error": str(e)})
                continue
            inst_mask = inst.get("mask") if isinstance(inst, dict) else getattr(inst, "mask", None)
            inst_score = inst.get("score") if isinstance(inst, dict) else getattr(inst, "score", 0.0)
            if inst_mask is None or np.squeeze(inst_mask).shape != combined.shape:
                continue
            combined |= (np.squeeze(inst_mask) > 0)
            kept.append(box)
            instances.append({"xyxy": [round(float(v), 2) for v in box],
                              "detector_confidence": round(float(cand.get("score", 0.0)), 4),
                              "sam2_score": round(float(inst_score), 4)})
        record_step("segment_all_instances", "success", tool="SAM2Adapter", details={
            "instances": len(instances), "cap": MAX_INSTANCES,
            "relation": relation, "reference_boxes": len(reference_boxes), "dropped_by_relation": dropped_by_relation,
            "note": "extra instances are ranked detector boxes; only the top one went through verification",
        })
        if len(instances) > 1:
            segmentation_mask = combined.astype(np.uint8)
            s_score = float(np.mean([i["sam2_score"] for i in instances]))
            sam2_res = {"mask": segmentation_mask, "score": s_score, "scores": s_scores,
                        "pixel_count": int(segmentation_mask.sum())}
    if aoi_mask is not None and segmentation_mask is not None and np.squeeze(segmentation_mask).shape == aoi_mask.shape:
        segmentation_mask = (np.squeeze(segmentation_mask) > 0).astype(np.uint8) & aoi_mask.astype(np.uint8)
        sam2_res = {"mask": segmentation_mask, "score": s_score, "scores": s_scores,
                    "pixel_count": int(segmentation_mask.sum())}
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
        "agent_deliberation": deliberation,
        "instance_count": len(instances),
        "instances": instances,
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
    box_txt = f"[{selected_box[0]:.1f}, {selected_box[1]:.1f}, {selected_box[2]:.1f}, {selected_box[3]:.1f}]"
    scores_txt = (f"detector confidence {grounding_score:.3f}, SAM 2 mask score {instances[0]['sam2_score']:.3f}, "
                  f"area {top_pixel_count:,} px")
    if verdict == VERIFIED:
        answer = (f"Found {target_category} at {box_txt}, confirmed by two agents: "
                  f"{scores_txt}, verification agent confidence {accepted_attempt.get('verifier_confidence'):.3f} "
                  f"(rank {accepted_attempt.get('verifier_rank')}).")
    elif verdict == CONTRADICTED:
        top = (accepted_attempt.get("verifier_top_matches") or [{}])[0]
        answer = (f"DISPUTED {target_category} at {box_txt}: the detector and reasoner selected it for the query's "
                  f"attributes ({scores_txt}), but the verification agent reads this region as "
                  f"'{top.get('label', 'another category')}' (rank {accepted_attempt.get('verifier_rank')} for {target_category}).")
    elif verdict == UNVERIFIED:
        top = (accepted_attempt.get("verifier_top_matches") or [{}])[0]
        answer = (f"UNCONFIRMED {target_category} at {box_txt}: {scores_txt}; the verification agent could not "
                  f"confirm the category (best match: {top.get('label', 'scene context')}).")
    else:
        answer = f"Segmented {target_category} at {box_txt} ({scores_txt}); verification agent unavailable."
    if deliberation["backtracks"]:
        answer += f" Backtracked past {deliberation['backtracks']} candidate(s) the verification agent contradicted."
    if deliberation["re_evaluated"]:
        answer += " Re-evaluated with a relaxed detector threshold."
    if len(instances) > 1:
        answer = (f"Segmented {len(instances)} instances of {target_category} ({mask_pixel_count:,} px in total, "
                  f"mean SAM 2 score {sam2_score:.3f}). Top-ranked instance: {answer}")

    return {
        "task": "grounding",
        "answer": answer,
        "selected_box": [round(float(c), 2) for c in selected_box],
        "segmentation_mask": segmentation_mask,
        "grounding_score": round(grounding_score, 4),
        "sam2_score": round(sam2_score, 4),
        "strategy": "V4_RELATIONAL",
        "detector": used_model,
        "instance_boxes": [i["xyxy"] for i in instances],
        "evidence": evidence,
        "agent_deliberation": deliberation,
        "trace": trace
    }

