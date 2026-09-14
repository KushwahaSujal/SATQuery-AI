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


def joint_rgb8_pair(arr1: np.ndarray, arr2: np.ndarray, pmin: float = 2.0, pmax: float = 98.0) -> Tuple[np.ndarray, np.ndarray, Optional[str]]:
    """
    Converts a bi-temporal pair to 8-bit RGB (H, W, 3) for models trained on 8-bit imagery.

    8-bit RGB passes through unchanged. Anything else (uint16 reflectance, float, >3 bands) is
    reduced to the first three bands and stretched with ONE set of per-band percentiles computed
    over both dates together — stretching each date independently would manufacture radiometric
    differences that a change detector reports as change. Returns (rgb1, rgb2, note) where note
    describes the conversion, or None if nothing was done.
    """
    def hwc(a: np.ndarray) -> np.ndarray:
        if a.ndim == 2:
            a = a[..., None]
        elif a.ndim == 3 and a.shape[0] < a.shape[1] and a.shape[0] < a.shape[2]:
            a = np.transpose(a, (1, 2, 0))
        if a.shape[2] == 1:
            a = np.repeat(a, 3, axis=2)
        return a[..., :3]

    x1, x2 = hwc(arr1), hwc(arr2)
    if x1.dtype == np.uint8 and x2.dtype == np.uint8 and arr1.ndim == 3 and min(arr1.shape) == 3 and min(arr2.shape) == 3:
        return x1, x2, None

    f1, f2 = x1.astype(np.float32), x2.astype(np.float32)
    out1, out2 = np.zeros(x1.shape, np.uint8), np.zeros(x2.shape, np.uint8)
    for b in range(3):
        both = np.concatenate([f1[..., b][np.isfinite(f1[..., b])], f2[..., b][np.isfinite(f2[..., b])]])
        lo, hi = (np.percentile(both, pmin), np.percentile(both, pmax)) if both.size else (0.0, 1.0)
        scale = 255.0 / (hi - lo) if hi > lo else 0.0
        out1[..., b] = np.clip((np.nan_to_num(f1[..., b], nan=lo) - lo) * scale, 0, 255).astype(np.uint8)
        out2[..., b] = np.clip((np.nan_to_num(f2[..., b], nan=lo) - lo) * scale, 0, 255).astype(np.uint8)
    bands = arr1.shape[0] if (arr1.ndim == 3 and arr1.shape[0] < arr1.shape[-1]) else (arr1.shape[-1] if arr1.ndim == 3 else 1)
    note = (f"Input is {arr1.dtype} with {bands} band(s); converted to 8-bit RGB from the first three bands using a "
            f"joint {pmin:g}-{pmax:g}% stretch across both dates. ChangeFormer was trained on 8-bit RGB (LEVIR-CD).")
    return out1, out2, note
