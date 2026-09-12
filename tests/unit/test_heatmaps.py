"""
Unit tests for SatQuery AI Probability Heatmaps & Binary Prediction Masks
"""
import pytest
import numpy as np
from PIL import Image
from backend.app.visualization.heatmaps import HeatmapEngine
from backend.app.visualization.provenance import VisualizationType, LayerProvenance


def test_probability_heatmap_rendering():
    # Probability map with values 0.0 to 1.0
    prob_map = np.linspace(0.0, 1.0, 10000, dtype=np.float32).reshape(100, 100)
    base_img = Image.new("RGB", (100, 100), (50, 50, 50))

    composite, legend, meta = HeatmapEngine.render_probability_heatmap(
        prob_map, base_image=base_img, threshold=0.5, source_model="ChangeFormer"
    )

    assert isinstance(composite, Image.Image)
    assert isinstance(legend, Image.Image)
    assert meta.layer_type == VisualizationType.PROBABILITY_HEATMAP
    assert meta.provenance == LayerProvenance.MODEL_PROBABILITY
    assert meta.source_model == "ChangeFormer"
    assert meta.raw_stats["threshold"] == 0.5
    assert meta.min_value == 0.0
    assert meta.max_value == 1.0


def test_binary_prediction_mask_rendering():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:50, 20:50] = 1  # 900 changed pixels

    composite, meta = HeatmapEngine.render_binary_prediction_mask(
        mask, source_model="ChangeFormer"
    )

    assert isinstance(composite, Image.Image)
    assert meta.layer_type == VisualizationType.BINARY_MASK
    assert meta.provenance == LayerProvenance.MODEL_OUTPUT
    assert meta.raw_stats["changed_pixel_count"] == 900
    assert meta.raw_stats["total_pixel_count"] == 10000
    assert meta.raw_stats["changed_percentage"] == 9.0
