from typing import Generator, List, Tuple, Optional
import numpy as np
from backend.app.config import settings


class RasterTiler:
    """
    Sliding-window tiling engine for large remote-sensing scenes.
    Yields overlapping window patches and seamlessly reconstructs full-resolution spatial outputs.
    """
    def __init__(self, tile_size: Optional[int] = None, overlap: Optional[int] = None):
        self.tile_size = tile_size or settings.geospatial.tiling.tile_size
        self.overlap = overlap or settings.geospatial.tiling.overlap
        self.stride = self.tile_size - self.overlap

    def generate_tiles(
        self, arr: np.ndarray
    ) -> Generator[Tuple[np.ndarray, int, int, int, int], None, None]:
        """
        Yields (tile_array, y_start, y_end, x_start, x_end)
        arr shape is (C, H, W) or (H, W).
        """
        if arr.ndim == 2:
            h, w = arr.shape
            is_2d = True
        else:
            _, h, w = arr.shape
            is_2d = False

        for y in range(0, h, self.stride):
            for x in range(0, w, self.stride):
                y_end = min(y + self.tile_size, h)
                x_end = min(x + self.tile_size, w)
                y_start = max(0, y_end - self.tile_size)
                x_start = max(0, x_end - self.tile_size)

                if is_2d:
                    tile = arr[y_start:y_end, x_start:x_end]
                else:
                    tile = arr[:, y_start:y_end, x_start:x_end]

                yield tile, y_start, y_end, x_start, x_end

    def stitch_tiles(
        self,
        tile_predictions: List[Tuple[np.ndarray, int, int, int, int]],
        output_shape: Tuple[int, int],
        channels: int = 1
    ) -> np.ndarray:
        """
        Stitches overlapping tile predictions using smooth weight averaging.
        """
        h, w = output_shape
        full_pred = np.zeros((channels, h, w), dtype=np.float32) if channels > 1 else np.zeros((h, w), dtype=np.float32)
        weight_map = np.zeros((h, w), dtype=np.float32)

        # 2D Hanning/Cosine window for edge blending
        win_1d = np.hanning(self.tile_size)
        win_2d = np.outer(win_1d, win_1d).astype(np.float32)
        win_2d = np.maximum(win_2d, 1e-4)

        for pred_tile, ys, ye, xs, xe in tile_predictions:
            th, tw = ye - ys, xe - xs
            tile_w = win_2d[:th, :tw]

            if channels > 1:
                full_pred[:, ys:ye, xs:xe] += pred_tile[:, :th, :tw] * tile_w
            else:
                full_pred[ys:ye, xs:xe] += pred_tile[:th, :tw] * tile_w
            weight_map[ys:ye, xs:xe] += tile_w

        weight_map = np.maximum(weight_map, 1e-6)
        if channels > 1:
            full_pred /= weight_map[np.newaxis, ...]
        else:
            full_pred /= weight_map

        return full_pred
