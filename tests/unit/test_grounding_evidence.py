import numpy as np
from backend.app.geo.metadata import RasterMetadata
from backend.app.evidence.fusion import EvidenceFusionEngine
from backend.app.evidence.boxes import normalize_box
from backend.app.geo.vectors import mask_to_geojson


def test_georeferenced_grounding_evidence():
    """
    Verifies that for georeferenced imagery:
    1. image-space bounding boxes are transformed to map coordinates in EPSG:4326;
    2. segmentation masks are transformed to geospatial polygons in EPSG:4326;
    3. GeoJSON is produced in EPSG:4326;
    4. source CRS metadata is preserved;
    5. pixel coordinates are never assumed to be geographic coordinates.
    """
    # Create metadata simulating a UTM GeoTIFF (EPSG:32618)
    meta = RasterMetadata(
        filepath="sample_utm.tif",
        filename="sample_utm.tif",
        format="GTiff",
        dtype="uint8",
        width=256,
        height=256,
        bands=3,
        crs="EPSG:32618",
        transform=[10.0, 0.0, 500000.0, 0.0, -10.0, 4500000.0],
        bounds=[500000.0, 4497440.0, 502560.0, 4500000.0],
        resolution=[10.0, 10.0],
        is_georeferenced=True
    )

    box = [50.0, 60.0, 120.0, 140.0]  # Pixel coords [x1, y1, x2, y2]
    mask = np.zeros((256, 256), dtype=np.uint8)
    mask[60:140, 50:120] = 1

    evidence = EvidenceFusionEngine.build_grounding_evidence(
        selected_box=box,
        segmentation_mask=mask,
        metadata=meta,
        request_id="test_geo_req",
        target_category="vehicle",
        grounding_score=0.88,
        sam2_score=0.92,
        summary="A small vehicle was detected and segmented."
    )

    # 1. Bounding Box verification
    assert len(evidence.spatial.boxes) == 1
    b_ev = evidence.spatial.boxes[0]
    assert b_ev.coordinate_space == "geographic"
    assert b_ev.source_crs == "EPSG:32618"
    assert b_ev.target_crs == "EPSG:4326"
    assert b_ev.geo_bounds is not None
    assert len(b_ev.geo_bounds) == 4

    min_lon, min_lat, max_lon, max_lat = b_ev.geo_bounds
    # Check that coordinates are valid lon/lat within standard WGS84 range
    assert -180.0 <= min_lon <= 180.0
    assert -90.0 <= min_lat <= 90.0
    assert min_lon < max_lon
    assert min_lat < max_lat
    # Explicitly verify coordinates are not pixel values
    assert not (0.0 <= min_lon <= 256.0 and 0.0 <= max_lat <= 256.0 and min_lon > 10.0)

    # 2. Polygon and GeoJSON verification
    gj = evidence.spatial.geojson_data
    assert gj is not None
    assert gj["type"] == "FeatureCollection"
    assert "OGC:1.3:CRS84" in gj["crs"]["properties"]["name"]
    assert gj["crs"]["properties"]["source_crs"] == "EPSG:32618"
    assert gj["crs"]["properties"]["target_crs"] == "EPSG:4326"

    assert len(gj["features"]) > 0
    f = gj["features"][0]
    assert f["properties"]["coordinate_space"] == "geographic"
    assert f["properties"]["source_crs"] == "EPSG:32618"
    assert f["properties"]["target_crs"] == "EPSG:4326"

    poly_coords = f["geometry"]["coordinates"][0]
    for pt in poly_coords:
        lon, lat = pt[0], pt[1]
        assert -180.0 <= lon <= 180.0
        assert -90.0 <= lat <= 90.0

    # 3. Overall evidence metadata
    assert evidence.metadata["is_georeferenced"] is True
    assert evidence.metadata["source_crs"] == "EPSG:32618"
    assert evidence.metadata["target_crs"] == "EPSG:4326"
    assert evidence.metadata["coordinate_space"] == "geographic"


def test_non_georeferenced_grounding_evidence():
    """
    Verifies that for non-georeferenced benchmark PNG/JPEG:
    1. evidence is strictly kept in image pixel coordinates;
    2. geo_bounds is None;
    3. coordinate_space is 'image_coordinates';
    4. pixel coordinates are never assumed to be geographic coordinates.
    """
    meta = RasterMetadata(
        filepath="sample_benchmark.png",
        filename="sample_benchmark.png",
        format="PNG",
        dtype="uint8",
        width=256,
        height=256,
        bands=3,
        crs=None,
        transform=None,
        bounds=None,
        resolution=None,
        is_georeferenced=False
    )

    box = [40.0, 50.0, 100.0, 110.0]
    mask = np.zeros((256, 256), dtype=np.uint8)
    mask[50:110, 40:100] = 1

    evidence = EvidenceFusionEngine.build_grounding_evidence(
        selected_box=box,
        segmentation_mask=mask,
        metadata=meta,
        request_id="test_nong_req",
        target_category="aircraft",
        grounding_score=0.75,
        sam2_score=0.85,
        summary="An aircraft was grounded in the benchmark image."
    )

    # 1. Bounding Box verification
    assert len(evidence.spatial.boxes) == 1
    b_ev = evidence.spatial.boxes[0]
    assert b_ev.coordinate_space == "image_coordinates"
    assert b_ev.geo_bounds is None  # Never assume pixel coords are geographic
    assert b_ev.source_crs is None
    assert b_ev.target_crs is None
    # Relative normalized 2D box [ymin, xmin, ymax, xmax]
    assert b_ev.box_2d == [round(50.0 / 256.0, 4), round(40.0 / 256.0, 4), round(110.0 / 256.0, 4), round(100.0 / 256.0, 4)]

    # 2. Polygon and GeoJSON verification
    gj = evidence.spatial.geojson_data
    assert gj is not None
    assert gj["type"] == "FeatureCollection"
    assert gj["crs"]["properties"]["name"] == "image_coordinates"
    assert gj["crs"]["properties"]["source_crs"] is None

    assert len(gj["features"]) > 0
    f = gj["features"][0]
    assert f["properties"]["coordinate_space"] == "image_coordinates"
    assert f["properties"]["source_crs"] is None

    poly_coords = f["geometry"]["coordinates"][0]
    for pt in poly_coords:
        x, y = pt[0], pt[1]
        assert 0.0 <= x <= 256.0
        assert 0.0 <= y <= 256.0

    # 3. Overall evidence metadata
    assert evidence.metadata["is_georeferenced"] is False
    assert evidence.metadata["source_crs"] is None
    assert evidence.metadata["coordinate_space"] == "image_coordinates"
