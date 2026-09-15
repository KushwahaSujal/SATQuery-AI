"""
SatQuery AI — Event object tracker (video only).

Detection runs on coarsely sampled frames (~2 fps on real_aerial_footage.mp4), too sparse to draw a box that
follows a moving object. For each flagged event this re-reads the frames inside the event window at a denser
rate, prompts SAM 2.1 video propagation with the event's confirmed box, tracks the object forwards and
backwards, and turns each frame's mask into a normalised box. The median RGB of the object's own mask pixels is
kept per frame so the requested colour can be checked by eye, without a colour-filled mask hiding it (Q-019).
"""
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from backend.app.logging import logger
from backend.app.video.decoder import VideoDecoder

TRACK_FPS = 10.0
MAX_TRACK_FRAMES = 90
# Masks smaller than this fraction of the frame are treated as "object lost" rather than drawn.
MIN_MASK_AREA_RATIO = 0.0002


def _box_from_mask(mask: np.ndarray) -> Optional[List[float]]:
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return None
    h, w = mask.shape[:2]
    return [round(ys.min() / h, 4), round(xs.min() / w, 4), round((ys.max() + 1) / h, 4), round((xs.max() + 1) / w, 4)]


def _object_colour(pixels: np.ndarray) -> np.ndarray:
    """
    Median colour of the object's body. Windows, tyres and shadow are unsaturated and pull a plain median towards
    grey: on real_aerial_footage.mp4 frame 228 the red car's mask gives [148, 96, 111] over all pixels but
    [120, 39, 53] over pixels with saturation > 0.3 (67% of the mask). White, grey and black objects have few
    saturated pixels, so below 20% the plain median is used.
    """
    px = pixels.reshape(-1, 3).astype(np.float32)
    hi, lo = px.max(axis=1), px.min(axis=1)
    saturated = px[(hi - lo) / np.maximum(hi, 1.0) > 0.3]
    return np.median(saturated if len(saturated) >= 0.2 * len(px) else px, axis=0)


def track_event(
    decoder: VideoDecoder,
    sam2_adapter: Any,
    start_frame: int,
    end_frame: int,
    anchor_frame: int,
    anchor_box_2d: List[float],
    work_dir: Path,
) -> List[Dict[str, Any]]:
    """
    Returns track points ordered by time: {"t", "frame", "box_2d": [ymin, xmin, ymax, xmax] (0-1), "rgb": [r, g, b]}.
    Frames where the object's mask is empty or tiny are omitted, so a gap in the list means "not visible".
    """
    meta = decoder.metadata
    fps = meta.fps if meta.fps > 0 else 25.0
    stride = max(1, int(round(fps / TRACK_FPS)))
    indices = list(range(max(0, start_frame), min(end_frame, meta.frame_count - 1) + 1, stride))
    if anchor_frame not in indices:
        indices.append(anchor_frame)
        indices.sort()
    if len(indices) > MAX_TRACK_FRAMES:
        step = len(indices) / MAX_TRACK_FRAMES
        kept = {indices[int(i * step)] for i in range(MAX_TRACK_FRAMES)} | {anchor_frame}
        indices = sorted(kept)

    frames_dir = work_dir / f"track_{start_frame}_{end_frame}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    images: Dict[int, np.ndarray] = {}
    try:
        # SAM2VideoPredictor indexes a JPEG directory positionally (sorted file names), not by video frame number.
        for pos, idx in enumerate(indices):
            _, img = decoder.get_frame_at_index(idx)
            img.save(frames_dir / f"{pos:06d}.jpg", quality=95)
            images[idx] = np.asarray(img)

        results = sam2_adapter.predict_video(
            video_input=frames_dir,
            prompt_box=anchor_box_2d,
            prompt_frame_idx=indices.index(anchor_frame),
            bidirectional=True,
        )
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)

    track: List[Dict[str, Any]] = []
    for pos, idx in enumerate(indices):
        res = results.get(pos)
        if not res or res.get("mask") is None:
            continue
        mask = np.squeeze(res["mask"]) > 0
        if mask.mean() < MIN_MASK_AREA_RATIO:
            continue
        box = _box_from_mask(mask)
        if box is None:
            continue
        frame = images[idx]
        rgb = _object_colour(frame[mask]) if frame.shape[:2] == mask.shape else None
        track.append({
            "t": round(idx / fps, 3),
            "frame": idx,
            "box_2d": box,
            "rgb": [int(v) for v in rgb] if rgb is not None else None,
        })
    logger.info(f"Tracked event frames {start_frame}-{end_frame}: {len(track)}/{len(indices)} frames with the object.")
    return track
