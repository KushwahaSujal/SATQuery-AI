"""Re-prompting a video job reuses its footage (Q-064).

POST /jobs/{id}/reuse-source only copied input/, which a video job leaves empty (its footage is in
video/), so every follow-up on a video answered "Job ... has no source imagery to reuse."
"""
import shutil

import httpx
import pytest

from backend.app.artifacts.manager import artifact_manager
from backend.app.main import app


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_video_job_follow_up_gets_its_footage(client):
    job_id = "test_reuse_video_job"
    dirs = artifact_manager.init_job_workspace(job_id)
    (dirs["root"] / "video").mkdir(exist_ok=True)
    (dirs["root"] / "video" / "clip.mp4").write_bytes(b"not really a video")
    try:
        res = await client.post(f"/api/jobs/{job_id}/reuse-source")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["kind"] == "video" and body["video_filename"] == "clip.mp4"
        assert body["image_filenames"] == []
        new_dir = artifact_manager.get_job_dir(body["request_id"])
        assert (new_dir / "video" / "clip.mp4").read_bytes() == b"not really a video"
        shutil.rmtree(new_dir, ignore_errors=True)
    finally:
        shutil.rmtree(dirs["root"], ignore_errors=True)


@pytest.mark.asyncio
async def test_image_job_follow_up_is_unchanged(client):
    job_id = "test_reuse_image_job"
    dirs = artifact_manager.init_job_workspace(job_id)
    (dirs["input"] / "a.png").write_bytes(b"png")
    try:
        body = (await client.post(f"/api/jobs/{job_id}/reuse-source")).json()
        assert body["image_filenames"] == ["a.png"] and body.get("kind", "image") == "image"
        shutil.rmtree(artifact_manager.get_job_dir(body["request_id"]), ignore_errors=True)
    finally:
        shutil.rmtree(dirs["root"], ignore_errors=True)
