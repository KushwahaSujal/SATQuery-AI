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
