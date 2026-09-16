"""
Model tests for the production LocateAnythingAdapter (real weights, CUDA).
Skips cleanly when the checkpoint repo, CUDA, or the fixture images are missing.
"""

from pathlib import Path

import pytest
import torch
from PIL import Image

from backend.app.ml.adapters.locate_anything import LocateAnythingAdapter

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = ROOT / "checkpoints" / "locate_anything_3b"
TENNIS_TILE = ROOT / "tests" / "data" / "grounding" / "05933_0000.png"
# 512x512 airport apron: ONE airliner (right half); the long white shapes on the left are jet
# bridges, the small ones service vehicles. LocateAnything also returns jet bridges as "airplane"
# (known false positives, see docs/models/LOCATE_ANYTHING.md), so only the airliner is asserted.
AIRPORT_TILE = ROOT / "tests" / "data" / "grounding" / "airport_apron.png"
# Hand-read from the image: the airliner's extent in pixels.
AIRPLANE_GT = [265.0, 230.0, 512.0, 465.0]

pytestmark = [
    pytest.mark.skipif(not CHECKPOINT.is_dir(), reason=f"checkpoint repo missing: {CHECKPOINT}"),
    pytest.mark.skipif(not torch.cuda.is_available(), reason="LocateAnything model tests need CUDA"),
]


def _iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@pytest.fixture(scope="module")
def adapter():
    ad = LocateAnythingAdapter()
    if not ad.is_available():
        pytest.skip(f"LocateAnything unavailable: {ad._unavailable_reason()}")
    ad.load_model()
    yield ad
    ad.unload()


def test_airport_tile_finds_the_airliner_deterministically(adapter):
    if not AIRPORT_TILE.is_file():
        pytest.skip(f"fixture image missing: {AIRPORT_TILE}")
    image = Image.open(AIRPORT_TILE).convert("RGB")
    w, h = image.size

    first = adapter.predict(image, "airplane")
    second = adapter.predict(image, "airplane")

    assert first.boxes, first.metadata["raw_answer"]
    for box in first.boxes:
        x1, y1, x2, y2 = box["xyxy"]
        assert 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h
        assert box["bbox"] == box["xyxy"]
        assert box["label"] == "airplane"
    assert max(_iou(b["xyxy"], AIRPLANE_GT) for b in first.boxes) >= 0.5

    meta = first.metadata
    assert meta["truncated"] is False
    assert meta["generation_mode"] == "slow"
    assert meta["temperature"] == 0.0
    assert meta["raw_box_count"] >= len(first.boxes)

    # Greedy decoding: two calls give the same answer and boxes.
    assert second.metadata["raw_answer"] == meta["raw_answer"]
    assert [b["xyxy"] for b in second.boxes] == [b["xyxy"] for b in first.boxes]


def test_tennis_tile_has_no_airplane(adapter):
    if not TENNIS_TILE.is_file():
        pytest.skip(f"fixture image missing: {TENNIS_TILE}")
    result = adapter.predict(str(TENNIS_TILE), "airplane")
    assert result.boxes == [], result.metadata["raw_answer"]
    assert result.confidence is None
    assert "<box>None</box>" in result.metadata["raw_answer"]
    assert result.metadata["truncated"] is False
