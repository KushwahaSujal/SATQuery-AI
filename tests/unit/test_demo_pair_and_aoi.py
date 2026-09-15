"""
Unit tests validating the real demo GeoTIFF pair and AOI GeoJSON assets.
"""
import json
from pathlib import Path
import pytest
import rasterio
from shapely.geometry import shape, box
from shapely.ops import transform as shapely_transform
import pyproj

from backend.app.geo.raster import RasterInspector

DEMO_DIR = Path(__file__).resolve().parents[2] / "datasets" / "samples" / "demo"


def test_demo_geotiff_pair_exists_and_valid():
    path_before = DEMO_DIR / "before.tif"
    path_after = DEMO_DIR / "after.tif"

    assert path_before.exists(), f"Missing demo asset: {path_before}"
    assert path_after.exists(), f"Missing demo asset: {path_after}"

    meta_b = RasterInspector.inspect(path_before)
    meta_a = RasterInspector.inspect(path_after)

    # Individual metadata checks
    assert meta_b.is_georeferenced is True
    assert meta_a.is_georeferenced is True
    assert meta_b.crs == "EPSG:32630"
    assert meta_a.crs == "EPSG:32630"
    assert (meta_b.width, meta_b.height) == (512, 512)
    assert (meta_a.width, meta_a.height) == (512, 512)
    assert meta_b.bands == 3
    assert meta_a.bands == 3
    assert meta_b.resolution == [10.0, 10.0]
    assert meta_a.resolution == [10.0, 10.0]

    # Alignment checks
    assert meta_b.crs == meta_a.crs
    assert meta_b.transform == meta_a.transform
    assert meta_b.bounds == meta_a.bounds


def test_demo_aoi_geojson_valid_and_intersects_raster():
    path_aoi = DEMO_DIR / "aoi.geojson"
    path_before = DEMO_DIR / "before.tif"

    assert path_aoi.exists(), f"Missing AOI asset: {path_aoi}"

    with open(path_aoi, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("type") == "FeatureCollection"
    assert len(data.get("features", [])) >= 1

    feature = data["features"][0]
    geom = shape(feature["geometry"])
    assert geom.is_valid is True
    assert geom.geom_type == "Polygon"

    # Validate strictly within raster bounds
    with rasterio.open(path_before) as src:
        # Reproject AOI to raster CRS
        to_utm = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
        geom_utm = shapely_transform(to_utm, geom)
        raster_box = box(*src.bounds)

        assert geom_utm.intersects(raster_box) is True
        assert geom_utm.within(raster_box) is True
        assert geom_utm.area > 0
