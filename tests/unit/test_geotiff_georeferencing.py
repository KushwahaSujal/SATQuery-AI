"""
GeoTIFF georeferencing without rasterio: CRS, affine transform, bounds, area and GeoJSON output.

Before this, the tifffile path hard-coded crs=None, so every GeoTIFF was treated as a plain image —
no metric area, GeoJSON in pixel coordinates (project/qna.md Q-009).
"""
import numpy as np
import pyproj
import pytest
import tifffile
from shapely.geometry import shape
from shapely.ops import transform as shp_transform

from backend.app.geo.raster import RasterInspector
from backend.app.geo.statistics import calculate_area_statistics
from backend.app.geo.vectors import mask_to_geojson


def _write(path, arr, geokeys=None, scale=None, tiepoint=None, matrix=None, nodata=None):
    tags = []
    if scale is not None:
        tags.append((33550, "d", 3, tuple(scale), False))
    if tiepoint is not None:
        tags.append((33922, "d", 6, tuple(tiepoint), False))
    if matrix is not None:
        tags.append((34264, "d", 16, tuple(matrix), False))
    if geokeys is not None:
        tags.append((34735, "H", len(geokeys), tuple(geokeys), False))
    if nodata is not None:
        tags.append((42113, "s", 0, str(nodata), False))
    tifffile.imwrite(path, arr, photometric="rgb" if arr.ndim == 3 else "minisblack", extratags=tags)
    return path


def _keys(*entries):
    return (1, 1, 0, len(entries)) + tuple(v for e in entries for v in e)


UTM14N = _keys((1024, 0, 1, 1), (1025, 0, 1, 1), (3072, 0, 1, 32614))
WGS84 = _keys((1024, 0, 1, 2), (1025, 0, 1, 1), (2048, 0, 1, 4326))
RGB = np.zeros((100, 200, 3), dtype=np.uint8)


def test_projected_utm_from_scale_and_tiepoint(tmp_path):
    p = _write(tmp_path / "utm.tif", RGB, UTM14N, scale=(0.5, 0.5, 0), tiepoint=(0, 0, 0, 620000.0, 3350000.0, 0))
    m = RasterInspector.inspect(p)
    assert m.is_georeferenced and m.format == "GeoTIFF"
    assert m.crs == "EPSG:32614"
    assert m.transform == [0.5, 0.0, 620000.0, 0.0, -0.5, 3350000.0]
    assert m.bounds == [620000.0, 3349950.0, 620100.0, 3350000.0]
    assert m.resolution == [0.5, 0.5]


def test_geographic_wgs84(tmp_path):
    p = _write(tmp_path / "wgs.tif", RGB, WGS84, scale=(0.0001, 0.0001, 0), tiepoint=(0, 0, 0, 77.5, 13.0, 0))
    m = RasterInspector.inspect(p)
    assert m.crs == "EPSG:4326"
    assert m.bounds == pytest.approx([77.5, 12.99, 77.52, 13.0])


def test_model_transformation_matrix(tmp_path):
    matrix = (10.0, 0, 0, 500000.0, 0, -10.0, 0, 4000000.0, 0, 0, 0, 0, 0, 0, 0, 1)
    p = _write(tmp_path / "mt.tif", RGB, UTM14N, matrix=matrix)
    m = RasterInspector.inspect(p)
    assert m.transform == [10.0, 0.0, 500000.0, 0.0, -10.0, 4000000.0]
    assert m.bounds == [500000.0, 3999000.0, 502000.0, 4000000.0]


def test_tiepoint_not_at_origin_and_pixel_is_point(tmp_path):
    keys = _keys((1024, 0, 1, 1), (1025, 0, 1, 2), (3072, 0, 1, 32614))  # RasterPixelIsPoint
    p = _write(tmp_path / "pt.tif", RGB, keys, scale=(2.0, 2.0, 0), tiepoint=(10, 20, 0, 1000.0, 5000.0, 0))
    m = RasterInspector.inspect(p)
    # origin = tiepoint moved back 10 cols / 20 rows, then half a pixel for PixelIsPoint
    assert m.transform[2] == pytest.approx(1000.0 - 10 * 2.0 - 1.0)
    assert m.transform[5] == pytest.approx(5000.0 + 20 * 2.0 + 1.0)


def test_nodata_tag(tmp_path):
    p = _write(tmp_path / "nd.tif", np.zeros((50, 50), np.uint16), UTM14N, scale=(1, 1, 0), tiepoint=(0, 0, 0, 0, 0, 0), nodata=-9999)
    assert RasterInspector.inspect(p).nodata == -9999.0


def test_plain_tiff_and_user_defined_crs_are_not_georeferenced(tmp_path):
    plain = RasterInspector.inspect(_write(tmp_path / "plain.tif", RGB))
    assert not plain.is_georeferenced and plain.crs is None and plain.format == "TIFF"
    user = _keys((1024, 0, 1, 1), (3072, 0, 1, 32767))
    custom = RasterInspector.inspect(_write(tmp_path / "u.tif", RGB, user, scale=(1, 1, 0), tiepoint=(0, 0, 0, 0, 0, 0)))
    assert not custom.is_georeferenced


def test_array_reads_channels_first(tmp_path):
    p = _write(tmp_path / "utm.tif", RGB, UTM14N, scale=(0.5, 0.5, 0), tiepoint=(0, 0, 0, 620000.0, 3350000.0, 0))
    arr, meta = RasterInspector.read_as_array(p)
    assert arr.shape == (3, 100, 200) and meta.is_georeferenced


@pytest.fixture
def utm_meta(tmp_path):
    arr = np.zeros((1024, 1024, 3), np.uint8)
    return RasterInspector.inspect(_write(tmp_path / "big.tif", arr, UTM14N, scale=(0.5, 0.5, 0), tiepoint=(0, 0, 0, 620000.0, 3350000.0, 0)))


def _mask_with_hole():
    mask = np.zeros((1024, 1024), np.uint8)
    mask[100:300, 200:600] = 1
    mask[150:200, 300:350] = 0
    return mask  # 80,000 - 2,500 = 77,500 px


def test_area_statistics_are_metric(utm_meta):
    st = calculate_area_statistics(_mask_with_hole(), utm_meta)
    assert st.estimated_area_sq_m == 77_500 * 0.25
    assert st.metric_crs == "EPSG:32614"


def test_geojson_polygon_is_real_shape_in_wgs84(utm_meta):
    g = mask_to_geojson(_mask_with_hole(), utm_meta)
    assert len(g["features"]) == 1
    f = g["features"][0]
    assert f["properties"]["pixel_count"] == 77_500
    assert f["properties"]["holes"] == 1
    assert f["properties"]["coordinate_space"] == "geographic"
    lon, lat = f["geometry"]["coordinates"][0][0]
    assert -97.8 < lon < -97.7 and 30.2 < lat < 30.3  # UTM 14N 620000E 3350000N is Austin, TX
    to_utm = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32614", always_xy=True).transform
    area = shp_transform(to_utm, shape(f["geometry"])).area
    # vertices on pixel centres trace ~half a pixel inside the boundary; within 1.5% of the pixel area
    assert area == pytest.approx(77_500 * 0.25, rel=0.015)


def test_geojson_stays_in_image_coordinates_without_georeference():
    g = mask_to_geojson(_mask_with_hole(), None)
    f = g["features"][0]
    assert f["properties"]["coordinate_space"] == "image_coordinates"
    xs = [pt[0] for pt in f["geometry"]["coordinates"][0]]
    assert 199 <= min(xs) and max(xs) <= 601


def test_saved_mask_geotiff_round_trips_georeference(tmp_path, utm_meta):
    from backend.app.evidence.masks import save_mask_as_geotiff

    out = save_mask_as_geotiff(_mask_with_hole(), tmp_path / "mask.tif", metadata=utm_meta)
    back = RasterInspector.inspect(out)
    assert back.is_georeferenced
    assert back.crs == utm_meta.crs and back.transform == utm_meta.transform and back.bounds == utm_meta.bounds


def test_joint_stretch_passes_8bit_rgb_through_unchanged():
    from backend.app.geo.optical_preprocessing import joint_rgb8_pair

    a = np.random.default_rng(0).integers(0, 256, (3, 64, 64), dtype=np.uint8)
    b = np.random.default_rng(1).integers(0, 256, (3, 64, 64), dtype=np.uint8)
    r1, r2, note = joint_rgb8_pair(a, b)
    assert note is None and r1.shape == (64, 64, 3)
    assert np.array_equal(r1, np.transpose(a, (1, 2, 0)))


def test_joint_stretch_does_not_invent_change_in_uint16():
    from backend.app.geo.optical_preprocessing import joint_rgb8_pair

    rng = np.random.default_rng(0)
    t1 = rng.integers(200, 3000, (4, 64, 64), dtype=np.uint16)   # 4-band reflectance-like
    t2 = t1.copy()
    t2[:, 20:40, 20:40] = 9000                                   # one genuinely changed patch
    r1, r2, note = joint_rgb8_pair(t1, t2)
    assert note and "joint" in note and r1.dtype == np.uint8
    unchanged = np.ones((64, 64), bool); unchanged[20:40, 20:40] = False
    assert np.array_equal(r1[unchanged], r2[unchanged])          # same stretch for both dates
    assert (r2[~unchanged] != r1[~unchanged]).any()
