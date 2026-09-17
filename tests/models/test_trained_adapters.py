"""Real inference for the four locally trained adapters, one model at a time.

Each test skips when its checkpoint or its input tile is missing (both are gitignored), and each
runs on CPU and unloads before the next one, so the suite never competes with a training job for
GPU memory. These check the output contract — shapes, dtypes, ranges — not accuracy; the measured
scores are in docs/models/trained_segmenters.md and project/qna.md Q-026, Q-028, Q-029, Q-032.
"""
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pytest
import torch

from backend.app.config import settings
from backend.app.ml.adapters.binary_segmenter import BuildingSegmenterAdapter, RoadSegmenterAdapter
from backend.app.ml.adapters.crater_detector import CraterDetectorAdapter
from backend.app.ml.adapters.landcover_segmenter import LandCoverSegmenterAdapter

RAW = settings.root_dir / "datasets/raw"
DEEPGLOBE = RAW / "deepglobe_roads/train"
LUNAR = RAW / "craters_lu3m6tgt/LU3M6TGT_yolo_format/valid/images"


def cpu_adapter(cls):
    """An adapter pinned to CPU, or a skip when its checkpoint is not on disk."""
    adapter = cls()
    if not adapter.is_available():
        pytest.skip(f"{adapter.name} checkpoint not available at {adapter.checkpoint_path}")
    adapter.device = torch.device("cpu")
    return adapter


def first_tile(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.is_dir():
        return None
    return next(iter(sorted(directory.glob(pattern))), None)


def read_rgb(path: Path) -> np.ndarray:
    return cv2.cvtColor(cv2.imread(str(path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def deepglobe_pair() -> tuple[np.ndarray, np.ndarray]:
    """A DeepGlobe road tile (already 0.5 m) with its ground-truth mask."""
    sat = first_tile(DEEPGLOBE, "*_sat.jpg")
    if sat is None:
        pytest.skip(f"No DeepGlobe tile under {DEEPGLOBE}")
    mask_path = sat.with_name(f"{sat.name[: -len('_sat.jpg')]}_mask.png")
    if not mask_path.is_file():
        pytest.skip(f"DeepGlobe mask missing for {sat.name}")
    return read_rgb(sat), cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)


def test_road_segmenter_returns_a_non_empty_mask_on_a_deepglobe_tile():
    img, gt = deepglobe_pair()
    adapter = cpu_adapter(RoadSegmenterAdapter)
    try:
        result = adapter.predict(img)
    finally:
        adapter.unload()
    assert adapter.loaded is False

    assert result.model_name == "RoadSegmenter"
    assert result.task == "segmentation"
    assert len(result.masks) == 1
    entry = result.masks[0]
    mask, prob = entry["binary_mask"], entry["probability_map"]

    assert mask.shape == img.shape[:2] == prob.shape
    assert mask.dtype == np.uint8 and prob.dtype == np.float32
    assert set(np.unique(mask)).issubset({0, 1})
    assert 0.0 <= float(prob.min()) and float(prob.max()) <= 1.0

    # The tile has roads in its ground truth, so an empty prediction is a failure, not a threshold
    # choice. The threshold is the one frozen on validation inside the checkpoint.
    assert gt.max() > 127, "expected a DeepGlobe tile that contains roads"
    assert entry["pixel_count"] > 0
    assert result.metadata["pixel_count"] == int(mask.sum()) > 0
    assert result.metadata["threshold_source"] == "checkpoint"
    assert 0.0 < result.metadata["threshold"] < 1.0
    assert result.metadata["coverage_pct"] == pytest.approx(
        100.0 * mask.sum() / mask.size, abs=1e-3
    )
    assert result.metadata["class_name"] == "road"
    assert result.metadata["trained_gsd_m"] == 0.5
    assert result.metadata["encoder"] == "resnet50"
    assert 0.0 <= result.confidence <= 1.0

    # Predictions overlap the ground truth: test IoU on this dataset is 0.557 (Q-032), so a mask
    # that misses it entirely means the preprocessing is wrong, not that the model is weak.
    pred = mask > 0
    truth = gt > 127
    assert (pred & truth).sum() / max((pred | truth).sum(), 1) > 0.2


def test_road_segmenter_honours_a_requested_threshold():
    img, _ = deepglobe_pair()
    adapter = cpu_adapter(RoadSegmenterAdapter)
    try:
        low = adapter.predict(img, threshold=0.1)
        high = adapter.predict(img, threshold=0.9)
    finally:
        adapter.unload()
    assert low.metadata["threshold_source"] == "request"
    assert low.metadata["threshold"] == pytest.approx(0.1)
    # A lower threshold can only add foreground pixels.
    assert low.metadata["pixel_count"] >= high.metadata["pixel_count"]


def test_building_segmenter_output_contract_on_a_deepglobe_tile():
    img, _ = deepglobe_pair()
    adapter = cpu_adapter(BuildingSegmenterAdapter)
    try:
        # A 512-px window keeps this test cheap; the tile is rural, so no non-empty assertion.
        result = adapter.predict(img[:512, :512])
    finally:
        adapter.unload()

    entry = result.masks[0]
    assert entry["binary_mask"].shape == (512, 512)
    assert entry["binary_mask"].dtype == np.uint8
    assert entry["probability_map"].dtype == np.float32
    assert set(np.unique(entry["binary_mask"])).issubset({0, 1})
    assert result.metadata["class_name"] == "building"
    assert result.metadata["total_pixel_count"] == 512 * 512
    assert result.metadata["output_shape"] == [512, 512]


def test_landcover_segmenter_returns_per_class_masks_and_areas():
    img, _ = deepglobe_pair()
    adapter = cpu_adapter(LandCoverSegmenterAdapter)
    try:
        result = adapter.predict(img[:512, :512])
        classes = adapter.classes
    finally:
        adapter.unload()

    assert classes == ["other", "built_up", "agriculture", "rangeland", "forest", "water", "barren"]
    assert result.task == "land_cover_segmentation"
    assert set(result.metadata["area_pct"]) == set(classes)
    # Every pixel gets exactly one class, so the shares sum to 100%.
    assert sum(result.metadata["area_pct"].values()) == pytest.approx(100.0, abs=0.05)
    assert sum(result.metadata["pixel_counts"].values()) == 512 * 512
    assert result.metadata["dominant_class"] in classes

    assert result.masks, "expected at least one class to be present"
    counts = [m["pixel_count"] for m in result.masks]
    assert counts == sorted(counts, reverse=True)
    for entry in result.masks:
        assert entry["binary_mask"].shape == (512, 512)
        assert entry["binary_mask"].dtype == np.uint8
        assert entry["label"] in classes
        assert entry["pixel_count"] == int(entry["binary_mask"].sum()) > 0
    class_map = result.masks[0]["class_map"]
    assert class_map.shape == (512, 512) and class_map.dtype == np.uint8
    assert int(class_map.max()) < len(classes)
    assert 0.0 <= result.confidence <= 1.0


def test_crater_detector_returns_grounding_dino_shaped_boxes_on_a_lunar_tile():
    tile = first_tile(LUNAR, "*.png")
    if tile is None:
        pytest.skip(f"No LU3M6TGT tile under {LUNAR}")
    img = read_rgb(tile)
    adapter = cpu_adapter(CraterDetectorAdapter)
    try:
        result = adapter.predict(img, confidence_threshold=0.25)
    finally:
        adapter.unload()
    assert adapter.loaded is False

    h, w = img.shape[:2]
    assert result.task == "detection"
    assert result.metadata["detection_count"] == len(result.boxes)
    assert result.metadata["license"].startswith("AGPL-3.0")
    assert result.boxes, "LU3M6TGT tiles are crater-dense; expected at least one detection"
    scores = [b["score"] for b in result.boxes]
    assert scores == sorted(scores, reverse=True)
    for box in result.boxes:
        x1, y1, x2, y2 = box["xyxy"]
        assert 0.0 <= x1 <= x2 <= w and 0.0 <= y1 <= y2 <= h
        assert 0.25 <= box["score"] <= 1.0
        assert box["label"] == "crater"
        ymin, xmin, ymax, xmax = box["box_2d"]
        assert all(0.0 <= v <= 1.0 for v in (ymin, xmin, ymax, xmax))
        assert ymin <= ymax and xmin <= xmax
    assert result.confidence == pytest.approx(float(np.mean(scores)))
