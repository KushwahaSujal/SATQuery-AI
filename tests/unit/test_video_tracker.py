"""Q-019: per-event object track for the video player, and keyframe outlines that keep the object's colour."""
from pathlib import Path

import numpy as np
from PIL import Image

from backend.app.schemas.video import VideoMetadata
from backend.app.video.flagger import draw_mask_outline
from backend.app.video.tracker import _box_from_mask, track_event


class FakeDecoder:
    """25 fps, 100 frames of 100x200 grey video with a red 20x20 square moving 1 px per frame to the right."""

    def __init__(self):
        self.metadata = VideoMetadata(filename="x.mp4", duration_sec=4.0, fps=25.0, width=200, height=100,
                                      frame_count=100, codec="h264")

    def get_frame_at_index(self, idx):
        arr = np.full((100, 200, 3), 90, np.uint8)
        arr[40:60, 10 + idx:30 + idx] = (200, 30, 30)
        return idx / 25.0, Image.fromarray(arr)


class FakeSam2:
    def __init__(self):
        self.calls = []

    def predict_video(self, video_input, prompt_box, prompt_frame_idx, bidirectional=False):
        files = sorted(Path(video_input).glob("*.jpg"))
        self.calls.append({"frames": len(files), "prompt_pos": prompt_frame_idx, "bidirectional": bidirectional})
        out = {}
        for pos, f in enumerate(files):
            arr = np.asarray(Image.open(f))
            mask = (arr[..., 0] > 150) & (arr[..., 1] < 80)
            out[pos] = {"mask": mask.astype(np.uint8), "score": 0.9}
        out[2] = {"mask": np.zeros((100, 200), np.uint8), "score": 0.0}  # object lost on one frame
        return out


def test_box_from_mask_is_normalised_ymin_xmin_ymax_xmax():
    m = np.zeros((100, 200), bool)
    m[40:60, 10:30] = True
    assert _box_from_mask(m) == [0.4, 0.05, 0.6, 0.15]
    assert _box_from_mask(np.zeros((4, 4), bool)) is None


def test_track_follows_the_object_both_directions_and_measures_its_colour(tmp_path):
    sam2 = FakeSam2()
    track = track_event(FakeDecoder(), sam2, start_frame=20, end_frame=60, anchor_frame=40,
                        anchor_box_2d=[0.4, 0.25, 0.6, 0.35], work_dir=tmp_path)
    call = sam2.calls[0]
    assert call["bidirectional"] is True
    assert call["frames"] == 21                      # 25 fps / 10 fps -> stride 2, frames 20, 22 .. 60 (anchor 40 included)
    assert [p["frame"] for p in track][:3] == [20, 22, 26]   # position 2 (frame 24) had an empty mask: omitted
    assert track[0]["t"] == 0.8
    xs = [p["box_2d"][1] for p in track]
    assert xs == sorted(xs) and xs[-1] > xs[0]       # box moves right with the object
    assert all(p["rgb"][0] > 150 and p["rgb"][1] < 80 for p in track)   # measured colour is red
    assert not list(tmp_path.iterdir())              # temporary frames removed


def test_object_colour_ignores_grey_windows_but_keeps_grey_cars_grey():
    from backend.app.video.tracker import _object_colour
    red_body_grey_glass = np.array([[200, 30, 30]] * 70 + [[120, 120, 125]] * 30, np.uint8)
    assert tuple(int(v) for v in _object_colour(red_body_grey_glass)) == (200, 30, 30)
    white_car = np.array([[230, 230, 235]] * 90 + [[200, 40, 40]] * 10, np.uint8)
    assert tuple(int(v) for v in _object_colour(white_car)) == (230, 230, 235)


def test_keyframe_outline_leaves_object_pixels_unchanged():
    arr = np.full((50, 50, 3), 90, np.uint8)
    arr[10:40, 10:40] = (200, 30, 30)
    mask = np.zeros((50, 50), np.uint8)
    mask[10:40, 10:40] = 1
    out = np.asarray(draw_mask_outline(Image.fromarray(arr), mask))
    assert tuple(out[25, 25]) == (200, 30, 30)       # centre keeps its red
    assert tuple(out[10, 25]) == (0, 230, 150)       # boundary drawn
    assert tuple(out[5, 5]) == (90, 90, 90)          # background untouched
