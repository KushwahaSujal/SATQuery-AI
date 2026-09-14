"""HTTP flow for GeoTIFF + GeoJSON AOI input: upload, AOI upload, analyze with file or inline AOI (Q-011)."""
import json
import uuid
from pathlib import Path

import numpy as np
import pyproj
import pytest
import tifffile
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app

ROOT = Path(__file__).resolve().parents[2]
SCENES = ROOT / "datasets/raw/ayushman_levircd_1024"
GEOKEYS = (1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, 32614)
TO_WGS = pyproj.Transformer.from_crs("EPSG:32614", "EPSG:4326", always_xy=True).transform
WEST_HALF = {"type": "Polygon", "coordinates": [[list(TO_WGS(x, y)) for x, y in
             [(620000, 3350000), (620256, 3350000), (620256, 3349488), (620000, 3349488), (620000, 3350000)]]]}


def _geotiff(path, arr):
    tifffile.imwrite(path, arr, photometric="rgb", extratags=[
        (33550, "d", 3, (0.5, 0.5, 0.0), False),
        (33922, "d", 6, (0, 0, 0, 620000.0, 3350000.0, 0), False),
        (34735, "H", len(GEOKEYS), GEOKEYS, False),
    ])
    return path


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_geotiff_upload_reports_crs_and_aoi_upload_validates(client, tmp_path):
    rid = str(uuid.uuid4())
    p = _geotiff(tmp_path / "scene.tif", np.zeros((1024, 1024, 3), np.uint8))
    up = client.post("/api/upload", files=[("files", ("scene.tif", p.open("rb"), "image/tiff"))], data={"request_id": rid})
    assert up.status_code == 200
    meta = up.json()["metadata"][0]
    assert meta["crs"] == "EPSG:32614" and meta["format"] == "GeoTIFF"

    ok = client.post("/api/upload/aoi", files={"file": ("west.geojson", json.dumps(WEST_HALF), "application/geo+json")}, data={"request_id": rid})
    assert ok.status_code == 200
    assert ok.json()["aoi_filename"] == "west.geojson" and ok.json()["crs"] == "EPSG:4326"

    bad = client.post("/api/upload/aoi", files={"file": ("bad.geojson", json.dumps({"type": "Point", "coordinates": [0, 0]}), "application/geo+json")}, data={"request_id": rid})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "AOI_INVALID"

    wrong_ext = client.post("/api/upload/aoi", files={"file": ("aoi.kml", "<kml/>", "text/xml")}, data={"request_id": rid})
    assert wrong_ext.status_code == 415


def test_analyze_restricts_change_to_aoi(client, tmp_path):
    if not (SCENES / "test_100_label.png").is_file():
        pytest.skip("LEVIR-CD 1024 scenes not available")
    rid = str(uuid.uuid4())
    files = []
    for tag in ("A", "B"):
        arr = np.array(Image.open(SCENES / f"test_100_{tag}.png").convert("RGB"))
        files.append(("files", (f"s_{tag}.tif", _geotiff(tmp_path / f"s_{tag}.tif", arr).open("rb"), "image/tiff")))
    assert client.post("/api/upload", files=files, data={"request_id": rid}).status_code == 200
    client.post("/api/upload/aoi", files={"file": ("west.geojson", json.dumps(WEST_HALF), "application/geo+json")}, data={"request_id": rid})

    body = {"query": "detect changes between these two images and calculate the changed area",
            "image_filenames": ["s_A.tif", "s_B.tif"], "request_id": rid}
    by_file = client.post("/api/analyze", json={**body, "aoi_filename": "west.geojson"}).json()
    inline = client.post("/api/analyze", json={**body, "aoi_geojson": WEST_HALF}).json()

    for res in (by_file, inline):
        assert res["status"] == "COMPLETED", res.get("errors")
        stats = res["evidence"]["spatial"]["statistics"]
        assert stats["total_valid_pixels"] == 512 * 1024        # the AOI, not the scene
        assert stats["estimated_area_sq_m"] == stats["changed_pixels"] * 0.25
        assert stats["metric_crs"] == "EPSG:32614"
        assert res["evidence"]["metadata"]["aoi"]["aoi_area_sq_m"] == pytest.approx(256 * 512, rel=1e-6)
    assert by_file["evidence"]["spatial"]["statistics"]["changed_pixels"] == inline["evidence"]["spatial"]["statistics"]["changed_pixels"]


def test_aoi_on_plain_image_fails_with_structured_code(client):
    if not (SCENES / "test_100_A.png").is_file():
        pytest.skip("LEVIR-CD 1024 scenes not available")
    rid = str(uuid.uuid4())
    files = [("files", (f"p_{t}.png", (SCENES / f"test_100_{t}.png").open("rb"), "image/png")) for t in ("A", "B")]
    assert client.post("/api/upload", files=files, data={"request_id": rid}).status_code == 200
    res = client.post("/api/analyze", json={"query": "detect changes", "image_filenames": ["p_A.png", "p_B.png"],
                                           "request_id": rid, "aoi_geojson": WEST_HALF}).json()
    assert res["status"] == "FAILED"
    assert any("georeferenced raster" in e for e in res["errors"])
    assert any("AOI_REQUIRES_GEOREFERENCED_RASTER" in s["step"] for s in res["execution_trace"])
