"""
ChangeFormer accuracy regression tests — assert the model is *right*, not merely that it ran.

The previous in-repo network passed every shape/finite-value test while scoring IoU 0.019
on LEVIR-CD (it loaded strictly but computed something else). These tests would have caught
that. Floors sit below measured values with margin; see project/qna.md for the numbers.

Data (git-ignored, skipped when absent):
  datasets/raw/levircd/data/test-*.parquet       LEVIR-CD-256 test split
  datasets/raw/ayushman_levircd_1024/            LEVIR-CD 1024 test scenes 100/101/105 + labels
"""
import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from backend.app.exceptions import InvalidInputError
from backend.app.ml.adapters.changeformer import ChangeFormerAdapter

ROOT = Path(__file__).resolve().parents[2]
LEVIR_PARQUET = ROOT / "datasets/raw/levircd/data/test-00000-of-00001-31d7c3e3444e5b5d.parquet"
SCENES_1024 = ROOT / "datasets/raw/ayushman_levircd_1024"


def _iou(pred: np.ndarray, gt: np.ndarray) -> float:
    pred, gt = pred.astype(bool), gt.astype(bool)
    union = np.logical_or(pred, gt).sum()
    return float(np.logical_and(pred, gt).sum() / union) if union else 1.0


@pytest.fixture(scope="module")
def adapter() -> ChangeFormerAdapter:
    ad = ChangeFormerAdapter()
    if not ad._resolve_checkpoint_path().is_file():
        pytest.skip("ChangeFormer checkpoint not available")
    # Earlier tests leave other models resident on the GPU. These tests measure accuracy at native
    # resolution, so start from a clean GPU instead of depending on whatever ran before; the
    # out-of-memory fallback path is tested separately in tests/unit/test_gpu_oom_recovery.py.
    from backend.app.ml.registry import model_registry
    model_registry.release_gpu_memory(exclude=("changeformer",))
    ad.load_model()
    return ad


def _scene(name: str):
    if not (SCENES_1024 / f"{name}_label.png").is_file():
        pytest.skip(f"LEVIR-CD 1024 scene {name} not available in {SCENES_1024}")
    a = Image.open(SCENES_1024 / f"{name}_A.png").convert("RGB")
    b = Image.open(SCENES_1024 / f"{name}_B.png").convert("RGB")
    gt = np.array(Image.open(SCENES_1024 / f"{name}_label.png")) > 128
    return a, b, gt


def test_uses_frozen_validation_threshold(adapter):
    assert adapter._configured_threshold() == pytest.approx(0.435)


def test_levircd_test_subset_iou(adapter):
    if not LEVIR_PARQUET.is_file():
        pytest.skip("LEVIR-CD test parquet not available")
    import pyarrow.parquet as pq

    rows = pq.ParquetFile(LEVIR_PARQUET).read().to_pylist()[:64]
    tp = fp = fn = 0
    for r in rows:
        a = Image.open(io.BytesIO(r["imageA"]["bytes"])).convert("RGB")
        b = Image.open(io.BytesIO(r["imageB"]["bytes"])).convert("RGB")
        gt = np.array(Image.open(io.BytesIO(r["label"]["bytes"])).convert("L")) > 128
        pred = adapter.predict(a, b).masks[0]["binary_mask"] > 0
        tp += int((pred & gt).sum()); fp += int((pred & ~gt).sum()); fn += int((~pred & gt).sum())
    # Measured 0.7175 on these 64 pairs; the broken reimplementation scored ~0.02.
    assert tp / (tp + fp + fn) >= 0.68


@pytest.mark.parametrize("name,floor", [("test_100", 0.76), ("test_101", 0.58), ("test_105", 0.74)])
def test_1024_scene_native_iou(adapter, name, floor):
    a, b, gt = _scene(name)
    res = adapter.predict(a, b)
    assert res.metadata["inference_mode"] == "native"
    # Measured (filtered mask): test_100 0.8086, test_101 0.6289, test_105 0.7909.
    assert _iou(res.masks[0]["binary_mask"], gt) >= floor


def test_identical_pair_reports_no_change(adapter):
    a, _, _ = _scene("test_100")
    res = adapter.predict(a, a.copy())
    assert res.metadata["raw_change_pixel_count"] == 0


def test_windowed_path_matches_native_quality(adapter, monkeypatch):
    a, b, gt = _scene("test_100")
    monkeypatch.setattr(type(adapter), "max_native_side", property(lambda self: 256))
    res = adapter.predict(a, b)
    assert res.metadata["inference_mode"] == "windowed"
    assert res.masks[0]["binary_mask"].shape == (1024, 1024)
    # 256 windows measured raw IoU 0.7883 on this scene vs 0.8075 native.
    assert _iou(res.masks[0]["binary_mask"], gt) >= 0.74


def test_non_multiple_of_32_size_is_padded_and_cropped(adapter):
    rng = np.random.default_rng(0)
    a = rng.integers(0, 256, (300, 470, 3), dtype=np.uint8)
    b = rng.integers(0, 256, (300, 470, 3), dtype=np.uint8)
    res = adapter.predict(a, b)
    m = res.masks[0]
    assert m["binary_mask"].shape == (300, 470)
    assert m["change_prob_map"].shape == (300, 470)
    assert m["logits"].shape == (1, 2, 300, 470)
    assert np.all(np.isfinite(m["logits"]))


def test_mismatched_sizes_rejected(adapter):
    a = np.zeros((256, 256, 3), dtype=np.uint8)
    b = np.zeros((256, 300, 3), dtype=np.uint8)
    with pytest.raises(InvalidInputError):
        adapter.predict(a, b)
