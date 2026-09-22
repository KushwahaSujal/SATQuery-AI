"""Direct trained-segmenter dispatch for plain, unqualified whole-image category masks.

`run_grounding_pipeline` (backend/app/workflows/grounding.py) funnels every mask/box query through
Grounding DINO + V4 reasoning + SAM 2. project/qna.md Q-025t and Q-026t measured that this is a poor
architectural fit for "mark all roads" (IoU 0.031 pipeline vs 0.554-0.606 trained U-Net segmenter,
DeepGlobe/Massachusetts) and, less dramatically, for "mark all buildings" in dense scenes (WHU 0.635
vs 0.831, Massachusetts 0.191 vs 0.686). Q-032 adds the ResNet-50 + TTA numbers these checkpoints use.

This module provides:
  - `classify_trained_segmenter_target`: a pure function deciding whether a query should route here.
    No model I/O, so it is unit-testable without any checkpoint on disk (tests/unit/
    test_trained_segmenter_dispatch.py).
  - `run_trained_segmenter_path`: runs the adapter and shapes a response matching
    `run_grounding_pipeline`'s return contract, so `grounding.py`'s callers (backend/app/agent/tools/
    inference.py's `run_grounding`) need no changes.

See docs/models/trained_segmenters.md and project/qna.md Q-025t, Q-026t, Q-031, Q-032, Q-038.
"""
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PIL import Image

from backend.app.config import settings
from backend.app.exceptions import InferenceError
from backend.app.ml.registry import model_registry
from backend.app.logging import logger

# Duplicated, not imported, from backend/app/orchestration/intent_classifier.py's OBJECT_PATTERNS
# road/building/water groups (and its plural-forming `(?:e?s)?` suffix trick). Duplicating instead of
# importing keeps backend/app/workflows/ decoupled from backend/app/orchestration/ (the capability
# router), which the instructions for this change explicitly leave untouched. If the two vocabularies
# ever drift, tests/unit/test_trained_segmenter_dispatch.py's word-list assertions will fail.
# "cloud" has no OBJECT_PATTERNS group at all: mask-phrased cloud queries still reach this pipeline
# because the router's fallback noun-phrase extractor picks the noun out after a grounding verb
# (measured: "mask the clouds" -> single_image_grounding, category "clouds"), while the
# quality-question phrasings that should *not* segment anything ("is this scene cloudy", "how cloudy
# is this image", "remove the clouds") classify as single_image_vqa and never arrive here.
_ROAD_WORDS = r"\b(road|highway|street|runway|bridge|railway|track)(?:e?s)?\b"
_BUILDING_WORDS = r"\b(building|structure|house|facility|warehouse|terminal|hangar|shed|roof)(?:e?s)?\b"
# Water: `intent_classifier.py`'s own "water body|lake|river|pond|reservoir|coastline" group, plus
# bare "water" — "mask all water" is the canonical phrasing and parses to category "water".
_WATER_WORDS = r"\b(water|waterway|lake|river|pond|reservoir|lagoon|coastline)(?:e?s)?\b"
_CLOUD_WORDS = r"\b(cloud)(?:e?s)?\b"

# Compound nouns that contain a target's vocabulary word but name a *different* object, measured
# against the real parser rather than guessed: "mask all water tanks" parses to category
# "water tanks" and "mask the water tower" to "water tower", both of which bare `\bwater\b` would
# otherwise capture — and a storage tank is the detector's job, not a water segmenter's.
# "cloud shadow" is likewise a distinct class from cloud; 95-Cloud labels the cloud, not its shadow.
# ("waterfront", "watershed" and "cloudy" need no entry — `\b` already keeps them out.)
TRAINED_SEGMENTER_EXCLUSIONS: Dict[str, str] = {
    "water_segmenter": r"\bwater\s+(tank|tower|treatment|pump|pipe|main)",
    "cloud_segmenter": r"\bcloud\s+shadow",
}

# Registry key -> the vocabulary that query must match (and match *only*) to dispatch to it.
TRAINED_SEGMENTER_TARGETS: Dict[str, str] = {
    "roads_segmenter": _ROAD_WORDS,
    "buildings_segmenter": _BUILDING_WORDS,
    "water_segmenter": _WATER_WORDS,
    "cloud_segmenter": _CLOUD_WORDS,
}

# Registry key -> the strategy string returned instead of "V4_RELATIONAL", so this path is
# traceable and never confusable with a V4 (detector + reasoner + SAM 2) result in logs or evidence.
STRATEGY_BY_MODEL: Dict[str, str] = {
    "roads_segmenter": "trained_segmenter_roads",
    "buildings_segmenter": "trained_segmenter_buildings",
    "water_segmenter": "trained_segmenter_water",
    "cloud_segmenter": "trained_segmenter_cloud",
}

# What the mask is called in the answer. "the road network" reads naturally; "the water network"
# does not, so each model names its own product.
MASK_NOUN_BY_MODEL: Dict[str, str] = {
    "roads_segmenter": "road network",
    "buildings_segmenter": "building footprints",
    "water_segmenter": "water extent",
    "cloud_segmenter": "cloud cover",
}

# An extra sentence for models whose training imagery is a different *kind* of image from the
# sub-metre aerial photography a user is most likely to upload, not merely a different scale.
# Roads and buildings need no entry: at 0.5 m they are already in that regime.
SENSOR_CAVEAT_BY_MODEL: Dict[str, str] = {
    "water_segmenter": (
        " This model was trained on Sentinel-2 satellite imagery at 10 m/px, roughly 20x coarser "
        "than typical sub-metre aerial photography; its accuracy on high-resolution imagery has "
        "not been measured."
    ),
    "cloud_segmenter": (
        " This model was trained on Landsat 8 scenes at 30 m/px, far coarser than typical aerial "
        "photography; its accuracy on high-resolution imagery has not been measured."
    ),
}


def classify_trained_segmenter_target(
    norm_query: str, parsed: Dict[str, Any], wants_all_instances: bool
) -> Optional[str]:
    """Returns a registry key ("roads_segmenter" / "buildings_segmenter") when `norm_query` is a
    plain, unqualified whole-image category request for that class, else None.

    `wants_all_instances` must be `_wants_all_instances(norm_query, "", parsed)` from grounding.py —
    the exact same category-vs-single-target signal every other multi-instance decision in the
    pipeline already uses (size/position/ordinal qualifiers and the "all/every/mask/plural-noun"
    text check), not a second, divergent classifier. `parsed` is `parse_v4_query(norm_query)`'s
    output.

    Returns one of "roads_segmenter", "buildings_segmenter", "water_segmenter" or
    "cloud_segmenter".

    Falls through (returns None) to the existing Grounding DINO + SAM 2 path for: single-target,
    ordinal, size/position qualifiers (via `wants_all_instances=False`); relational qualifiers
    ("the road near the school") and colour qualifiers ("mask red buildings") — neither is a signal
    `_wants_all_instances` checks, so they are checked explicitly here; multiple classes in one query
    ("roads and buildings", "mask water and roads"); a compound noun that merely contains a target
    word but names another object ("water tanks", "cloud shadows" — `TRAINED_SEGMENTER_EXCLUSIONS`);
    and any class without a trained segmenter (cars, ships, planes, ...).

    Deliberately *not* routed, though checkpoints and adapters exist for them — see
    docs/models/trained_segmenters.md for the full argument:
      - **land cover** (7-class): its result is a class-index map, and every consumer of this
        pipeline's `segmentation_mask` treats that field as one binary mask (`fusion.py` does
        `segmentation_mask > 0` for the PNG and hands it to `mask_to_geojson(binary_mask=...)`), so
        a 7-class map would be silently reinterpreted as "class 0 is background, classes 1-6 are
        one object" and produce wrong area statistics and wrong polygons.
      - **ISPRS Potsdam / Vaihingen** (6-class, 0.1 m): choosing between them and the 0.5 m
        road/building models is a resolution-and-band decision, and no GSD or band metadata reaches
        this function. Guessing would be worse than falling through.
    """
    if not settings.trained_segmenter_routing.enabled:
        return None
    if not wants_all_instances:
        return None
    # Neither signal `_wants_all_instances` itself checks: a relational or colour-qualified request
    # needs a specific instance or attribute filter a class-only segmenter cannot apply.
    if parsed.get("relation") or parsed.get("color"):
        return None

    category_text = str(parsed.get("category") or "").lower()
    matches = [
        key for key, pattern in TRAINED_SEGMENTER_TARGETS.items()
        if re.search(pattern, category_text)
        and not re.search(TRAINED_SEGMENTER_EXCLUSIONS.get(key, r"(?!)"), category_text)
    ]
    if len(matches) != 1:
        return None  # no recognised class, or more than one ("roads and buildings")
    return matches[0]


def run_trained_segmenter_path(
    model_key: str,
    pil_img: Image.Image,
    norm_query: str,
    target_category: str,
    record_step: Callable[..., None],
    t0: float,
) -> Dict[str, Any]:
    """Runs the trained segmenter on the whole image and returns a dict shaped exactly like
    `run_grounding_pipeline`'s normal return, minus `trace` (the caller owns that list and appends
    to it via `record_step`, so it merges this path's steps with the ones already recorded for
    image validation and query parsing).

    GSD/resolution: the segmenters were trained at 0.5 m/px (project/qna.md Q-025t/Q-026t/Q-032).
    `run_grounding_pipeline` has no resolution metadata for an arbitrary uploaded image in the
    general case (no AgentState/GeoTIFF GSD is threaded this deep), so this runs the model at the
    image's native resolution and says so in the answer text — it does not invent an unvalidated
    resampling step. A caller that knows its image's GSD should resample to 0.5 m before calling
    `run_grounding_pipeline`.
    """
    adapter = model_registry.get_adapter(model_key)
    class_label = getattr(adapter, "class_name", None) or target_category
    strategy = STRATEGY_BY_MODEL[model_key]
    checkpoint_path = adapter.checkpoint_path

    record_step("call_trained_segmenter", "started", tool=type(adapter).__name__, details={
        "model": model_key, "checkpoint": str(checkpoint_path), "class_name": class_label
    })
    try:
        result = adapter.predict(pil_img)
    except Exception as e:
        record_step("call_trained_segmenter", "error", tool=type(adapter).__name__, details={"error": str(e)})
        raise InferenceError(f"{type(adapter).__name__} inference error: {e}", model_name=model_key) from e

    mask_entry = result.masks[0]
    mask = mask_entry["binary_mask"]
    total = int(mask.size)
    pixel_count = int(mask_entry.get("pixel_count", int(mask.sum())))
    coverage_pct = float(result.metadata.get("coverage_pct", 100.0 * pixel_count / total if total else 0.0))
    threshold = result.metadata.get("threshold")
    threshold_source = result.metadata.get("threshold_source")
    trained_gsd_m = result.metadata.get("trained_gsd_m")
    model_confidence = float(result.confidence) if result.confidence is not None else None

    record_step("call_trained_segmenter", "success", tool=type(adapter).__name__, details={
        "pixel_count": pixel_count, "coverage_pct": round(coverage_pct, 4),
        "threshold": threshold, "threshold_source": threshold_source, "confidence": model_confidence,
    })

    answer = (
        f"Segmented the {MASK_NOUN_BY_MODEL.get(model_key, f'{class_label} mask')}: "
        f"{coverage_pct:.2f}% of the image "
        f"({pixel_count:,} px), using the trained {class_label} segmenter "
        f"(checkpoint {Path(checkpoint_path).name if checkpoint_path else 'unknown'}, "
        f"threshold {threshold:.2f} from {threshold_source}). Trained and validated at "
        f"{trained_gsd_m} m/px ground sampling distance; this image was run at its native "
        f"resolution, with no GSD metadata available to resample it (docs/models/trained_segmenters.md)."
        f"{SENSOR_CAVEAT_BY_MODEL.get(model_key, '')}"
    )

    evidence: Dict[str, Any] = {
        "target_category": class_label,
        "selected_box": None,
        "mask_pixel_count": pixel_count,
        "mask_area_ratio": round(pixel_count / total, 6) if total else 0.0,
        "grounding_confidence": None,
        "sam2_confidence": None,
        "model_confidence": round(model_confidence, 4) if model_confidence is not None else None,
        "reasoning_scores": {},
        "reference_evidence": {"reference_boxes": [], "reference_count": 0, "method": "none"},
        "agent_deliberation": None,
        "instance_count": 1,
        "instance_filters": {},
        "instances": [{"xyxy": None, "detector_confidence": None, "sam2_score": None}],
        "all_candidates": [],
        "trained_segmenter": {
            "model_key": model_key,
            "checkpoint": str(checkpoint_path),
            "threshold": threshold,
            "threshold_source": threshold_source,
            "coverage_pct": round(coverage_pct, 4),
            "trained_gsd_m": trained_gsd_m,
            "encoder": result.metadata.get("encoder"),
            "tta": result.metadata.get("tta"),
        },
    }
    record_step("build_visual_evidence", "success", details={
        "mask_pixel_count": pixel_count, "confidence": model_confidence
    })
    record_step("complete_pipeline", "success", details={"elapsed_seconds": round(time.perf_counter() - t0, 3)})

    return {
        "task": "grounding",
        "answer": answer,
        "selected_box": None,
        "segmentation_mask": mask,
        "grounding_score": None,
        "sam2_score": round(model_confidence, 4) if model_confidence is not None else None,
        "strategy": strategy,
        "detector": model_key,
        "instance_boxes": [],
        "evidence": evidence,
        "agent_deliberation": None,
    }
