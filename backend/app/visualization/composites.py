"""
SatQuery AI — Multispectral Composites & Single-Band Visualization Engine
Provides scientifically grounded True Color, False Color, Single Band, and Band Difference rendering.
Distinguishes display normalization from raw physical/radiometric values.
"""
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.app.geo.metadata import RasterMetadata
from backend.app.visualization.provenance import LayerProvenance, VisualizationType, LayerMetadata
from backend.app.logging import logger


def _apply_percentile_stretch(
    arr_2d: np.ndarray,
    p_min: float = 2.0,
    p_max: float = 98.0
) -> Tuple[np.ndarray, float, float, float]:
    """
    Computes display contrast stretching without altering underlying data.
    Returns (stretched_uint8, raw_min, raw_max, raw_mean).
    """
    data = arr_2d.astype(np.float32)
    valid = data[np.isfinite(data)]
    if valid.size == 0:
        return np.zeros_like(data, dtype=np.uint8), 0.0, 0.0, 0.0

    raw_min = float(np.min(valid))
    raw_max = float(np.max(valid))
    raw_mean = float(np.mean(valid))

    vmin = np.percentile(valid, p_min)
    vmax = np.percentile(valid, p_max)

    if vmax > vmin:
        norm = np.clip((data - vmin) / (vmax - vmin) * 255.0, 0, 255)
    else:
        norm = np.clip(data, 0, 255)

    return norm.astype(np.uint8), raw_min, raw_max, raw_mean


def generate_colorbar_legend(
    vmin: float,
    vmax: float,
    cmap_name: str = "viridis",
    title: str = "Value",
    units: str = "DN",
    width_px: int = 280,
    height_px: int = 65
) -> Image.Image:
    """
    Generates a high-resolution, transparent colorbar legend for derived layers.
    """
    fig, ax = plt.subplots(figsize=(width_px / 100, height_px / 100), dpi=100)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
    cmap = matplotlib.colormaps.get_cmap(cmap_name)

    cbar = fig.colorbar(
        matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=ax,
        orientation="horizontal"
    )
    cbar.set_label(f"{title} ({units})", color="#cbd5e1", fontsize=8, labelpad=4)
    cbar.ax.tick_params(labelsize=7, colors="#94a3b8")

    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


class CompositeRenderer:
    """Renders authentic optical composites and individual spectral bands."""

    @classmethod
    def render_true_color(
        cls,
        arr: np.ndarray,
        metadata: Optional[RasterMetadata] = None,
        rgb_bands: Tuple[int, int, int] = (0, 1, 2)
    ) -> Tuple[Image.Image, LayerMetadata]:
        """
        Renders True Color / RGB using authentic visible spectral bands.
        """
        if arr.ndim == 2:
            arr = arr[np.newaxis, ...]
        elif arr.ndim == 3 and arr.shape[2] in [1, 3, 4] and arr.shape[0] > arr.shape[2]:
            arr = np.transpose(arr, (2, 0, 1))

        c, h, w = arr.shape
        r_idx, g_idx, b_idx = rgb_bands

        if max(r_idx, g_idx, b_idx) >= c:
            raise ValueError(f"True Color requires 3 visible bands, but raster only contains {c} band(s).")

        ch_r, min_r, max_r, mean_r = _apply_percentile_stretch(arr[r_idx])
        ch_g, min_g, max_g, mean_g = _apply_percentile_stretch(arr[g_idx])
        ch_b, min_b, max_b, mean_b = _apply_percentile_stretch(arr[b_idx])

        rgb_stack = np.stack([ch_r, ch_g, ch_b], axis=-1)
        img = Image.fromarray(rgb_stack, "RGB")

        layer_meta = LayerMetadata(
            layer_id="true_color",
            layer_type=VisualizationType.TRUE_COLOR,
            title="True Color / RGB",
            provenance=LayerProvenance.SOURCE_DATA,
            units="DN",
            min_value=float(min(min_r, min_g, min_b)),
            max_value=float(max(max_r, max_g, max_b)),
            mean_value=float((mean_r + mean_g + mean_b) / 3.0),
            crs=metadata.crs if metadata else None,
            bounds=metadata.bounds if metadata else None,
            resolution=metadata.resolution if metadata else None,
            raw_stats={"r_mean": mean_r, "g_mean": mean_g, "b_mean": mean_b}
        )
        return img, layer_meta

    @classmethod
    def render_false_color(
        cls,
        arr: np.ndarray,
        metadata: Optional[RasterMetadata] = None,
        band_indices: Tuple[int, int, int] = (3, 0, 1),
        title: str = "False Color — NIR / Red / Green"
    ) -> Tuple[Image.Image, LayerMetadata]:
        """
        Renders a verified False Color composite using explicit multispectral bands.
        Default: R=NIR, G=Red, B=Green (Vegetation/Urban emphasis).
        """
        if arr.ndim == 2:
            arr = arr[np.newaxis, ...]
        elif arr.ndim == 3 and arr.shape[2] in [1, 3, 4] and arr.shape[0] > arr.shape[2]:
            arr = np.transpose(arr, (2, 0, 1))

        c, h, w = arr.shape
        b_r, b_g, b_b = band_indices

        if max(b_r, b_g, b_b) >= c:
            raise ValueError(f"False color composite '{title}' requires band indices {band_indices}, but raster has only {c} bands.")

        ch_r, min_r, max_r, mean_r = _apply_percentile_stretch(arr[b_r])
        ch_g, min_g, max_g, mean_g = _apply_percentile_stretch(arr[b_g])
        ch_b, min_b, max_b, mean_b = _apply_percentile_stretch(arr[b_b])

        composite_stack = np.stack([ch_r, ch_g, ch_b], axis=-1)
        img = Image.fromarray(composite_stack, "RGB")

        layer_meta = LayerMetadata(
            layer_id="false_color",
            layer_type=VisualizationType.FALSE_COLOR,
            title=title,
            provenance=LayerProvenance.DERIVED_INDEX,
            units="DN",
            min_value=float(min(min_r, min_g, min_b)),
            max_value=float(max(max_r, max_g, max_b)),
            mean_value=float((mean_r + mean_g + mean_b) / 3.0),
            crs=metadata.crs if metadata else None,
            bounds=metadata.bounds if metadata else None,
            resolution=metadata.resolution if metadata else None
        )
        return img, layer_meta

    @classmethod
    def render_single_band(
        cls,
        arr: np.ndarray,
        band_idx: int = 0,
        metadata: Optional[RasterMetadata] = None,
        colormap: str = "viridis"
    ) -> Tuple[Image.Image, Image.Image, LayerMetadata]:
        """
        Renders a single band with percentile-stretched colormap and colorbar legend.
        """
        if arr.ndim == 2:
            arr = arr[np.newaxis, ...]
        elif arr.ndim == 3 and arr.shape[2] in [1, 3, 4] and arr.shape[0] > arr.shape[2]:
            arr = np.transpose(arr, (2, 0, 1))

        c = arr.shape[0]
        if band_idx >= c:
            raise ValueError(f"Band index {band_idx} out of range for raster with {c} bands.")

        norm_uint8, raw_min, raw_max, raw_mean = _apply_percentile_stretch(arr[band_idx])

        cmap = matplotlib.colormaps.get_cmap(colormap)
        colored_rgba = (cmap(norm_uint8 / 255.0) * 255.0).astype(np.uint8)
        img = Image.fromarray(colored_rgba, "RGBA")

        band_name = metadata.band_descriptions[band_idx] if (metadata and metadata.band_descriptions and band_idx < len(metadata.band_descriptions)) else f"Band {band_idx + 1}"
        legend_img = generate_colorbar_legend(raw_min, raw_max, cmap_name=colormap, title=band_name)

        layer_meta = LayerMetadata(
            layer_id=f"band_{band_idx + 1}",
            layer_type=VisualizationType.SINGLE_BAND,
            title=f"Single Band — {band_name}",
            provenance=LayerProvenance.SOURCE_DATA,
            units="DN",
            min_value=raw_min,
            max_value=raw_max,
            mean_value=raw_mean,
            colormap=colormap,
            crs=metadata.crs if metadata else None,
            bounds=metadata.bounds if metadata else None,
            resolution=metadata.resolution if metadata else None
        )
        return img, legend_img, layer_meta
