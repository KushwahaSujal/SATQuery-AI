"""
Unit tests for SatQuery AI Pixel Inspector & Histogram Statistics
"""
import pytest
import numpy as np
from backend.app.visualization.inspector import InspectorEngine
from backend.app.geo.metadata import RasterMetadata


def test_pixel_to_geographic():
    # Affine transform: origin (500000, 4000000), 10m pixel resolution: [500000, 10, 0, 4000000, 0, -10]
    transform = [500000.0, 10.0, 0.0, 4000000.0, 0.0, -10.0]
    coords = InspectorEngine.pixel_to_geographic(col=50, row=30, transform=transform, crs="EPSG:32632")

    assert coords is not None
    geo_x, geo_y = coords
    assert geo_x == 500000.0 + 10.0 * 50.0  # 500500.0
    assert geo_y == 4000000.0 - 10.0 * 30.0  # 3999700.0


def test_inspect_pixel_values():
    arr = np.arange(3 * 10 * 10, dtype=np.uint8).reshape(3, 10, 10)
    meta = RasterMetadata(
        filepath="t.tif", filename="t.tif", format="TIFF", width=10, height=10, bands=3, dtype="uint8",
        crs=None, bounds=None, transform=None, resolution=None, nodata=None,
        band_descriptions=["Red", "Green", "Blue"], tags={}, is_georeferenced=False
    )

    data = InspectorEngine.inspect_pixel(arr, col=2, row=3, metadata=meta)
    assert data["pixel"] == {"col": 2, "row": 3}
    assert "Red" in data["band_values"]
    assert "Green" in data["band_values"]
    assert "Blue" in data["band_values"]


def test_histogram_calculation():
    arr = np.random.normal(50.0, 10.0, (100, 100)).astype(np.float32)
    hist = InspectorEngine.compute_histogram(arr, num_bins=50, units="DN")

    assert hist["total_pixels"] == 10000
    assert len(hist["bins"]) == 50
    assert "percentiles" in hist
    assert hist["percentiles"]["p2"] < hist["percentiles"]["p98"]
