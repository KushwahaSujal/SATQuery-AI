from typing import Literal, Optional, Tuple
import numpy as np
import torch
import torchvision.transforms as T
from backend.app.logging import logger

SARRepresentation = Literal["linear", "dB", "unknown"]


class SARPreprocessor:
    """
    Robust Synthetic Aperture Radar (SAR) data preprocessor.
    Supports explicit data representations (linear amplitude/intensity, decibels (dB), or unknown),
    power-law normalization, clipping, and nodata handling.
    Never blindly applies linear-to-dB transformation without checking representation mode.
    """
    @staticmethod
    def preprocess_sar(
        arr: np.ndarray,
        representation: SARRepresentation = "linear",
        convert_to_db: bool = False,
        clip_min_db: float = -35.0,
        clip_max_db: float = 0.0,
        target_size: Optional[Tuple[int, int]] = (512, 512),
        output_channels: int = 2
    ) -> torch.Tensor:
        """
        Prepares a SAR raster array as a standardized float tensor for feature encoders.
        Returns tensor with shape (1, C, H, W).
        """
        # Ensure shape (C, H, W)
        if arr.ndim == 2:
            arr = arr[np.newaxis, ...]
        elif arr.ndim == 3 and arr.shape[2] <= 4 and arr.shape[0] > arr.shape[2]:
            arr = np.transpose(arr, (2, 0, 1))

        sar_data = arr.astype(np.float32)

        # Replace NaNs / Infs with 0
        sar_data = np.nan_to_num(sar_data, nan=0.0, posinf=0.0, neginf=0.0)

        # Convert to dB if requested and data is in linear representation
        if convert_to_db:
            if representation == "linear":
                # 10 * log10(intensity + eps)
                sar_data = 10.0 * np.log10(np.maximum(sar_data, 1e-6))
                # Clip to typical SAR dB range
                sar_data = np.clip(sar_data, clip_min_db, clip_max_db)
                # Normalize dB to [0, 1]
                sar_data = (sar_data - clip_min_db) / (clip_max_db - clip_min_db)
            elif representation == "dB":
                logger.info("SAR data already declared in dB representation. Skipping linear-to-dB conversion.")
                sar_data = np.clip(sar_data, clip_min_db, clip_max_db)
                sar_data = (sar_data - clip_min_db) / (clip_max_db - clip_min_db)
            else:
                logger.warning("SAR representation unknown. Applying conservative min-max stretching without dB conversion.")
                sar_data = SARPreprocessor._normalize_min_max(sar_data)
        else:
            # Standard normalization
            sar_data = SARPreprocessor._normalize_min_max(sar_data)

        # Ensure requested output channels (e.g. 2 for VV/VH or duplicate single channel)
        c, h, w = sar_data.shape
        if c < output_channels:
            repeats = int(np.ceil(output_channels / c))
            sar_data = np.repeat(sar_data, repeats, axis=0)[:output_channels, :, :]
        elif c > output_channels:
            sar_data = sar_data[:output_channels, :, :]

        tensor = torch.from_numpy(sar_data)

        if target_size is not None:
            resize_transform = T.Resize(target_size, antialias=True)
            tensor = resize_transform(tensor)

        return tensor.unsqueeze(0)  # (1, C, H, W)

    @staticmethod
    def _normalize_min_max(arr: np.ndarray) -> np.ndarray:
        c, h, w = arr.shape
        out = np.zeros_like(arr, dtype=np.float32)
        for i in range(c):
            ch = arr[i]
            valid = ch[np.isfinite(ch) & (ch > 0)]
            if valid.size > 0:
                p1 = np.percentile(valid, 1)
                p99 = np.percentile(valid, 99)
                if p99 > p1:
                    out[i] = np.clip((ch - p1) / (p99 - p1), 0.0, 1.0)
                else:
                    out[i] = np.zeros_like(ch)
            else:
                out[i] = np.zeros_like(ch)
        return out
