"""
SatQuery AI — VideoSampler
Implements configurable coarse sampling, adaptive stride, and event-focused resampling
without exhausting memory.
"""
from typing import List, Optional, Set, Tuple
from PIL import Image

from backend.app.video.decoder import VideoDecoder
from backend.app.schemas.video import VideoSamplingConfig
from backend.app.logging import logger


class VideoSampler:
    """
    Manages multi-tier frame extraction:
    Tier 1: Uniform / coarse sampling at target FPS (e.g. 1.0 FPS)
    Tier 2: Event-focused local window resampling around detected triggers
    """

    @staticmethod
    def sample_coarse_frames(
        decoder: VideoDecoder,
        config: Optional[VideoSamplingConfig] = None
    ) -> List[Tuple[int, float, Image.Image]]:
        """
        Samples frames at specified sample_fps up to max_frames with stride.
        Returns list of (frame_index, timestamp_sec, PIL.Image).
        """
        cfg = config or VideoSamplingConfig()
        meta = decoder.metadata

        if meta.frame_count <= 0:
            return []

        # Calculate stride from target sampling fps
        raw_fps = meta.fps if meta.fps > 0 else 25.0
        frame_interval = max(1, int(round(raw_fps / cfg.sample_fps)))
        effective_stride = max(1, frame_interval * cfg.analysis_stride)

        sampled_results: List[Tuple[int, float, Image.Image]] = []

        # Stride iteration over video stream
        for frame_idx, timestamp_sec, pil_img in decoder.iter_frames(
            stride=effective_stride,
            max_frames=cfg.max_frames
        ):
            sampled_results.append((frame_idx, timestamp_sec, pil_img))

        logger.info(
            f"Coarse sampling completed for '{meta.filename}': extracted {len(sampled_results)} frames "
            f"(target {cfg.sample_fps} FPS, stride {effective_stride}, limit {cfg.max_frames})."
        )
        return sampled_results

    @staticmethod
    def sample_refinement_window(
        decoder: VideoDecoder,
        anchor_indices: List[int],
        window_size: int = 3,
        already_sampled_indices: Optional[Set[int]] = None
    ) -> List[Tuple[int, float, Image.Image]]:
        """
        Densely samples surrounding frames around candidate detections to refine event boundaries.
        Avoids re-extracting frames already in memory.
        """
        if not anchor_indices or window_size <= 0:
            return []

        seen = set(already_sampled_indices or set())
        meta = decoder.metadata
        max_idx = meta.frame_count - 1

        indices_to_fetch: Set[int] = set()
        for anchor in anchor_indices:
            for offset in range(-window_size, window_size + 1):
                target = anchor + offset
                if 0 <= target <= max_idx and target not in seen:
                    indices_to_fetch.add(target)

        refined_frames: List[Tuple[int, float, Image.Image]] = []
        for idx in sorted(list(indices_to_fetch)):
            ts, img = decoder.get_frame_at_index(idx)
            refined_frames.append((idx, ts, img))
            seen.add(idx)

        logger.info(f"Refinement window extraction: gathered {len(refined_frames)} additional frames.")
        return refined_frames
