"""
Unit tests for SatQuery AI Visualization Registry
"""
import pytest
import numpy as np
from backend.app.geo.metadata import RasterMetadata
from backend.app.visualization.registry import VisualizationRegistry
from backend.app.visualization.provenance import VisualizationType, LayerProvenance


def test_registry_optical_3band():
    meta = RasterMetadata(
        filepath="test.png",
        filename="test.png",
        format="PNG",
        width=256,
        height=256,
        bands=3,
        dtype="uint8",
        crs=None,
        bounds=None,
        transform=None,
        resolution=None,
        nodata=None,
        band_descriptions=["Red", "Green", "Blue"],
        tags={},
        is_georeferenced=False
    )

    layers = VisualizationRegistry.discover_available_layers([meta])
    layer_types = [l.layer_type for l in layers]

    assert VisualizationType.TRUE_COLOR in layer_types
    assert VisualizationType.SINGLE_BAND in layer_types
    # 3-band RGB should NOT have NDVI or false color NIR
    assert VisualizationType.SPECTRAL_INDEX not in layer_types
    assert VisualizationType.FALSE_COLOR not in layer_types


def test_registry_optical_4band_multispectral():
    meta = RasterMetadata(
        filepath="test_4b.tif",
        filename="test_4b.tif",
        format="GeoTIFF",
        width=512,
        height=512,
        bands=4,
        dtype="uint16",
        crs="EPSG:32632",
        bounds=[500000, 4000000, 505000, 4005000],
        transform=[500000, 10, 0, 4005000, 0, -10],
        resolution=[10, 10],
        nodata=0,
        band_descriptions=["Red", "Green", "Blue", "NIR"],
        tags={},
        is_georeferenced=True
    )

    layers = VisualizationRegistry.discover_available_layers([meta])
    layer_ids = [l.layer_id for l in layers]

    assert "true_color" in layer_ids
    assert "band_1" in layer_ids
    assert "band_4" in layer_ids
    assert "false_color_nir" in layer_ids
    assert "ndvi" in layer_ids
    assert "ndwi" in layer_ids


def test_registry_with_changeformer_results():
    meta1 = RasterMetadata(filepath="a.png", filename="a.png", format="PNG", width=256, height=256, bands=3, dtype="uint8", crs=None, bounds=None, transform=None, resolution=None, nodata=None, band_descriptions=[], tags={}, is_georeferenced=False)
    meta2 = RasterMetadata(filepath="b.png", filename="b.png", format="PNG", width=256, height=256, bands=3, dtype="uint8", crs=None, bounds=None, transform=None, resolution=None, nodata=None, band_descriptions=[], tags={}, is_georeferenced=False)

    model_res = {"changeformer": {"changed_percentage": 14.5}, "change_probability": True}
    layers = VisualizationRegistry.discover_available_layers([meta1, meta2], model_res)
    layer_ids = [l.layer_id for l in layers]

    assert "change_probability_heatmap" in layer_ids
    assert "change_binary_mask" in layer_ids
    assert "change_overlay" in layer_ids
    assert "comparison_split" in layer_ids
