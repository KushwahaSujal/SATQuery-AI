"""
Unit tests for SatQuery AI Remote-Sensing Spectral Indices (NDVI, NDWI)
"""
import pytest
import numpy as np
from PIL import Image
from backend.app.visualization.indices import SpectralIndexEngine
from backend.app.geo.metadata import RasterMetadata
from backend.app.visualization.provenance import VisualizationType, LayerProvenance


def test_ndvi_with_4band_multispectral():
    # Shape: (4, 64, 64) -> [Red, Green, Blue, NIR]
    # Simulate high vegetation: high NIR (0.8), low Red (0.1)
    arr = np.zeros((4, 64, 64), dtype=np.float32)
    arr[0] = 0.1  # Red
    arr[1] = 0.2  # Green
    arr[2] = 0.1  # Blue
    arr[3] = 0.8  # NIR

    meta = RasterMetadata(
        filepath="multi.tif",
        filename="multi.tif",
        format="GeoTIFF",
        width=64,
        height=64,
        bands=4,
        dtype="float32",
        crs="EPSG:4326",
        bounds=[-122.4, 37.7, -122.3, 37.8],
        transform=None,
        resolution=None,
        nodata=None,
        band_descriptions=["Red", "Green", "Blue", "NIR"],
        tags={},
        is_georeferenced=True
    )

    res = SpectralIndexEngine.compute_ndvi(arr, meta)

    assert res.available is True
    assert res.image is not None
    assert res.legend is not None
    assert res.raw_array is not None
    # (0.8 - 0.1) / (0.8 + 0.1) = 0.7 / 0.9 = ~0.7778
    assert pytest.approx(float(res.raw_array[0, 0]), 0.01) == 0.778
    assert res.metadata.layer_type == VisualizationType.SPECTRAL_INDEX
    assert res.metadata.provenance == LayerProvenance.DERIVED_INDEX


def test_ndvi_missing_nir_returns_index_not_available():
    # Standard 3-band RGB imagery has no NIR
    arr_3b = np.random.randint(0, 255, (3, 64, 64), dtype=np.uint8)
    meta_3b = RasterMetadata(
        filepath="rgb.png",
        filename="rgb.png",
        format="PNG",
        width=64,
        height=64,
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

    res = SpectralIndexEngine.compute_ndvi(arr_3b, meta_3b)

    assert res.available is False
    assert res.image is None
    assert "INDEX_NOT_AVAILABLE" in res.unavailability_reason
    assert "Near-Infrared" in res.unavailability_reason


def test_ndwi_calculation():
    # Green=0.7, NIR=0.2 (water body)
    arr = np.zeros((4, 32, 32), dtype=np.float32)
    arr[0] = 0.1
    arr[1] = 0.7  # Green
    arr[2] = 0.1
    arr[3] = 0.2  # NIR

    meta = RasterMetadata(
        filepath="water.tif", filename="water.tif", format="TIFF",
        width=32, height=32, bands=4, dtype="float32",
        crs=None, bounds=None, transform=None, resolution=None, nodata=None,
        band_descriptions=["Red", "Green", "Blue", "NIR"], tags={}, is_georeferenced=False
    )

    res = SpectralIndexEngine.compute_ndwi(arr, meta)
    assert res.available is True
    # (0.7 - 0.2) / (0.7 + 0.2) = 0.5 / 0.9 = ~0.5556
    assert pytest.approx(float(res.raw_array[0, 0]), 0.01) == 0.556
