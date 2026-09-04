import pytest
from pathlib import Path
from PIL import Image

from backend.app.video.decoder import VideoDecoder
from backend.app.video.sampler import VideoSampler
from backend.app.schemas.video import VideoSamplingConfig


def test_sampler_coarse_sampling():
    test_video = Path("datasets/samples/video/derived_patrol.mp4")
    with VideoDecoder(test_video) as decoder:
        cfg = VideoSamplingConfig(sample_fps=2.0, max_frames=6)
        samples = VideoSampler.sample_coarse_frames(decoder, config=cfg)
        assert len(samples) <= 6
        assert len(samples) > 0
        for idx, ts, img in samples:
            assert isinstance(idx, int)
            assert isinstance(ts, float)
            assert isinstance(img, Image.Image)


def test_sampler_refinement_window():
    test_video = Path("datasets/samples/video/derived_patrol.mp4")
    with VideoDecoder(test_video) as decoder:
        refined = VideoSampler.sample_refinement_window(
            decoder,
            anchor_indices=[10],
            window_size=2,
            already_sampled_indices={10}
        )
        indices = [r[0] for r in refined]
        # Should contain indices 8, 9, 11, 12 (10 was already sampled)
        assert 10 not in indices
        assert 8 in indices or 9 in indices or 11 in indices or 12 in indices
