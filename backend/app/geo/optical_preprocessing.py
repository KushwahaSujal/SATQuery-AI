from typing import List, Optional, Tuple
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image


def preprocess_optical_image(
    arr: np.ndarray,
    target_size: Optional[Tuple[int, int]] = (512, 512),
    selected_bands: Optional[List[int]] = None,
    mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
    std: Tuple[float, float, float] = (0.229, 0.224, 0.225),
) -> torch.Tensor:
    """
    Standard optical remote-sensing preprocessing for foundation models.
    Normalizes multi-band array to RGB tensor and standardizes values.
    """
    if arr.ndim == 2:
        arr = arr[np.newaxis, ...]
    elif arr.ndim == 3 and arr.shape[2] in [1, 2, 3, 4] and arr.shape[0] > arr.shape[2]:
        arr = np.transpose(arr, (2, 0, 1))

    c, h, w = arr.shape

    if selected_bands is not None and len(selected_bands) == 3:
        rgb = arr[selected_bands, :, :]
    elif c >= 3:
        rgb = arr[:3, :, :]
    elif c == 1:
        rgb = np.repeat(arr, 3, axis=0)
    else:
        rgb = arr[:3, :, :]

    rgb_float = rgb.astype(np.float32)

    # Scale to [0, 1]
    for i in range(3):
        ch = rgb_float[i]
        finite_mask = np.isfinite(ch)
        if finite_mask.any():
            min_val = np.min(ch[finite_mask])
            max_val = np.max(ch[finite_mask])
            if max_val > min_val:
                rgb_float[i] = np.clip((ch - min_val) / (max_val - min_val), 0.0, 1.0)
            else:
                rgb_float[i] = np.zeros_like(ch)
        else:
            rgb_float[i] = np.zeros_like(ch)

    tensor = torch.from_numpy(rgb_float)  # (3, H, W)

    if target_size is not None:
        resize_transform = T.Resize(target_size, antialias=True)
        tensor = resize_transform(tensor)

    normalize = T.Normalize(mean=mean, std=std)
    tensor = normalize(tensor)

    return tensor.unsqueeze(0)  # (1, 3, H, W)


def to_pil_rgb(arr: np.ndarray) -> Image.Image:
    """Helper to convert an optical raster array into standard PIL RGB Image."""
    if arr.ndim == 2:
        arr = arr[np.newaxis, ...]
    elif arr.ndim == 3 and arr.shape[2] in [1, 2, 3, 4] and arr.shape[0] > arr.shape[2]:
        arr = np.transpose(arr, (2, 0, 1))

    c, h, w = arr.shape
    if c >= 3:
        rgb = arr[:3, :, :]
    elif c == 1:
        rgb = np.repeat(arr, 3, axis=0)
    else:
        rgb = arr[:3, :, :]

    rgb_norm = []
    for i in range(3):
        ch = rgb[i].astype(np.float32)
        valid = ch[np.isfinite(ch)]
        if valid.size > 0:
            min_v, max_v = np.percentile(valid, 2), np.percentile(valid, 98)
            if max_v > min_v:
                norm_ch = np.clip((ch - min_v) / (max_v - min_v) * 255.0, 0, 255)
            else:
                norm_ch = np.clip(ch, 0, 255)
        else:
            norm_ch = np.zeros_like(ch)
        rgb_norm.append(norm_ch.astype(np.uint8))

    return Image.fromarray(np.stack(rgb_norm, axis=-1))
