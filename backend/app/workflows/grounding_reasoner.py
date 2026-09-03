"""
SATQUERY AI — Production Grounding Reasoner (Notebook 4 V4 Reasoning)
Translates complex natural language spatial queries into structured attributes,
deduplicates candidates, and performs multi-criteria geometric & spatial reasoning
over Grounding DINO candidate boxes without using ground truth or chain-of-thought.
"""

import re
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image

from backend.app.logging import logger


# ==============================================================================
# 1. QUERY PARSER
# ==============================================================================

POSITION_KEYWORDS = {
    "top-left": (0.25, 0.25),
    "top-right": (0.75, 0.25),
    "bottom-left": (0.25, 0.75),
    "bottom-right": (0.75, 0.75),
    "bottom-middle": (0.50, 0.75),
    "bottom-center": (0.50, 0.75),
    "top-middle": (0.50, 0.25),
    "top-center": (0.50, 0.25),
    "top": (0.50, 0.25),
    "bottom": (0.50, 0.75),
    "left": (0.25, 0.50),
    "right": (0.75, 0.50),
    "center": (0.50, 0.50),
    "middle": (0.50, 0.50),
    "north": (0.50, 0.25),
    "south": (0.50, 0.75),
    "east": (0.75, 0.50),
    "west": (0.25, 0.50),
    "upper": (0.50, 0.25),
    "lower": (0.50, 0.75),
}

SIZE_KEYWORDS = {
    "largest": "large",
    "biggest": "large",
    "large": "large",
    "big": "large",
    "huge": "large",
    "smallest": "small",
    "tiny": "small",
    "small": "small",
    "medium": "medium",
    "longest": "long",
}

COLOR_KEYWORDS = {
    "white", "black", "red", "blue", "yellow", "green",
    "gray", "grey", "dark", "bright", "silver", "orange"
}

ORDINAL_KEYWORDS = {
    "first": 0,
    "second": 1,
    "third": 2,
    "fourth": 3,
    "fifth": 4,
    "last": -1,
    "leftmost": "leftmost",
    "rightmost": "rightmost",
    "topmost": "topmost",
    "bottommost": "bottommost",
}

RELATION_PATTERNS = [
    (r"\b(?:near|close to|next to|beside|adjacent to)\s+(?:the\s+|a\s+|an\s+)?([a-z\s]+)", "near"),
    (r"\b(?:above|north of|on top of)\s+(?:the\s+|a\s+|an\s+)?([a-z\s]+)", "above"),
    (r"\b(?:below|south of|underneath)\s+(?:the\s+|a\s+|an\s+)?([a-z\s]+)", "below"),
    (r"\b(?:to the left of|west of)\s+(?:the\s+|a\s+|an\s+)?([a-z\s]+)", "left_of"),
    (r"\b(?:to the right of|east of)\s+(?:the\s+|a\s+|an\s+)?([a-z\s]+)", "right_of"),
]


def parse_v4_query(query: str) -> Dict[str, Any]:
    """
    Parses a natural-language referring expression query into semantic components:
    - category (target subject to pass to detector)
    - position (spatial modifier)
    - size (relative size modifier)
    - color (color modifier)
    - ordinal (sequence selector)
    - relation & reference_category (relational modifier)
    """
    import re
    parsed: Dict[str, Any] = {
        "raw_query": query,
        "category": None,
        "position": None,
        "size": None,
        "color": None,
        "ordinal": None,
        "relation": None,
        "reference_category": None,
        "clean_prompt": None
    }

    # Normalize text: lowercase, remove punctuation except hyphens, strip colored/colour suffix
    norm_text = query.lower().strip()
    norm_text = re.sub(r"-(?:colored|colour|coloured)\b", "", norm_text)
    clean_text = re.sub(r"[^\w\s-]", " ", norm_text)

    # 1. Detect Relational Modifiers and Reference Objects
    for pattern, rel_type in RELATION_PATTERNS:
        match = re.search(pattern, clean_text)
        if match:
            parsed["relation"] = rel_type
            parsed["reference_category"] = match.group(1).strip()
            # Remove relational phrase to isolate target subject
            clean_text = clean_text[:match.start()] + " " + clean_text[match.end():]
            break

    # 2. Detect Position
    # Check multi-word positions first (top-left, bottom-right, bottom-middle, etc.)
    for pos_key in [
        "top-left", "top-right", "bottom-left", "bottom-right",
        "bottom-middle", "bottom-center", "top-middle", "top-center"
    ]:
        if pos_key in clean_text or pos_key.replace("-", " ") in clean_text:
            parsed["position"] = pos_key
            clean_text = clean_text.replace(pos_key, " ").replace(pos_key.replace("-", " "), " ")
            break

    tokens = clean_text.split()

    # Detect single-token positions if multi-word not matched
    if not parsed["position"]:
        for token in list(tokens):
            if token in POSITION_KEYWORDS:
                parsed["position"] = token
                tokens = [t for t in tokens if t != token]
                break

    # 3. Detect Ordinals
    for token in list(tokens):
        if token in ORDINAL_KEYWORDS:
            parsed["ordinal"] = token
            tokens = [t for t in tokens if t != token]
            break

    # 4. Detect Size
    for token in list(tokens):
        if token in SIZE_KEYWORDS:
            parsed["size"] = SIZE_KEYWORDS[token]
            tokens = [t for t in tokens if t != token]
            break

    # 5. Detect Color
    for token in list(tokens):
        # Also check strip of -color or -colored if any token remained
        base_token = re.sub(r"-.*", "", token)
        if token in COLOR_KEYWORDS or base_token in COLOR_KEYWORDS:
            parsed["color"] = token if token in COLOR_KEYWORDS else base_token
            tokens = [t for t in tokens if t != token]
            break

    # 6. Remaining tokens form the base category / subject
    # Remove common filler words, scene references, and user directive verbs
    stop_words = {
        "the", "a", "an", "that", "this", "these", "those", "is", "of", "and", "in", "on", "at",
        "find", "locate", "detect", "ground", "all", "one", "please", "can", "you",
        "highlight", "segment", "outline", "identify", "pinpoint", "mark", "show",
        "located", "situated", "positioned", "corner", "side", "part", "area", "portion",
        "image", "scene", "photo", "picture", "satellite", "colored", "colour", "color"
    }
    subject_tokens = [
        t for t in tokens
        if t not in stop_words
        and t not in POSITION_KEYWORDS
        and t not in COLOR_KEYWORDS
        and t not in SIZE_KEYWORDS
        and t not in ORDINAL_KEYWORDS
    ]
    category = " ".join(subject_tokens).strip()

    if not category:
        category = "object"

    parsed["category"] = category
    # Normalized prompt suitable for Grounding DINO
    parsed["clean_prompt"] = f"{category}."

    return parsed


# ==============================================================================
# 2. GEOMETRIC & ATTRIBUTE SCORING
# ==============================================================================

def position_score(box: List[float], img_shape: Tuple[int, int], target_pos: str) -> float:
    """
    Computes spatial position alignment score [0.0, 1.0] between a bounding box [x1, y1, x2, y2]
    and a target position anchor (e.g. 'top-left', 'center', 'right').
    """
    if not target_pos or target_pos not in POSITION_KEYWORDS:
        return 1.0

    width, height = img_shape
    if width <= 0 or height <= 0:
        return 1.0

    x1, y1, x2, y2 = box
    cx = (x1 + x2) / (2.0 * width)
    cy = (y1 + y2) / (2.0 * height)

    target_cx, target_cy = POSITION_KEYWORDS[target_pos]

    # Euclidean distance in normalized coordinate space [0, 1]
    dist = math.sqrt((cx - target_cx) ** 2 + (cy - target_cy) ** 2)
    # Gaussian decay centered at target anchor (sigma ~ 0.35)
    score = math.exp(- (dist ** 2) / (2.0 * (0.35 ** 2)))
    return max(0.0, min(1.0, float(score)))


def size_score(box: List[float], all_boxes: List[List[float]], target_size: str) -> float:
    """
    Computes relative size score [0.0, 1.0] compared to all candidate boxes.
    Supports 'large' / 'biggest' and 'small' / 'tiny' and 'medium'.
    """
    if not target_size or not all_boxes:
        return 1.0

    areas = [max(1.0, (b[2] - b[0]) * (b[3] - b[1])) for b in all_boxes]
    current_area = max(1.0, (box[2] - box[0]) * (box[3] - box[1]))

    min_area = min(areas)
    max_area = max(areas)

    if max_area == min_area:
        return 1.0

    norm_area = (current_area - min_area) / (max_area - min_area)

    if target_size == "large":
        return float(norm_area)
    elif target_size == "small":
        return float(1.0 - norm_area)
    elif target_size == "medium":
        # Score distance to median
        return float(1.0 - abs(norm_area - 0.5) * 2.0)
    return 1.0


def color_score(box: List[float], image: Optional[Union[Image.Image, np.ndarray]], target_color: str) -> float:
    """
    Computes photometric color consistency [0.0, 1.0] of image pixels within the candidate box.
    """
    if not target_color or image is None:
        return 1.0

    try:
        if isinstance(image, Image.Image):
            img_arr = np.array(image.convert("RGB"))
        elif isinstance(image, np.ndarray):
            img_arr = image if image.ndim == 3 else np.stack([image] * 3, axis=-1)
        else:
            return 1.0

        h, w = img_arr.shape[:2]
        x1 = max(0, min(int(box[0]), w - 1))
        y1 = max(0, min(int(box[1]), h - 1))
        x2 = max(x1 + 1, min(int(box[2]), w))
        y2 = max(y1 + 1, min(int(box[3]), h))

        patch = img_arr[y1:y2, x1:x2]
        if patch.size == 0:
            return 1.0

        mean_rgb = np.mean(patch, axis=(0, 1))
        r, g, b = mean_rgb[:3]
        brightness = (r + g + b) / 3.0

        color = target_color.lower()
        if color in ("white", "bright"):
            return float(min(1.0, brightness / 200.0))
        elif color in ("black", "dark"):
            return float(max(0.0, 1.0 - brightness / 100.0))
        elif color == "red":
            diff = max(0.0, r - max(g, b))
            return float(min(1.0, diff / 50.0 + 0.2))
        elif color == "blue":
            diff = max(0.0, b - max(r, g))
            return float(min(1.0, diff / 50.0 + 0.2))
        elif color == "green":
            diff = max(0.0, g - max(r, b))
            return float(min(1.0, diff / 50.0 + 0.2))
        elif color == "yellow":
            diff = min(r, g) - b
            return float(min(1.0, max(0.0, diff / 50.0 + 0.2)))
        elif color in ("gray", "grey", "silver"):
            spread = max(r, g, b) - min(r, g, b)
            return float(max(0.0, 1.0 - spread / 40.0))
        return 1.0
    except Exception:
        return 1.0


def nms_candidates(candidates: List[Dict[str, Any]], iou_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Standard Non-Maximum Suppression to deduplicate model candidate predictions.
    Does NOT use or reference ground truth.
    """
    if not candidates:
        return []

    # Sort by detector score descending
    sorted_candidates = sorted(candidates, key=lambda c: c.get("score", 0.0), reverse=True)
    kept: List[Dict[str, Any]] = []

    def compute_iou(b1: List[float], b2: List[float]) -> float:
        ix1 = max(b1[0], b2[0])
        iy1 = max(b1[1], b2[1])
        ix2 = min(b1[2], b2[2])
        iy2 = min(b1[3], b2[3])

        inter_w = max(0.0, ix2 - ix1)
        inter_h = max(0.0, iy2 - iy1)
        inter_area = inter_w * inter_h

        area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        union_area = area1 + area2 - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    for cand in sorted_candidates:
        box = cand["xyxy"]
        should_keep = True
        for kept_cand in kept:
            if compute_iou(box, kept_cand["xyxy"]) > iou_threshold:
                should_keep = False
                break
        if should_keep:
            kept.append(cand)

    return kept


def relation_score(target_box: List[float], reference_boxes: List[List[float]], relation: str) -> float:
    """
    Computes spatial relational score [0.0, 1.0] between a target candidate box
    and detected reference landmark boxes.
    """
    if not reference_boxes or not relation:
        return 1.0

    tx = (target_box[0] + target_box[2]) / 2.0
    ty = (target_box[1] + target_box[3]) / 2.0

    if relation in ("near", "close to", "next to", "beside", "adjacent to"):
        # Distance to closest reference object
        min_dist = min(
            math.sqrt((tx - (rb[0] + rb[2]) / 2.0) ** 2 + (ty - (rb[1] + rb[3]) / 2.0) ** 2)
            for rb in reference_boxes
        )
        # Normalized proximity decay
        return float(math.exp(-min_dist / 150.0))

    elif relation in ("above", "north of"):
        # Target should have lower Y than reference
        valid_refs = [rb for rb in reference_boxes if ty < (rb[1] + rb[3]) / 2.0]
        return 1.0 if valid_refs else 0.2

    elif relation in ("below", "south of"):
        # Target should have higher Y than reference
        valid_refs = [rb for rb in reference_boxes if ty > (rb[1] + rb[3]) / 2.0]
        return 1.0 if valid_refs else 0.2

    elif relation in ("left_of", "west of"):
        valid_refs = [rb for rb in reference_boxes if tx < (rb[0] + rb[2]) / 2.0]
        return 1.0 if valid_refs else 0.2

    elif relation in ("right_of", "east of"):
        valid_refs = [rb for rb in reference_boxes if tx > (rb[0] + rb[2]) / 2.0]
        return 1.0 if valid_refs else 0.2

    return 1.0


def ordinal_select(candidates: List[Dict[str, Any]], ordinal: str, axis: str = "x") -> Optional[Dict[str, Any]]:
    """
    Selects candidate based on spatial ordinal ranking ('first', 'second', 'leftmost', 'rightmost').
    """
    if not candidates:
        return None

    ord_key = str(ordinal).lower()

    if ord_key == "leftmost":
        return min(candidates, key=lambda c: c["xyxy"][0])
    elif ord_key == "rightmost":
        return max(candidates, key=lambda c: c["xyxy"][2])
    elif ord_key == "topmost":
        return min(candidates, key=lambda c: c["xyxy"][1])
    elif ord_key == "bottommost":
        return max(candidates, key=lambda c: c["xyxy"][3])

    idx = ORDINAL_KEYWORDS.get(ord_key)
    if isinstance(idx, int):
        # Sort along specified axis (default horizontal X)
        if axis == "y":
            sorted_c = sorted(candidates, key=lambda c: (c["xyxy"][1] + c["xyxy"][3]) / 2.0)
        else:
            sorted_c = sorted(candidates, key=lambda c: (c["xyxy"][0] + c["xyxy"][2]) / 2.0)

        if 0 <= idx < len(sorted_c):
            return sorted_c[idx]
        elif idx == -1 and sorted_c:
            return sorted_c[-1]
        # Fallback to closest available rank
        return sorted_c[min(max(0, idx), len(sorted_c) - 1)]

    return candidates[0]


def detect_reference_heuristic(
    image: Any,
    reference_category: str,
    min_area_pixels: int = 150
) -> List[Dict[str, Any]]:
    """
    Broad visual, color, and intensity region heuristic for geographical reference landmarks
    (e.g., water bodies, roads, runways, vegetation, open fields).

    IMPORTANT:
    This is purely a visual region heuristic.
    Boxes returned have score=None and is_heuristic=True.
    Heuristic regions must NEVER be reported as semantic model confidence.
    """
    if image is None:
        return []

    try:
        if isinstance(image, Image.Image):
            arr = np.array(image.convert("RGB"))
        elif isinstance(image, (str, Path)):
            arr = np.array(Image.open(image).convert("RGB"))
        elif isinstance(image, np.ndarray):
            arr = image if image.ndim == 3 else np.stack([image] * 3, axis=-1)
        else:
            return []

        h, w = arr.shape[:2]
        r = arr[:, :, 0].astype(np.float32)
        g = arr[:, :, 1].astype(np.float32)
        b = arr[:, :, 2].astype(np.float32)
        mean_int = (r + g + b) / 3.0
        color_spread = np.max(arr, axis=2) - np.min(arr, axis=2)

        cat = reference_category.lower().strip()

        if any(w in cat for w in ["road", "runway", "highway", "street", "pavement", "path"]):
            # Low saturation, moderate intensity concrete/asphalt
            mask = (color_spread < 25) & (mean_int > 50) & (mean_int < 180)
        elif any(w in cat for w in ["water", "river", "lake", "ocean", "sea", "canal"]):
            # Low reflectance or dominant blue component
            mask = (mean_int < 60) | ((b > r + 15) & (b > g))
        elif any(w in cat for w in ["vegetation", "grass", "field", "trees", "forest", "greenery"]):
            # Dominant green component
            mask = (g > r + 10) & (g > b)
        elif any(w in cat for w in ["building", "structure", "roof"]):
            # High intensity contrast / edges
            mask = (mean_int > 160) | (mean_int < 40)
        else:
            # Fallback to salient contrast region
            mask = (mean_int > 170) | (mean_int < 35)

        from scipy.ndimage import label, find_objects
        labeled, _ = label(mask)
        slices = find_objects(labeled)

        heuristic_boxes: List[Dict[str, Any]] = []
        for slc in slices:
            if slc is None:
                continue
            ymin, ymax = slc[0].start, slc[0].stop
            xmin, xmax = slc[1].start, slc[1].stop
            area = (ymax - ymin) * (xmax - xmin)
            if area >= min_area_pixels:
                heuristic_boxes.append({
                    "xyxy": [float(xmin), float(ymin), float(xmax), float(ymax)],
                    "label": reference_category,
                    "score": None,  # NEVER report heuristic as model confidence!
                    "is_heuristic": True,
                    "method": "visual_region_heuristic",
                    "area": area
                })

        # Sort largest regions first and limit to top 5
        heuristic_boxes.sort(key=lambda b: b.get("area", 0), reverse=True)
        return heuristic_boxes[:5]
    except Exception as e:
        logger.warning(f"Visual region heuristic detection failed for '{reference_category}': {e}")
        return []


def detect_reference(
    adapter: Optional[Any],
    image: Optional[Any],
    reference_category: str,
    box_threshold: float = 0.25,
    allow_heuristic_fallback: bool = True
) -> Tuple[List[Dict[str, Any]], str, Optional[float]]:
    """
    Detects reference landmark objects to support relational queries.
    Distinguishes strictly between:
    1. 'semantic_grounding_dino': Genuine Grounding DINO detection with detector confidence.
    2. 'visual_region_heuristic': Broad visual/color region heuristic. Never reports confidence.

    Returns:
        (reference_boxes, method, semantic_confidence)
        semantic_confidence is ONLY populated for genuine semantic detector outputs.
        For heuristic regions, semantic_confidence is ALWAYS None.
    """
    if not reference_category:
        return [], "none", None

    # 1. Attempt Semantic Grounding DINO Detection First
    if adapter is not None and image is not None:
        try:
            res = adapter.predict(
                image_or_context=image,
                prompt=f"{reference_category}.",
                box_threshold=box_threshold
            )
            raw_boxes = res.get("boxes", []) if isinstance(res, dict) else getattr(res, "boxes", [])
            if raw_boxes:
                boxes = []
                scores = []
                for b in raw_boxes:
                    sc = b.get("score")
                    if sc is not None:
                        scores.append(float(sc))
                    boxes.append({
                        "xyxy": b["xyxy"],
                        "label": b.get("label", reference_category),
                        "score": float(sc) if sc is not None else None,
                        "is_heuristic": False,
                        "method": "semantic_grounding_dino"
                    })
                avg_conf = float(np.mean(scores)) if scores else None
                return boxes, "semantic_grounding_dino", avg_conf
        except Exception as e:
            logger.warning(f"Semantic Grounding DINO reference detection failed for '{reference_category}': {e}")

    # 2. Broad Visual/Color Region Heuristic Fallback
    if allow_heuristic_fallback and image is not None:
        heuristic_boxes = detect_reference_heuristic(image, reference_category)
        if heuristic_boxes:
            # Semantic confidence is strictly None for heuristics
            return heuristic_boxes, "visual_region_heuristic", None

    return [], "none", None


# ==============================================================================
# 3. MULTI-CRITERIA RANKING & ORCHESTRATION
# ==============================================================================

def rank_v4_candidates(
    candidates: List[Dict[str, Any]],
    parsed_query: Dict[str, Any],
    img_shape: Tuple[int, int],
    image: Optional[Any] = None,
    reference_boxes: Optional[List[Dict[str, Any]]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Ranks candidate boxes using multi-criteria weighted scoring across detector confidence,
    spatial position, relative size, color consistency, and relational proximity.
    """
    if not candidates:
        return [], {}

    all_boxes = [c["xyxy"] for c in candidates]
    ref_boxes_raw = [r["xyxy"] for r in reference_boxes] if reference_boxes else []

    ranked = []
    for cand in candidates:
        box = cand["xyxy"]
        det_score = float(cand.get("score", 0.5))

        pos_s = position_score(box, img_shape, parsed_query.get("position") or "")
        sz_s = size_score(box, all_boxes, parsed_query.get("size") or "")
        clr_s = color_score(box, image, parsed_query.get("color") or "")
        rel_s = relation_score(box, ref_boxes_raw, parsed_query.get("relation") or "")

        # Compute weighted total score based on active query modifiers
        weights = {"detector": 0.40}
        scores = {"detector": round(det_score, 4)}

        if parsed_query.get("position"):
            weights["position"] = 0.25
            scores["position"] = round(pos_s, 4)
        if parsed_query.get("size"):
            weights["size"] = 0.20
            scores["size"] = round(sz_s, 4)
        if parsed_query.get("color"):
            weights["color"] = 0.15
            scores["color"] = round(clr_s, 4)
        if parsed_query.get("relation") and ref_boxes_raw:
            weights["relation"] = 0.30
            scores["relation"] = round(rel_s, 4)

        # Normalize weights
        total_w = sum(weights.values())
        norm_weights = {k: v / total_w for k, v in weights.items()}

        composite_score = (
            norm_weights.get("detector", 0) * det_score
            + norm_weights.get("position", 0) * pos_s
            + norm_weights.get("size", 0) * sz_s
            + norm_weights.get("color", 0) * clr_s
            + norm_weights.get("relation", 0) * rel_s
        )

        cand_with_reasoning = dict(cand)
        cand_with_reasoning["reasoning_score"] = round(float(composite_score), 4)
        cand_with_reasoning["reasoning_scores"] = scores
        ranked.append(cand_with_reasoning)

    ranked.sort(key=lambda c: c["reasoning_score"], reverse=True)
    best_scores = ranked[0]["reasoning_scores"] if ranked else {}
    return ranked, best_scores


def run_v4_reasoning(
    candidates: List[Dict[str, Any]],
    query: str,
    img_shape: Tuple[int, int],
    image: Optional[Any] = None,
    adapter: Optional[Any] = None,
    iou_nms_threshold: float = 0.50
) -> Dict[str, Any]:
    """
    Main V4 Reasoning Pipeline for Grounding.
    Consumes candidates from GroundingDINOAdapter, applies NMS deduplication,
    evaluates linguistic and spatial modifiers, and selects the optimal target box.

    Returns:
        {
            "selected_box": Dict[str, Any] or None,
            "strategy": str,
            "candidates": List[Dict[str, Any]],
            "parsed_query": Dict[str, Any],
            "reference_evidence": Dict[str, Any],
            "reasoning_scores": Dict[str, float]
        }
    """
    parsed = parse_v4_query(query)

    # 1. Deduplicate detector candidates with NMS
    deduped = nms_candidates(candidates, iou_threshold=iou_nms_threshold)

    if not deduped:
        return {
            "selected_box": None,
            "strategy": "empty_candidates",
            "candidates": [],
            "parsed_query": parsed,
            "reference_evidence": {
                "reference_category": parsed.get("reference_category"),
                "reference_count": 0,
                "method": "none",
                "is_heuristic": False,
                "semantic_confidence": None,
                "reference_boxes": []
            },
            "reasoning_scores": {}
        }

    # 2. Reference landmark detection if relational modifier present
    ref_boxes: List[Dict[str, Any]] = []
    ref_method: str = "none"
    ref_conf: Optional[float] = None

    if parsed.get("relation") and parsed.get("reference_category"):
        ref_boxes, ref_method, ref_conf = detect_reference(
            adapter=adapter,
            image=image,
            reference_category=parsed["reference_category"]
        )

    ref_evidence = {
        "reference_category": parsed.get("reference_category"),
        "reference_count": len(ref_boxes),
        "method": ref_method,
        "is_heuristic": (ref_method == "visual_region_heuristic"),
        "semantic_confidence": ref_conf,  # None if heuristic, float only for model detector
        "reference_boxes": [r["xyxy"] for r in ref_boxes]
    }

    # 3. Strategy Selection
    # Case A: Ordinal Directive ('first', 'second', 'leftmost')
    if parsed.get("ordinal"):
        axis = "y" if parsed.get("position") in ("top", "bottom") else "x"
        selected = ordinal_select(deduped, ordinal=parsed["ordinal"], axis=axis)
        strategy = f"ordinal_{parsed['ordinal']}"
        ranked, _ = rank_v4_candidates(deduped, parsed, img_shape, image, ref_boxes)
        return {
            "selected_box": selected,
            "strategy": strategy,
            "candidates": ranked,
            "parsed_query": parsed,
            "reference_evidence": ref_evidence,
            "reasoning_scores": selected.get("reasoning_scores", {"detector": selected.get("score", 0.0)}) if selected else {}
        }

    # Case B: Multi-attribute or relational ranking
    has_modifiers = any([
        parsed.get("position"),
        parsed.get("size"),
        parsed.get("color"),
        (parsed.get("relation") and ref_boxes)
    ])

    ranked, best_scores = rank_v4_candidates(
        candidates=deduped,
        parsed_query=parsed,
        img_shape=img_shape,
        image=image,
        reference_boxes=ref_boxes
    )

    strategy = "multi_attribute_ranking" if has_modifiers else "detector_confidence"
    selected = ranked[0] if ranked else None

    return {
        "selected_box": selected,
        "strategy": strategy,
        "candidates": ranked,
        "parsed_query": parsed,
        "reference_evidence": ref_evidence,
        "reasoning_scores": best_scores
    }
