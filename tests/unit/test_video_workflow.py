import pytest
from pathlib import Path

from backend.app.workflows.video_analysis import VideoAnalysisWorkflow
from backend.app.schemas.agent import TaskType, JobStatus
from backend.app.schemas.video import VideoSamplingConfig, VideoFlagConfig


def test_route_video_query():
    # Grounding query
    task, reason = VideoAnalysisWorkflow.route_video_query("Highlight every red vehicle on the road")
    assert task == TaskType.VIDEO_GROUNDING

    # Tracking query
    task, reason = VideoAnalysisWorkflow.route_video_query("Track the moving vessel near the shoreline")
    assert task == TaskType.VIDEO_GROUNDING_TRACKING

    # VQA query
    task, reason = VideoAnalysisWorkflow.route_video_query("Describe what is happening across this scene")
    assert task == TaskType.VIDEO_VQA

    # Change query
    task, reason = VideoAnalysisWorkflow.route_video_query("Detect temporal scene change in the area")
    assert task == TaskType.VIDEO_CHANGE


@pytest.mark.asyncio
async def test_video_workflow_no_events_found():
    test_video = Path("datasets/samples/video/derived_patrol.mp4")
    # Search for an impossible object that does not exist in the satellite patrol fixture
    resp = await VideoAnalysisWorkflow.execute(
        video_path=test_video,
        query="Highlight the purple flying saucer in the sky",
        job_id="test_neg_job",
        sampling_config=VideoSamplingConfig(sample_fps=1.0, max_frames=3),
        flagging_config=VideoFlagConfig(min_event_score=0.5)
    )

    assert resp.status == JobStatus.COMPLETED
    assert len(resp.flags) == 0
    assert "NO_RELEVANT_EVENTS_FOUND" in resp.workflow_reason
