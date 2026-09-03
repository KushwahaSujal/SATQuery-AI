"""
Unit tests for SatQuery AI Multispectral Composites & Single-Band Rendering
"""
import pytest
import numpy as np
from PIL import Image
from backend.app.visualization.composites import CompositeRenderer, _apply_percentile_stretch
from backend.app.visualization.provenance import VisualizationType, LayerProvenance


def test_apply_percentile_stretch():
    arr = np.linspace(0, 1000, 10000, dtype=np.float32).reshape(100, 100)
    norm, r_min, r_max, r_mean = _apply_percentile_stretch(arr, p_min=2.0, p_max=98.0)

    assert norm.dtype == np.uint8
    assert norm.shape == (100, 100)
    assert r_min == 0.0
    assert r_max == 1000.0
    assert norm.min() == 0
    assert norm.max() == 255


def test_render_true_color_3band():
    arr = np.random.randint(0, 255, (3, 64, 64), dtype=np.uint8)
    img, meta = CompositeRenderer.render_true_color(arr)

    assert isinstance(img, Image.Image)
    assert img.size == (64, 64)
    assert img.mode == "RGB"
    assert meta.layer_type == VisualizationType.TRUE_COLOR
    assert meta.provenance == LayerProvenance.SOURCE_DATA


def test_render_false_color_success_and_failure():
    # 4-band array [R, G, B, NIR]
    arr = np.random.randint(0, 255, (4, 64, 64), dtype=np.uint8)
    img, meta = CompositeRenderer.render_false_color(arr, band_indices=(3, 0, 1))

    assert isinstance(img, Image.Image)
    assert meta.layer_type == VisualizationType.FALSE_COLOR
    assert meta.provenance == LayerProvenance.DERIVED_INDEX

    # 3-band array cannot render false color with index 3
    arr_3b = np.random.randint(0, 255, (3, 64, 64), dtype=np.uint8)
    with pytest.raises(ValueError, match="requires band indices"):
        CompositeRenderer.render_false_color(arr_3b, band_indices=(3, 0, 1))


def test_render_single_band_with_colormap_legend():
    arr = np.random.randint(100, 5000, (1, 64, 64), dtype=np.uint16)
    img, legend, meta = CompositeRenderer.render_single_band(arr, band_idx=0, colormap="viridis")

    assert isinstance(img, Image.Image)
    assert isinstance(legend, Image.Image)
    assert meta.layer_type == VisualizationType.SINGLE_BAND
    assert meta.min_value >= 100
    assert meta.max_value <= 5000
