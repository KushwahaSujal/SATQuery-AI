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
    # An object that is genuinely not in the fixture. Grounding DINO still proposes a
    # region for it at 0.558-0.563 confidence -- which PASSES the 0.35 floor. What
    # rejects it is max_box_area_ratio: the proposed box covers 99.9% of the frame on
    # every sampled frame, and a box that size is not an object detection.
    # This was xfail until that gate landed. (project/pre-demo.md 2.1a, 3g)
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


@pytest.mark.asyncio
async def test_video_workflow_finds_detections_when_target_is_present():
    """Positive path: a target that IS in the footage must produce detections.

    Regression guard for the field-access bug where video_analysis.py read
    `gd_res.metadata["boxes"]` — a key the Grounding DINO adapter never sets,
    since GroundingResult exposes `boxes` as a top-level field. Every frame
    therefore yielded zero candidates and the video pipeline could never flag
    anything, while reporting the misleading NO_RELEVANT_EVENTS_FOUND.
    """
    test_video = Path("datasets/samples/video/real_aerial_footage.mp4")
    resp = await VideoAnalysisWorkflow.execute(
        video_path=test_video,
        query="find all vehicles",
        job_id="test_pos_job",
        # Cover the first ~12s: the earliest real vehicle is at 4.8-8.2s. Sampling
        # only the first 4s caught nothing but low-confidence artefacts.
        sampling_config=VideoSamplingConfig(sample_fps=2.0, max_frames=24),
        flagging_config=VideoFlagConfig(min_event_score=0.1, min_persistence_frames=1),
    )

    assert resp.status == JobStatus.COMPLETED
    detection_steps = [
        s for s in resp.execution_trace
        if "Candidate detections found" in s.step
    ]
    assert detection_steps, "workflow never reported a detection count"
    assert "on 0 sampled frames" not in detection_steps[0].step, (
        "Grounding DINO returns boxes for this footage, so the workflow must see them; "
        f"got: {detection_steps[0].step}"
    )


@pytest.mark.asyncio
async def test_video_workflow_reports_frame_failures_distinctly(monkeypatch):
    """A frame that errors must not be reported as 'target absent'.

    Every per-frame exception was swallowed into a log warning, so the trace said
    'Candidate detections found on 0 sampled frames' and the result read
    NO_RELEVANT_EVENTS_FOUND -- indistinguishable from the target genuinely not
    being there. A CUDA OOM on a busy demo GPU therefore looks like a clean
    negative result. (project/pre-demo.md 2.1b)
    """
    from backend.app.ml.registry import model_registry

    gd = model_registry.get_adapter("grounding_dino")
    monkeypatch.setattr(
        gd, "predict",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("CUDA out of memory")),
    )

    resp = await VideoAnalysisWorkflow.execute(
        video_path=Path("datasets/samples/video/real_aerial_footage.mp4"),
        query="find all vehicles",
        job_id="test_frame_fail_job",
        sampling_config=VideoSamplingConfig(sample_fps=1.0, max_frames=3),
        flagging_config=VideoFlagConfig(min_event_score=0.1, min_persistence_frames=1),
    )

    assert "NO_RELEVANT_EVENTS_FOUND" not in (resp.workflow_reason or ""), (
        "all frames errored, so this is a detection failure, not an absent target; "
        f"got: {resp.workflow_reason}"
    )
    assert "DETECTION_FAILED" in (resp.workflow_reason or "")
    trace_text = " ".join(f"{s.step} {s.details or ''}" for s in resp.execution_trace)
    assert "3 frame(s) failed" in trace_text, f"failures absent from trace: {trace_text}"


@pytest.mark.asyncio
async def test_video_flag_mask_is_not_empty():
    """SAM 2.1 must produce actual mask pixels, not an all-zero PNG.

    SAM2VideoPredictor indexes its frame directory positionally (0..N-1), but the
    workflow passed the original video frame number as prompt_frame_idx. With 6
    sampled frames and an anchor at frame 60 that raised "index N is out of bounds",
    was caught, and fell back to per-image prediction -- which also returned nothing.
    Flags therefore carried a bounding box and an overlay but a blank mask.
    (project/pre-demo.md 2.1c)
    """
    import numpy as np
    from PIL import Image

    resp = await VideoAnalysisWorkflow.execute(
        video_path=Path("datasets/samples/video/real_aerial_footage.mp4"),
        query="find all vehicles",
        job_id="test_mask_job",
        # As above: reach the real vehicle rather than the first few empty seconds.
        sampling_config=VideoSamplingConfig(sample_fps=2.0, max_frames=24),
        flagging_config=VideoFlagConfig(min_event_score=0.1, min_persistence_frames=1),
    )

    assert resp.flags, "expected at least one flag on footage containing vehicles"
    flag = resp.flags[0]
    assert flag.mask_url, "flag carries no mask artifact"

    mask_path = Path("results") / "test_mask_job" / "video" / Path(flag.mask_url).name
    assert mask_path.is_file(), f"mask file missing: {mask_path}"
    frac = float((np.array(Image.open(mask_path)) > 0).mean())
    # The per-image fallback yielded ~9 pixels out of 331,776 (frac 2.7e-05), which a
    # ">0" check passes trivially. A real vehicle box here covers roughly 6% of the
    # frame, so require at least 0.1% before calling the mask usable.
    assert frac > 0.001, f"segmentation mask is effectively empty (nonzero fraction {frac:.2e})"


@pytest.mark.asyncio
async def test_absent_colour_reports_not_applicable():
    """A colour that is not in the footage must be reported as NOT_APPLICABLE.

    Grounding DINO is open-vocabulary: it returns a best-matching region for any
    prompt, and its confidence does not separate present from absent (measured
    0.83-0.92 for red, white, yellow, blue and green alike). Photometric colour
    consistency does separate them: present 0.97-1.00, absent 0.21-0.26.
    (project/pre-demo.md 2.1a)
    """
    resp = await VideoAnalysisWorkflow.execute(
        video_path=Path("datasets/samples/video/real_aerial_footage.mp4"),
        query="spot a yellow car",
        job_id="test_absent_colour",
        sampling_config=VideoSamplingConfig(sample_fps=1.0, max_frames=8),
        flagging_config=VideoFlagConfig(min_event_score=0.1, min_persistence_frames=1),
    )

    assert resp.status == JobStatus.COMPLETED
    assert not resp.flags, f"there is no yellow car in this clip; got {len(resp.flags)} flag(s)"
    assert "NOT_APPLICABLE" in (resp.workflow_reason or ""), resp.workflow_reason
    assert "yellow" in (resp.workflow_reason or "").lower()


@pytest.mark.asyncio
async def test_present_colour_still_detected():
    """Regression guard: the colour gate must not reject a colour that IS present."""
    resp = await VideoAnalysisWorkflow.execute(
        video_path=Path("datasets/samples/video/real_aerial_footage.mp4"),
        query="spot a red car",
        job_id="test_present_colour",
        sampling_config=VideoSamplingConfig(sample_fps=1.0, max_frames=32),
        flagging_config=VideoFlagConfig(min_event_score=0.1, min_persistence_frames=1),
    )
    assert resp.flags, "the clip contains a red car at ~17.4s"
    assert "NOT_APPLICABLE" not in (resp.workflow_reason or "")
