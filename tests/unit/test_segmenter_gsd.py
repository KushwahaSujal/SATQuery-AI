"""A GeoTIFF's pixel size reaches the trained-segmenter answer (Q-063).

The water segmenter's answer said "no GSD metadata available" and warned about sub-metre aerial
photography on a 10 m Sentinel-2 GeoTIFF whose header states 10 m/px.
"""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from backend.app.workflows import trained_segmenter as ts

VALENCIA = Path("demo_resources/2_change_detection/sentinel2_valencia/before.tif")
PNG = Path("demo_resources/1_masking/airport_airplanes__P0173_0003.png")


def test_gsd_read_from_projected_geotiff_and_absent_for_png():
    assert ts.read_ground_sample_distance(str(VALENCIA)) == 10.0
    assert ts.read_ground_sample_distance(str(PNG)) is None
    assert ts.read_ground_sample_distance(Image.new("RGB", (4, 4))) is None


def _fake_adapter(pixels: int, size: int = 100):
    mask = np.zeros((size, size), dtype=np.uint8)
    mask.flat[:pixels] = 1
    result = SimpleNamespace(
        masks=[{"binary_mask": mask, "pixel_count": pixels}], confidence=0.95,
        metadata={"coverage_pct": 100.0 * pixels / mask.size, "threshold": 0.2,
                  "threshold_source": "checkpoint", "trained_gsd_m": 10.0})
    return SimpleNamespace(class_name="water", checkpoint_path="best.pt", predict=lambda img: result)


def _run(monkeypatch, gsd):
    monkeypatch.setattr(ts.model_registry, "get_adapter", lambda key: _fake_adapter(2_500))
    return ts.run_trained_segmenter_path("water_segmenter", Image.new("RGB", (100, 100)), "segment water",
                                         "water", lambda *a, **k: None, 0.0, gsd_m=gsd)["answer"]


def test_known_gsd_gives_area_and_drops_the_aerial_caveat(monkeypatch):
    answer = _run(monkeypatch, 10.0)
    assert "10 m/px" in answer and "0.25 km²" in answer          # 2,500 px x 100 m²
    assert "no GSD metadata" not in answer and "sub-metre aerial" not in answer


def test_unknown_gsd_keeps_the_original_wording(monkeypatch):
    answer = _run(monkeypatch, None)
    assert "no GSD metadata available" in answer and "sub-metre aerial" in answer
