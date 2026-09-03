"""
API endpoint tests for SatQuery AI Visual Analytics
"""
import pytest
import httpx
from pathlib import Path
from PIL import Image
import numpy as np
from backend.app.main import app
from backend.app.artifacts.manager import artifact_manager


@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_visual_analytics_api_flow(async_client, tmp_path):
    job_id = "test_vis_job_001"
    dirs = artifact_manager.init_job_workspace(job_id)

    # Save a test 3-band RGB image in input/
    img = Image.new("RGB", (64, 64), (100, 150, 200))
    img_path = dirs["input"] / "test_optical.png"
    img.save(img_path)

    # 1. GET /api/analysis/{job_id}/layers
    res = await async_client.get(f"/api/analysis/{job_id}/layers")
    assert res.status_code == 200
    layers = res.json()
    assert len(layers) >= 2
    layer_ids = [l["layer_id"] for l in layers]
    assert "true_color" in layer_ids

    # 2. GET /api/analysis/{job_id}/visualizations/true_color
    res_img = await async_client.get(f"/api/analysis/{job_id}/visualizations/true_color")
    assert res_img.status_code == 200
    assert res_img.headers["content-type"] == "image/png"

    # 3. POST /api/analysis/{job_id}/inspect-pixel
    res_inspect = await async_client.post(
        f"/api/analysis/{job_id}/inspect-pixel",
        json={"col": 10, "row": 15}
    )
    assert res_inspect.status_code == 200
    inspect_data = res_inspect.json()
    assert inspect_data["pixel"] == {"col": 10, "row": 15}
    assert "band_values" in inspect_data

    # 4. GET /api/analysis/{job_id}/histogram/band_1
    res_hist = await async_client.get(f"/api/analysis/{job_id}/histogram/band_1")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert hist_data["total_pixels"] == 64 * 64
    assert len(hist_data["bins"]) == 50

    # 5. GET /api/analysis/{job_id}/export/true_color?format=png
    res_exp = await async_client.get(f"/api/analysis/{job_id}/export/true_color?format=png")
    assert res_exp.status_code == 200
    assert "attachment" in res_exp.headers.get("content-disposition", "")
