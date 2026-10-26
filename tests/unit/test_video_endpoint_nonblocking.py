"""A running video analysis must not freeze the server (Q-064).

VideoAnalysisWorkflow.execute ran its GPU work inline on the event loop, so for the ~2 minutes a video
job took, every other request -- including the progress poll the UI drives its step list from -- hung.
The UI sat on "Planning the workflow" until the job finished (measured: one poll blocked 0.4 s -> 88 s).
"""
import asyncio
import shutil
import time

import httpx
import pytest

from backend.app.api.v1.endpoints import video as video_ep
from backend.app.artifacts.manager import artifact_manager
from backend.app.main import app
from backend.app.schemas.agent import JobStatus


@pytest.mark.asyncio
async def test_progress_is_served_while_a_video_job_runs(monkeypatch):
    job_id = "test_nonblocking_video_job"
    dirs = artifact_manager.init_job_workspace(job_id)
    (dirs["root"] / "video").mkdir(exist_ok=True)
    (dirs["root"] / "video" / "clip.mp4").write_bytes(b"x")
    artifact_manager.save_progress_json(job_id, {"job_id": job_id, "status": "RUNNING"})

    async def slow_execute(**kwargs):
        time.sleep(3.0)                       # synchronous, like GPU inference
        return video_ep.VideoAnalysisResponse.model_construct(
            job_id=job_id, status=JobStatus.FAILED, flags=[], execution_trace=[], warnings=[])

    monkeypatch.setattr(video_ep.VideoAnalysisWorkflow, "execute", staticmethod(slow_execute))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                     timeout=30) as c:
            # Timed from the moment the job starts: a blocked loop delays the sleep below too.
            t = time.perf_counter()
            run = asyncio.create_task(c.post("/api/video/analyze",
                                             data={"query": "find cars", "request_id": job_id}))
            await asyncio.sleep(0.3)
            res = await c.get(f"/api/jobs/{job_id}/progress")
            waited = time.perf_counter() - t
            await run
        assert res.status_code == 200
        assert waited < 1.5, f"progress poll waited {waited:.1f}s behind the video job"
    finally:
        shutil.rmtree(dirs["root"], ignore_errors=True)
