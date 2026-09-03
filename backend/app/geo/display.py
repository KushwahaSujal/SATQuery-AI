import numpy as np
from PIL import Image
from typing import Optional, Tuple
from pathlib import Path
from backend.app.config import settings
from backend.app.logging import logger


def render_display_rgb(
    arr: np.ndarray,
    bands: Optional[Tuple[int, int, int]] = None,
    percentile_min: float = 2.0,
    percentile_max: float = 98.0,
    max_dim: int = 1024
) -> Image.Image:
    """
    Renders an arbitrary multi-band raster as a crisp, contrast-stretched 8-bit RGB image
    strictly for UI display and visualization.
    Does NOT alter underlying raw numeric arrays used for ML inference.
    """
    # Normalize arr shape to (C, H, W)
    if arr.ndim == 2:
        arr = arr[np.newaxis, ...]
    elif arr.ndim == 3 and arr.shape[2] in [1, 2, 3, 4] and arr.shape[0] > arr.shape[2]:
        arr = np.transpose(arr, (2, 0, 1))

    c, h, w = arr.shape

    if c >= 3:
        if bands is not None and len(bands) == 3:
            rgb_arr = arr[[bands[0], bands[1], bands[2]], :, :]
        else:
            rgb_arr = arr[:3, :, :]
    elif c == 2:
        # e.g., SAR dual-pol [VV, VH] -> compose [VV, VH, VV/VH ratio]
        vv = arr[0]
        vh = arr[1]
        ratio = np.where(vh != 0, vv / (vh + 1e-6), 0)
        rgb_arr = np.stack([vv, vh, ratio], axis=0)
    elif c == 1:
        # Grayscale -> replicate to 3 channels
        rgb_arr = np.repeat(arr, 3, axis=0)
    else:
        rgb_arr = arr[:3, :, :]

    # Robust 2%-98% percentile stretching per channel
    stretched_channels = []
    for i in range(3):
        ch = rgb_arr[i].astype(np.float32)
        # Filter out nodata/NaN/Inf
        valid = ch[np.isfinite(ch)]
        if valid.size > 0:
            p_min = np.percentile(valid, percentile_min)
            p_max = np.percentile(valid, percentile_max)
            if p_max > p_min:
                ch_norm = np.clip((ch - p_min) / (p_max - p_min) * 255.0, 0, 255)
            else:
                ch_norm = np.clip(ch, 0, 255)
        else:
            ch_norm = np.zeros_like(ch)
        stretched_channels.append(ch_norm.astype(np.uint8))

    rgb_uint8 = np.stack(stretched_channels, axis=-1)  # (H, W, 3)
    img = Image.fromarray(rgb_uint8)

    # Downscale if exceeding max_dim for UI responsiveness
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

    return img


def save_display_preview(
    arr: np.ndarray,
    output_path: Path | str,
    bands: Optional[Tuple[int, int, int]] = None
) -> Path:
    """Generates and saves a display preview PNG image."""
    img = render_display_rgb(arr, bands=bands)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), format="PNG", optimize=True)
    return out
