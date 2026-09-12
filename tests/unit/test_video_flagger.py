import pytest
from pathlib import Path
import numpy as np
from PIL import Image

from backend.app.video.flagger import VideoFlagger, FrameDetection
from backend.app.config import VideoEventScoringSettings
from backend.app.schemas.video import VideoFlagConfig


def test_scoring_weights_validation():
    # Valid weights (sum = 1.0)
    cfg = VideoEventScoringSettings(
        detector_weight=0.4,
        reasoning_weight=0.3,
        segmentation_weight=0.2,
        persistence_weight=0.1
    )
    cfg.validate_weights()

    # Invalid weights
    bad_cfg = VideoEventScoringSettings(
        detector_weight=0.5,
        reasoning_weight=0.5,
        segmentation_weight=0.2,
        persistence_weight=0.1
    )
    with pytest.raises(ValueError, match="must sum to 1.0"):
        bad_cfg.validate_weights()


def test_compute_event_score_is_heuristic():
    score = VideoFlagger.compute_event_score(
        detector_score=0.8,
        reasoning_score=0.9,
        segmentation_score=0.7,
        persistence_seconds=1.5
    )
    assert 0.0 <= score <= 1.0
    # Transparent score: 0.4*0.8 + 0.3*0.9 + 0.2*0.7 + 0.1*(1.5/2.0) = 0.32 + 0.27 + 0.14 + 0.075 = 0.805
    assert abs(score - 0.805) < 0.01


def test_flagger_clustering_and_transient_filtering(tmp_path):
    img = Image.new("RGB", (100, 100), color="blue")
    box = [0.1, 0.1, 0.4, 0.4]

    # Cluster 1: 3 consecutive frames -> persists -> flagged
    # Cluster 2: 1 single frame at frame 100 -> transient -> dropped
    dets = [
        FrameDetection(frame_index=10, timestamp_sec=1.0, box_2d=box, label="car", detector_score=0.8, reasoning_score=0.9, image=img),
        FrameDetection(frame_index=11, timestamp_sec=1.1, box_2d=box, label="car", detector_score=0.85, reasoning_score=0.95, image=img),
        FrameDetection(frame_index=12, timestamp_sec=1.2, box_2d=box, label="car", detector_score=0.82, reasoning_score=0.9, image=img),
        FrameDetection(frame_index=100, timestamp_sec=10.0, box_2d=box, label="car", detector_score=0.7, reasoning_score=0.7, image=img)
    ]

    cfg = VideoFlagConfig(min_persistence_frames=2, min_persistence_seconds=0.15, max_gap_frames=2)
    flags = VideoFlagger.generate_flags(
        detections=dets,
        job_id="test_job",
        video_id="test_vid",
        artifacts_video_dir=tmp_path,
        config=cfg
    )

    # Exactly 1 persistent flag should be created; the transient detection at frame 100 must be dropped
    assert len(flags) == 1
    flag = flags[0]
    assert flag.start_frame == 10
    assert flag.end_frame == 12
    assert flag.start_timestamp == 1.0
    assert flag.end_timestamp == 1.2
    assert flag.label == "car"
    assert flag.event_score > 0.0
    assert flag.metadata["event_score_type"] == "heuristic_ranking_score"
    assert flag.metadata["calibrated_model_probability"] is False


def test_annotated_overlay_preserves_true_colour():
    """Pixels outside the mask must keep their original colour.

    flagger.py passed a numpy array to create_change_overlay, which routes arrays
    through render_display_rgb -- a 2-98 percentile contrast stretch intended for
    multi-band satellite rasters. On ordinary video that recolours the whole frame:
    a red car rendered green, which is actively misleading for colour queries.
    (project/pre-demo.md 3f)
    """
    import numpy as np
    from PIL import Image
    from backend.app.geo.rendering import create_change_overlay

    # A red car on grey asphalt, in miniature.
    base = np.full((40, 40, 3), 90, dtype=np.uint8)
    base[5:15, 5:15] = (200, 30, 30)
    base_pil = Image.fromarray(base)

    mask = np.zeros((40, 40), dtype=np.uint8)
    mask[30:35, 30:35] = 1          # mask somewhere else entirely

    out = np.array(create_change_overlay(base_pil, mask, color_rgb=(0, 230, 150), alpha=0.45).convert("RGB"))

    car = out[5:15, 5:15].reshape(-1, 3).mean(axis=0)
    assert car[0] > car[1] and car[0] > car[2], f"car is no longer red: RGB={car}"
    assert abs(float(car[0]) - 200) < 25, f"red channel shifted too far: {car[0]}"
