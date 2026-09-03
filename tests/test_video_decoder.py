import pytest
from pathlib import Path
from PIL import Image

from backend.app.video.decoder import VideoDecoder, VideoDecodeError
from backend.app.exceptions import InvalidInputError, UnsupportedFormatError


def test_decoder_nonexistent_file(tmp_path):
    with pytest.raises(InvalidInputError, match="Video file not found"):
        VideoDecoder(tmp_path / "nonexistent.mp4").open()


def test_decoder_unsupported_format(tmp_path):
    dummy_txt = tmp_path / "video.txt"
    dummy_txt.write_text("not a video")
    with pytest.raises(UnsupportedFormatError, match="Unsupported video format"):
        VideoDecoder(dummy_txt).open()


def test_decoder_metadata_and_frame_access():
    test_video = Path("datasets/samples/video/derived_patrol.mp4")
    assert test_video.exists(), "Derived test video fixture missing"

    with VideoDecoder(test_video) as decoder:
        meta = decoder.metadata
        assert meta.filename == "derived_patrol.mp4"
        assert meta.duration_sec > 0
        assert meta.fps > 0
        assert meta.width > 0
        assert meta.height > 0
        assert meta.frame_count > 0

        # Frame index seeking
        ts, img = decoder.get_frame_at_index(0)
        assert isinstance(img, Image.Image)
        assert ts == 0.0
        assert img.size == (meta.width, meta.height)

        # Timestamp seeking
        mid_time = meta.duration_sec / 2.0
        idx, mid_img = decoder.get_frame_at_timestamp(mid_time)
        assert isinstance(mid_img, Image.Image)
        assert idx > 0


def test_decoder_streaming_iterator():
    test_video = Path("datasets/samples/video/derived_patrol.mp4")
    with VideoDecoder(test_video) as decoder:
        frames = list(decoder.iter_frames(stride=5, max_frames=4))
        assert len(frames) == 4
        # First frame should be index 0
        assert frames[0][0] == 0
        # Second frame should be index 5
        assert frames[1][0] == 5
        assert isinstance(frames[0][2], Image.Image)
