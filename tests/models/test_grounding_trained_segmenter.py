"""Real end-to-end test for the trained-segmenter dispatch inside `run_grounding_pipeline`
(project/qna.md Q-025t, Q-026t, Q-038). Runs on CPU, on one small DeepGlobe tile already on disk;
skips when the tile or the checkpoint is missing (both are gitignored), matching the convention in
tests/models/test_trained_adapters.py.

This checks that "mark all roads" through the *full* pipeline entry point routes to the trained
segmenter, not just that the adapter works in isolation (already covered by
tests/models/test_trained_adapters.py) or that the dispatch decision is correct in isolation
(tests/unit/test_trained_segmenter_dispatch.py).
"""
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pytest
import torch

from backend.app.config import settings
from backend.app.ml.registry import model_registry
from backend.app.workflows.grounding import run_grounding_pipeline

RAW = settings.root_dir / "datasets/raw"
DEEPGLOBE = RAW / "deepglobe_roads/train"


def first_tile(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.is_dir():
        return None
    return next(iter(sorted(directory.glob(pattern))), None)


def deepglobe_pair():
    """The smallest DeepGlobe road tile on disk (by file size), with its ground-truth mask."""
    tiles = sorted(DEEPGLOBE.glob("*_sat.jpg"), key=lambda p: p.stat().st_size)
    if not tiles:
        pytest.skip(f"No DeepGlobe tile under {DEEPGLOBE}")
    sat = tiles[0]
    mask_path = sat.with_name(f"{sat.name[: -len('_sat.jpg')]}_mask.png")
    if not mask_path.is_file():
        pytest.skip(f"DeepGlobe mask missing for {sat.name}")
    img = cv2.cvtColor(cv2.imread(str(sat), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    gt = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    return img, gt


def test_mark_all_roads_routes_to_the_trained_segmenter_end_to_end():
    img, gt = deepglobe_pair()

    adapter = model_registry.get_adapter("roads_segmenter")
    if not adapter.is_available():
        pytest.skip(f"roads_segmenter checkpoint not available at {adapter.checkpoint_path}")
    adapter.device = torch.device("cpu")  # keep this test cheap and GPU-free, as in test_trained_adapters.py

    result = run_grounding_pipeline(image=img, query="mark all roads")

    # Routed to the trained segmenter, not Grounding DINO + SAM 2.
    assert result["strategy"] == "trained_segmenter_roads"
    assert result["detector"] == "roads_segmenter"
    assert result["selected_box"] is None
    assert result["grounding_score"] is None

    mask = result["segmentation_mask"]
    assert mask is not None
    assert mask.shape == img.shape[:2]

    pred = np.squeeze(mask) > 0
    pred_fraction = float(pred.sum()) / float(pred.size)
    # DeepGlobe roads are a small minority of pixels; a plausible prediction is non-trivial but not
    # most of the tile. Test IoU on this checkpoint's held-out DeepGlobe split is 0.557-0.569
    # (project/qna.md Q-032), so an empty or near-full-frame mask means something broke upstream of
    # the model, not that the model is weak.
    assert 0.0 < pred_fraction < 0.5

    truth = gt > 127
    if truth.any():
        iou = float((pred & truth).sum()) / float(max((pred | truth).sum(), 1))
        # Loose bound: this is one tile, not the held-out test split scored in Q-032. It only needs
        # to rule out a broken wiring (e.g. an empty prediction or the wrong image reaching the model).
        assert iou > 0.05

    ev = result["evidence"]
    assert ev["trained_segmenter"]["model_key"] == "roads_segmenter"
    assert ev["trained_segmenter"]["threshold"] is not None
    assert "trained_segmenter_roads" in [
        s for s in [result["strategy"]]
    ]
    trace_steps = [step["step"] for step in result["trace"]]
    assert "call_trained_segmenter" in trace_steps
    assert "validate_image" in trace_steps
    assert "parse_query" in trace_steps
    # Steps unique to the old detector + SAM 2 path never ran.
    assert "call_grounding_dino" not in trace_steps
    assert "call_sam2" not in trace_steps

    adapter.unload()
