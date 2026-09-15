"""GeoJSON area-of-interest input: parsing, CRS handling, rasterisation and structured errors (Q-011)."""
import json

import numpy as np
import pyproj
import pytest

from backend.app.geo.aoi import AOIError, aoi_bbox_ratio, load_aoi, rasterize_aoi, resolve_request_aoi
from backend.app.geo.metadata import RasterMetadata

# 1024 x 1024 raster, UTM 14N, 0.5 m pixels, origin (620000 E, 3350000 N)
UTM = RasterMetadata(filepath="x.tif", filename="x.tif", format="GeoTIFF", width=1024, height=1024, bands=3, dtype="uint8",
                     crs="EPSG:32614", transform=[0.5, 0.0, 620000.0, 0.0, -0.5, 3350000.0],
                     bounds=[620000.0, 3349488.0, 620512.0, 3350000.0], resolution=[0.5, 0.5], is_georeferenced=True)
PLAIN = RasterMetadata(filepath="x.png", filename="x.png", format="PNG", width=1024, height=1024, bands=3, dtype="uint8")
TO_WGS = pyproj.Transformer.from_crs("EPSG:32614", "EPSG:4326", always_xy=True).transform


def utm_rect_as_wgs84(x0, y0, x1, y1, densify=0):
    """A rectangle defined in UTM metres, expressed as an RFC 7946 lon/lat polygon."""
    xs = np.linspace(x0, x1, densify + 2)
    ys = np.linspace(y0, y1, densify + 2)
    ring = [(x, y0) for x in xs] + [(x1, y) for y in ys[1:]] + [(x, y1) for x in xs[::-1][1:]] + [(x0, y) for y in ys[::-1][1:]]
    return {"type": "Polygon", "coordinates": [[list(TO_WGS(x, y)) for x, y in ring]]}


def test_pixel_rows_and_columns_of_a_reprojected_aoi_are_exact():
    # columns 100..299 (x 620050..620150), rows 200..399 (y 3349900..3349800)
    aoi = load_aoi(utm_rect_as_wgs84(620050.0, 3349800.0, 620150.0, 3349900.0))
    assert aoi.crs == "EPSG:4326"
    r = rasterize_aoi(aoi, UTM)
    ys, xs = np.nonzero(r.mask)
    assert (xs.min(), xs.max(), ys.min(), ys.max()) == (100, 299, 200, 399)
    assert r.pixel_count == 200 * 200
    assert r.aoi_area_sq_m == pytest.approx(100.0 * 100.0, rel=1e-4)
    assert r.coverage_of_aoi == pytest.approx(1.0, abs=1e-6)


def test_accepts_feature_collection_json_string_and_file(tmp_path):
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": utm_rect_as_wgs84(620000.0, 3349900.0, 620050.0, 3349950.0)},
        {"type": "Feature", "properties": {}, "geometry": utm_rect_as_wgs84(620200.0, 3349900.0, 620250.0, 3349950.0)},
        {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [0, 0]}},
    ]}
    f = tmp_path / "aoi.geojson"
    f.write_text(json.dumps(fc))
    for src in (fc, json.dumps(fc), f):
        aoi = load_aoi(src)
        assert aoi.feature_count == 2
        assert rasterize_aoi(aoi, UTM).pixel_count == 2 * 100 * 100


def test_legacy_crs_member_is_honoured():
    doc = {"type": "Feature", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::32614"}},
           "geometry": {"type": "Polygon", "coordinates": [[[620000, 3350000], [620100, 3350000], [620100, 3349900], [620000, 3349900], [620000, 3350000]]]}}
    aoi = load_aoi(doc)
    assert aoi.crs == "EPSG:32614"
    assert rasterize_aoi(aoi, UTM).pixel_count == 200 * 200


def test_polygon_holes_are_excluded():
    outer = [[620000, 3350000], [620100, 3350000], [620100, 3349900], [620000, 3349900], [620000, 3350000]]
    hole = [[620025, 3349975], [620025, 3349925], [620075, 3349925], [620075, 3349975], [620025, 3349975]]
    doc = {"type": "Polygon", "crs": {"type": "name", "properties": {"name": "EPSG:32614"}}, "coordinates": [outer, hole]}
    assert rasterize_aoi(load_aoi(doc), UTM).pixel_count == 200 * 200 - 100 * 100


def test_partially_outside_reports_coverage():
    aoi = load_aoi(utm_rect_as_wgs84(620412.0, 3349800.0, 620612.0, 3349900.0))  # half east of the raster
    r = rasterize_aoi(aoi, UTM)
    assert r.coverage_of_aoi == pytest.approx(0.5, abs=0.01)
    assert r.pixel_count == 200 * 200


def test_errors_are_structured():
    with pytest.raises(AOIError) as outside:
        rasterize_aoi(load_aoi(utm_rect_as_wgs84(700000.0, 3349800.0, 700100.0, 3349900.0)), UTM)
    assert outside.value.code == "AOI_OUTSIDE_RASTER" and outside.value.status_code == 422

    with pytest.raises(AOIError) as plain:
        rasterize_aoi(load_aoi(utm_rect_as_wgs84(620050.0, 3349800.0, 620150.0, 3349900.0)), PLAIN)
    assert plain.value.code == "AOI_REQUIRES_GEOREFERENCED_RASTER"

    for bad in ({"type": "Point", "coordinates": [0, 0]}, "not json", {"no": "type"}):
        with pytest.raises(AOIError) as invalid:
            load_aoi(bad)
        assert invalid.value.code == "AOI_INVALID"


def test_request_parameters_and_box_helper(tmp_path):
    poly = utm_rect_as_wgs84(620050.0, 3349800.0, 620150.0, 3349900.0)
    assert resolve_request_aoi({}) is None
    assert resolve_request_aoi({"aoi_geojson": poly}).feature_count == 1
    (tmp_path / "a.geojson").write_text(json.dumps(poly))
    assert resolve_request_aoi({"aoi_filename": "a.geojson"}, tmp_path).crs == "EPSG:4326"
    with pytest.raises(AOIError):
        resolve_request_aoi({"aoi_filename": "missing.geojson"}, tmp_path)

    mask = rasterize_aoi(load_aoi(poly), UTM).mask
    assert aoi_bbox_ratio([150, 250, 200, 300], mask) == (True, 1.0)
    assert aoi_bbox_ratio([600, 600, 650, 650], mask)[0] is False
