import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from backend.app.main import app


@pytest.mark.asyncio
async def test_video_upload_endpoint():
    test_video = Path("datasets/samples/video/derived_patrol.mp4")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with open(test_video, "rb") as f:
            resp = await ac.post(
                "/api/video/upload",
                files={"file": ("derived_patrol.mp4", f, "video/mp4")}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["filename"] == "derived_patrol.mp4"
        assert "video_metadata" in data
        assert data["video_metadata"]["duration_sec"] > 0
        assert "video_url" in data


@pytest.mark.asyncio
async def test_video_upload_invalid_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/video/upload",
            files={"file": ("test.txt", b"plain text data", "text/plain")}
        )
        assert resp.status_code == 415


@pytest.mark.asyncio
async def test_video_stream_endpoint():
    test_video = Path("datasets/samples/video/derived_patrol.mp4")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # First upload to get job_id
        with open(test_video, "rb") as f:
            up_resp = await ac.post(
                "/api/video/upload",
                files={"file": ("derived_patrol.mp4", f, "video/mp4")}
            )
        job_id = up_resp.json()["job_id"]

        # Stream endpoint
        stream_resp = await ac.get(f"/api/video/{job_id}/stream")
        assert stream_resp.status_code in (200, 206)
        assert stream_resp.headers.get("content-type") == "video/mp4"
