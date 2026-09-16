"""Q-021: GET /api/video/{id} is served from result.json when the database has no record."""
import shutil

import pytest
from fastapi.testclient import TestClient

from backend.app.artifacts.manager import artifact_manager
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_video_job_without_db_record_is_served_from_result_json(client):
    job = "q020-video-fallback"
    artifact_manager.save_result_json(job, {
        "job_id": job, "status": "COMPLETED", "task": "video_grounding",
        "workflow_id": "workflow_video_analysis", "workflow_reason": "Detected and flagged 1 important moment(s).",
        "video_metadata": {"filename": "x.mp4", "duration_sec": 30.16, "fps": 25.0, "width": 768, "height": 432,
                           "frame_count": 754, "codec": "h264"},
        "flags": [{"flag_id": "flag_1", "start_timestamp": 15.36, "end_timestamp": 18.72, "start_frame": 192,
                   "end_frame": 234, "peak_frame": 228, "label": "red car", "reason": "test", "event_score": 0.89,
                   "metadata": {"track": [{"t": 15.36, "frame": 192, "box_2d": [0.1, 0.2, 0.3, 0.4], "rgb": [120, 39, 53]}]}}],
        "models_used": ["grounding_dino", "sam2"], "execution_trace": [], "warnings": [], "errors": [], "artifacts": {},
    })
    try:
        r = client.get(f"/api/video/{job}")
        assert r.status_code == 200
        body = r.json()
        assert body["flags"][0]["end_timestamp"] == 18.72
        assert body["flags"][0]["metadata"]["track"][0]["rgb"] == [120, 39, 53]
    finally:
        shutil.rmtree(artifact_manager.get_job_dir(job), ignore_errors=True)


def test_unknown_video_job_is_still_404(client):
    assert client.get("/api/video/q020-no-such-video").status_code == 404
