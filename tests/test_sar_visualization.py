"""
Unit tests for SatQuery AI SAR Visualization Engine
"""
import pytest
import numpy as np
from PIL import Image
from backend.app.visualization.sar import SARVisualizationEngine
from backend.app.geo.metadata import RasterMetadata
from backend.app.visualization.provenance import VisualizationType, LayerProvenance


def test_sar_polarization_rendering():
    # 2-band dual-pol [VV, VH]
    arr = np.random.uniform(0.01, 1.5, (2, 64, 64)).astype(np.float32)

    meta = RasterMetadata(
        filepath="sar.tif",
        filename="sar.tif",
        format="GeoTIFF",
        width=64,
        height=64,
        bands=2,
        dtype="float32",
        crs="EPSG:32632",
        bounds=None,
        transform=None,
        resolution=[10, 10],
        nodata=None,
        band_descriptions=["VV", "VH"],
        tags={"SENSOR": "Sentinel-1 SAR", "UNITS": "Sigma0 Linear"},
        is_georeferenced=True
    )

    img, legend, layer_meta = SARVisualizationEngine.render_polarization_layer(arr, "VV", meta)
    assert isinstance(img, Image.Image)
    assert isinstance(legend, Image.Image)
    assert layer_meta.layer_type == VisualizationType.SAR_POLARIZATION
    assert layer_meta.units == "Sigma0 Linear"

    # Test dual-pol composite
    comp_img, comp_meta = SARVisualizationEngine.render_dual_pol_composite(arr, meta)
    assert isinstance(comp_img, Image.Image)
    assert comp_meta.layer_type == VisualizationType.SAR_POLARIZATION
    assert comp_meta.provenance == LayerProvenance.DERIVED_INDEX


def test_sar_db_conversion():
    arr = np.ones((1, 32, 32), dtype=np.float32) * 10.0  # 10 linear power
    meta = RasterMetadata(
        filepath="sar_1b.tif", filename="sar_1b.tif", format="TIFF",
        width=32, height=32, bands=1, dtype="float32",
        crs=None, bounds=None, transform=None, resolution=None, nodata=None,
        band_descriptions=["VV"], tags={"UNITS": "Power"}, is_georeferenced=False
    )

    img, legend, layer_meta = SARVisualizationEngine.render_polarization_layer(arr, "VV", meta, to_db=True)
    assert "dB" in layer_meta.units
    # 10*log10(10) = 10 dB
    assert pytest.approx(layer_meta.mean_value, 0.1) == 10.0
