"""
SatQuery AI — VideoDecoder Abstraction
Provides streaming, timestamp-based frame access for video footage (.mp4, .mov)
using OpenCV without loading entire videos into RAM.
"""
from typing import Generator, List, Optional, Tuple, Union
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

from backend.app.schemas.video import VideoMetadata
from backend.app.exceptions import InvalidInputError, UnsupportedFormatError, SatQueryException
from backend.app.logging import logger


class VideoDecodeError(SatQueryException):
    """Raised when video file cannot be opened, sought, or decoded."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message=message, code="VIDEO_DECODE_ERROR", details=details)


class VideoDecoder:
    """
    Streaming video decoder wrapping OpenCV cv2.VideoCapture.
    Supports context manager pattern for automatic file resource cleanup.
    Never loads all video frames into RAM simultaneously.
    """
    SUPPORTED_EXTENSIONS = {".mp4", ".mov"}

    def __init__(self, video_path: Union[str, Path]):
        self.path = Path(video_path).resolve()
        if not self.path.exists():
            raise InvalidInputError(f"Video file not found at '{self.path}'", details={"path": str(self.path)})

        ext = self.path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(
                f"Unsupported video format '{ext}'. Supported formats: {sorted(list(self.SUPPORTED_EXTENSIONS))}",
                details={"extension": ext, "supported": list(self.SUPPORTED_EXTENSIONS)}
            )

        self._cap: Optional[cv2.VideoCapture] = None
        self._metadata: Optional[VideoMetadata] = None

    def __enter__(self) -> "VideoDecoder":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def open(self) -> None:
        """Initializes OpenCV video capture and validates metadata."""
        if self._cap is not None and self._cap.isOpened():
            return

        self._cap = cv2.VideoCapture(str(self.path))
        if not self._cap.isOpened():
            raise VideoDecodeError(
                f"Failed to open video file '{self.path.name}' with OpenCV decoder.",
                details={"path": str(self.path)}
            )

        fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps <= 0.0 or np.isnan(fps):
            fps = 25.0  # Safe standard fallback if FPS flag is absent

        frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration_sec = float(frame_count / fps) if fps > 0 else 0.0

        fourcc_int = int(self._cap.get(cv2.CAP_PROP_FOURCC) or 0)
        codec_chars = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip()
        codec = codec_chars if codec_chars else "unknown"

        if width <= 0 or height <= 0:
            raise VideoDecodeError(
                f"Invalid video stream dimensions ({width}x{height}) in '{self.path.name}'.",
                details={"width": width, "height": height}
            )

        self._metadata = VideoMetadata(
            filename=self.path.name,
            duration_sec=round(duration_sec, 3),
            fps=round(fps, 3),
            width=width,
            height=height,
            frame_count=frame_count,
            codec=codec
        )
        logger.info(
            f"Opened video '{self.path.name}': {width}x{height}, {fps:.2f} fps, "
            f"{frame_count} frames, {duration_sec:.2f}s duration."
        )

    def close(self) -> None:
        """Releases video file handle."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def metadata(self) -> VideoMetadata:
        if self._metadata is None:
            self.open()
        return self._metadata

    def get_frame_at_index(self, frame_idx: int) -> Tuple[float, Image.Image]:
        """
        Extracts single frame at specified frame index.
        Returns (timestamp_sec, PIL.Image in RGB).
        """
        if self._cap is None or not self._cap.isOpened():
            self.open()

        frame_idx = max(0, min(frame_idx, self.metadata.frame_count - 1))
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, bgr_frame = self._cap.read()
        if not ret or bgr_frame is None:
            raise VideoDecodeError(
                f"Failed to read frame at index {frame_idx} from '{self.path.name}'.",
                details={"frame_index": frame_idx}
            )

        timestamp_sec = float(frame_idx / self.metadata.fps) if self.metadata.fps > 0 else 0.0
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        return timestamp_sec, Image.fromarray(rgb_frame)

    def get_frame_at_timestamp(self, timestamp_sec: float) -> Tuple[int, Image.Image]:
        """
        Extracts single frame closest to requested timestamp in seconds.
        Returns (frame_index, PIL.Image in RGB).
        """
        if self._cap is None or not self._cap.isOpened():
            self.open()

        timestamp_sec = max(0.0, min(timestamp_sec, self.metadata.duration_sec))
        frame_idx = int(round(timestamp_sec * self.metadata.fps))
        frame_idx = max(0, min(frame_idx, self.metadata.frame_count - 1))

        self._cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000.0)
        ret, bgr_frame = self._cap.read()
        if not ret or bgr_frame is None:
            # Fallback to direct frame index seek
            _, img = self.get_frame_at_index(frame_idx)
            return frame_idx, img

        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        return frame_idx, Image.fromarray(rgb_frame)

    def iter_frames(
        self,
        stride: int = 1,
        max_frames: Optional[int] = None
    ) -> Generator[Tuple[int, float, Image.Image], None, None]:
        """
        Yields (frame_index, timestamp_sec, PIL.Image) in streaming fashion with specified stride.
        Never buffers frames in memory.
        """
        if self._cap is None or not self._cap.isOpened():
            self.open()

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        current_idx = 0
        yielded_count = 0

        while True:
            ret, bgr_frame = self._cap.read()
            if not ret or bgr_frame is None:
                break

            if current_idx % stride == 0:
                timestamp_sec = float(current_idx / self.metadata.fps) if self.metadata.fps > 0 else 0.0
                rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                yield current_idx, timestamp_sec, Image.fromarray(rgb_frame)
                yielded_count += 1

                if max_frames is not None and yielded_count >= max_frames:
                    break

            current_idx += 1
