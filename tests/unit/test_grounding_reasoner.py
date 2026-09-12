"""
Unit tests for production Grounding Reasoner (Notebook 4 V4 Reasoning).
Verifies parsing, scoring functions, NMS candidate deduplication,
ordinal selection, multi-attribute ranking, and final reasoning output contract.
"""

import pytest
import numpy as np
from PIL import Image

from backend.app.workflows.grounding_reasoner import (
    parse_v4_query,
    position_score,
    size_score,
    color_score,
    nms_candidates,
    relation_score,
    ordinal_select,
    detect_reference,
    rank_v4_candidates,
    run_v4_reasoning,
)


def test_parse_v4_query():
    # 1. Complex multi-modifier query
    q1 = "find the small white vehicle on the top-left near the runway"
    p1 = parse_v4_query(q1)
    assert p1["category"] == "vehicle"
    assert p1["size"] == "small"
    assert p1["color"] == "white"
    assert p1["position"] == "top-left"
    assert p1["relation"] == "near"
    assert p1["reference_category"] == "runway"
    # Deliberate contract change (project/pre-demo.md 3f): the colour now stays in the
    # prompt. It used to be stripped, which made "red car" and "yellow car" identical
    # to the detector. This assertion previously read "vehicle."
    assert p1["clean_prompt"] == "white vehicle."

    # 2. Ordinal query
    q2 = "locate the second largest airplane"
    p2 = parse_v4_query(q2)
    assert p2["category"] == "airplane"
    assert p2["ordinal"] == "second"
    assert p2["size"] == "large"

    # 3. Simple category
    q3 = "storage tank."
    p3 = parse_v4_query(q3)
    assert p3["category"] == "storage tank"
    assert p3["position"] is None


def test_position_score():
    img_shape = (256, 256)
    # Box in top-left quadrant [20, 20, 50, 50]
    box_tl = [20.0, 20.0, 50.0, 50.0]
    # Box in bottom-right quadrant [200, 200, 240, 240]
    box_br = [200.0, 200.0, 240.0, 240.0]

    score_tl_tl = position_score(box_tl, img_shape, "top-left")
    score_br_tl = position_score(box_br, img_shape, "top-left")
    assert score_tl_tl > score_br_tl
    assert score_tl_tl > 0.70


def test_size_score():
    boxes = [
        [10.0, 10.0, 20.0, 20.0],  # area = 100
        [10.0, 10.0, 50.0, 50.0],  # area = 1600
        [10.0, 10.0, 100.0, 100.0] # area = 8100
    ]
    score_small = size_score(boxes[0], boxes, "small")
    score_large = size_score(boxes[0], boxes, "large")
    assert score_small > score_large

    score_big_large = size_score(boxes[2], boxes, "large")
    assert score_big_large == 1.0


def test_nms_candidates():
    candidates = [
        {"xyxy": [10.0, 10.0, 30.0, 30.0], "score": 0.90, "label": "car"},
        {"xyxy": [12.0, 12.0, 31.0, 31.0], "score": 0.85, "label": "car"}, # Overlapping with box 1
        {"xyxy": [100.0, 100.0, 120.0, 120.0], "score": 0.75, "label": "car"}, # Distinct
    ]
    kept = nms_candidates(candidates, iou_threshold=0.5)
    assert len(kept) == 2
    assert kept[0]["score"] == 0.90
    assert kept[1]["score"] == 0.75


def test_ordinal_select():
    candidates = [
        {"xyxy": [100.0, 50.0, 120.0, 70.0], "score": 0.8}, # Right
        {"xyxy": [20.0, 50.0, 40.0, 70.0], "score": 0.9},   # Left
        {"xyxy": [60.0, 50.0, 80.0, 70.0], "score": 0.7},   # Middle
    ]
    leftmost = ordinal_select(candidates, "leftmost")
    assert leftmost["xyxy"][0] == 20.0

    second = ordinal_select(candidates, "second")
    assert second["xyxy"][0] == 60.0


def test_run_v4_reasoning_pipeline():
    candidates = [
        {"xyxy": [10.0, 10.0, 25.0, 25.0], "score": 0.85, "label": "vehicle"},  # small, top-left
        {"xyxy": [200.0, 200.0, 250.0, 250.0], "score": 0.85, "label": "vehicle"}, # large, bottom-right
        {"xyxy": [120.0, 120.0, 135.0, 135.0], "score": 0.80, "label": "vehicle"}, # small, center
    ]

    # Query targeting the small vehicle on the top-left
    res = run_v4_reasoning(
        candidates=candidates,
        query="the small vehicle on the top-left",
        img_shape=(256, 256)
    )

    assert "selected_box" in res
    assert "strategy" in res
    assert "candidates" in res
    assert "parsed_query" in res
    assert "reference_evidence" in res
    assert "reasoning_scores" in res

    selected = res["selected_box"]
    assert selected is not None
    # Candidate 0 should be selected due to high position (top-left) and size (small) alignment
    assert selected["xyxy"] == [10.0, 10.0, 25.0, 25.0]
    assert res["strategy"] == "multi_attribute_ranking"
    assert "position" in res["reasoning_scores"]
    assert "size" in res["reasoning_scores"]


def test_reference_detection_distinction():
    # 1. Semantic Grounding DINO Detection
    class MockGroundingAdapter:
        def predict(self, image_or_context, prompt, box_threshold=0.25):
            return {
                "boxes": [
                    {"xyxy": [50.0, 50.0, 150.0, 150.0], "score": 0.82, "label": "runway"}
                ]
            }

    dummy_img = Image.new("RGB", (200, 200), color=(128, 128, 128))
    boxes, method, conf = detect_reference(
        adapter=MockGroundingAdapter(),
        image=dummy_img,
        reference_category="runway"
    )
    assert method == "semantic_grounding_dino"
    assert conf == 0.82
    assert len(boxes) == 1
    assert boxes[0]["is_heuristic"] is False
    assert boxes[0]["score"] == 0.82

    # 2. Broad Visual/Color Region Heuristic Fallback
    # (No adapter provided -> falls back to visual heuristic)
    # Image with road-like gray stripe in the middle
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    arr[40:60, :] = [100, 100, 100] # Gray road band
    heuristic_img = Image.fromarray(arr)

    boxes_h, method_h, conf_h = detect_reference(
        adapter=None,
        image=heuristic_img,
        reference_category="road"
    )
    assert method_h == "visual_region_heuristic"
    assert conf_h is None  # Never reported as confidence!
    assert len(boxes_h) >= 1
    assert boxes_h[0]["is_heuristic"] is True
    assert boxes_h[0]["score"] is None

    # 3. Test evidence metadata propagation in run_v4_reasoning
    candidates = [{"xyxy": [10.0, 10.0, 20.0, 20.0], "score": 0.9, "label": "vehicle"}]
    res = run_v4_reasoning(
        candidates=candidates,
        query="vehicle near the road",
        img_shape=(100, 100),
        image=heuristic_img,
        adapter=None
    )
    evidence = res["reference_evidence"]
    assert evidence["method"] == "visual_region_heuristic"
    assert evidence["is_heuristic"] is True
    assert evidence["semantic_confidence"] is None


def test_spot_is_treated_as_a_verb_not_part_of_the_object():
    """'spot' was missing from the verb stoplist, so 'spot a red car' asked the
    detector for a nonexistent "spot car" class (project/pre-demo.md 3f)."""
    for verb in ("spot", "show", "highlight", "locate", "find"):
        p = parse_v4_query(f"{verb} a car")
        assert p["category"] == "car", f"{verb!r} leaked into the category: {p['category']!r}"


def test_colour_reaches_the_detector_prompt():
    """Colour was parsed then stripped, so 'red car' and 'yellow car' produced a
    byte-identical prompt and the tool could not tell them apart (3f)."""
    red = parse_v4_query("spot a red car")
    yellow = parse_v4_query("spot a yellow car")
    white = parse_v4_query("spot white cars")

    assert red["color"] == "red" and yellow["color"] == "yellow" and white["color"] == "white"
    assert red["category"] == "car" and yellow["category"] == "car"

    assert red["clean_prompt"] == "red car."
    assert yellow["clean_prompt"] == "yellow car."
    assert white["clean_prompt"] == "white cars."
    assert red["clean_prompt"] != yellow["clean_prompt"], "red and yellow must differ"


def test_colourless_queries_are_unchanged():
    """Regression guard: queries without a colour keep the bare category prompt."""
    assert parse_v4_query("find all vehicles")["clean_prompt"] == "vehicles."
    assert parse_v4_query("storage tank.")["clean_prompt"] == "storage tank."
