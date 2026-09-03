from pathlib import Path
from typing import Any, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw
from backend.app.geo.display import render_display_rgb


def create_change_overlay(
    bg_arr: Any,
    change_mask: np.ndarray,
    color_rgb: Tuple[int, int, int] = (255, 59, 48),  # Crimson Red
    alpha: float = 0.5,
    color: Optional[Tuple[int, int, int]] = None
) -> Image.Image:
    """
    Renders a high-contrast visual overlay of detected change/segmentation mask
    blended on top of the base image.
    """
    if color is not None:
        color_rgb = color

    if isinstance(bg_arr, Image.Image):
        base_img = bg_arr.convert("RGBA")
    else:
        base_img = render_display_rgb(bg_arr).convert("RGBA")
    w, h = base_img.size

    if change_mask.ndim > 2:
        change_mask = np.squeeze(change_mask)

    # Resize mask to match display image dimensions if needed
    mask_img = Image.fromarray((change_mask > 0).astype(np.uint8) * 255).resize(
        (w, h), Image.Resampling.NEAREST
    )
    mask_np = np.array(mask_img) > 0

    overlay_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay_np = np.zeros((h, w, 4), dtype=np.uint8)
    
    overlay_np[mask_np] = [color_rgb[0], color_rgb[1], color_rgb[2], int(alpha * 255)]
    overlay_layer = Image.fromarray(overlay_np, "RGBA")

    result = Image.alpha_composite(base_img, overlay_layer)
    return result


def create_side_by_side_comparison(
    arr1: np.ndarray,
    arr2: np.ndarray,
    overlay_img: Optional[Image.Image] = None,
    label1: str = "T1 (Before)",
    label2: str = "T2 (After)",
    label3: str = "Change Overlay"
) -> Image.Image:
    """
    Stitches before/after/overlay rasters side-by-side into a single high-resolution comparison panel.
    """
    img1 = render_display_rgb(arr1).convert("RGB")
    img2 = render_display_rgb(arr2).convert("RGB")

    target_h = 512
    # Scale both to target_h
    def scale_to_h(img: Image.Image, h: int) -> Image.Image:
        w = max(1, int(img.width * (h / float(img.height))))
        return img.resize((w, h), Image.Resampling.BILINEAR)

    img1 = scale_to_h(img1, target_h)
    img2 = scale_to_h(img2, target_h)

    images = [img1, img2]
    if overlay_img:
        images.append(scale_to_h(overlay_img.convert("RGB"), target_h))

    total_w = sum(img.width for img in images) + (len(images) - 1) * 8
    canvas = Image.new("RGB", (total_w, target_h), (24, 24, 27))  # Dark slate background

    x_offset = 0
    for img in images:
        canvas.paste(img, (x_offset, 0))
        x_offset += img.width + 8

    return canvas


def save_image(img: Image.Image, output_path: str | Path) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), format="PNG", optimize=True)
    return out
