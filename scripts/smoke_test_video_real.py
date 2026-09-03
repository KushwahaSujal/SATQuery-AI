"""
SatQuery AI — Real Footage Smoke Test (REAL_FOOTAGE)
Validates the end-to-end video analysis and moment-flagging pipeline using authentic real video footage.
Provenance: REAL_FOOTAGE (Authentic roadway vehicle surveillance footage).
"""
import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.video.decoder import VideoDecoder
from backend.app.schemas.video import VideoSamplingConfig, VideoFlagConfig
from backend.app.workflows.video_analysis import VideoAnalysisWorkflow
from backend.app.schemas.agent import JobStatus
from backend.app.logging import logger


async def run_real_video_smoke_test():
    print("\n" + "=" * 70)
    print("SATQUERY AI — REAL FOOTAGE SMOKE TEST")
    print("PROVENANCE: REAL_FOOTAGE (Authentic traffic surveillance footage)")
    print("=" * 70)

    video_path = root_dir / "datasets" / "samples" / "video" / "real_aerial_footage.mp4"
    if not video_path.exists():
        print(f"ERROR: Real video fixture not found at {video_path}")
        sys.exit(1)

    print(f"\n[STEP 1] Inspecting authentic video metadata for: {video_path.name}")
    with VideoDecoder(video_path) as decoder:
        meta = decoder.metadata
        print(f"  Filename:   {meta.filename}")
        print(f"  Resolution: {meta.width}x{meta.height}")
        print(f"  FPS:        {meta.fps:.2f}")
        print(f"  Frames:     {meta.frame_count}")
        print(f"  Duration:   {meta.duration_sec:.2f}s")
        print(f"  Codec:      {meta.codec}")

    query = "Flag every moment where a car is present on the road"
    print(f"\n[STEP 2] Executing VideoAnalysisWorkflow with query: '{query}'")

    # Sample at 0.5 FPS up to 3 frames for fast CPU execution
    sampling_cfg = VideoSamplingConfig(
        sample_fps=0.5,
        max_frames=3,
        analysis_stride=1
    )
    flagging_cfg = VideoFlagConfig(
        min_persistence_frames=1,
        min_persistence_seconds=0.5,
        min_event_score=0.20
    )

    response = await VideoAnalysisWorkflow.execute(
        video_path=video_path,
        query=query,
        job_id="smoke_real_001",
        sampling_config=sampling_cfg,
        flagging_config=flagging_cfg
    )

    print(f"\n[STEP 3] Workflow Result:")
    print(f"  Status:          {response.status.value}")
    print(f"  Task:            {response.task.value}")
    print(f"  Workflow Reason: {response.workflow_reason}")
    print(f"  Models Used:     {response.models_used}")
    print(f"  Flags Generated: {len(response.flags)}")

    for i, flag in enumerate(response.flags, 1):
        print(f"\n  --- Flag #{i} [{flag.flag_id}] ---")
        print(f"  Time Window:  {flag.start_timestamp:.2f}s -> {flag.end_timestamp:.2f}s (Peak Frame: {flag.peak_frame})")
        print(f"  Label:        {flag.label}")
        print(f"  Event Score:  {flag.event_score} (Heuristic ranking score; not model confidence)")
        print(f"  Model Scores: {flag.model_scores}")
        print(f"  Keyframe URL: {flag.keyframe_url}")
        print(f"  Overlay URL:  {flag.overlay_url}")
        print(f"  Mask URL:     {flag.mask_url}")

    assert response.status == JobStatus.COMPLETED, f"Expected COMPLETED but got {response.status}"
    print("\n" + "=" * 70)
    print("REAL FOOTAGE SMOKE TEST: PASSED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_real_video_smoke_test())
