"""
SatQuery AI — Continuous Probability Heatmaps & Overlay Engine
Generates model probability heatmaps (ChangeFormer change probability, SAM 2 confidence),
intensity heatmaps, and alpha-blended evidence overlays with explicit legends and thresholds.
Zero-fabrication: Never represents a probability heatmap as an 'accuracy map'.
"""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.app.visualization.provenance import LayerProvenance, VisualizationType, LayerMetadata
from backend.app.visualization.composites import generate_colorbar_legend
from backend.app.logging import logger


class HeatmapEngine:
    """
    Renders continuous probability heatmaps and evidence overlays.
    """

    @classmethod
    def render_probability_heatmap(
        cls,
        prob_map: np.ndarray,
        base_image: Optional[Image.Image] = None,
        threshold: float = 0.5,
        source_model: str = "ChangeFormer",
        title: str = "Change Probability Heatmap",
        colormap: str = "turbo",
        alpha: float = 0.65
    ) -> Tuple[Image.Image, Image.Image, LayerMetadata]:
        """
        Renders a continuous model probability heatmap [0.0, 1.0].
        If base_image is provided, alpha-blends the heatmap over the base image.
        Generates an explicit colorbar legend with threshold marker.
        """
        arr = np.squeeze(prob_map).astype(np.float32)
        arr = np.clip(arr, 0.0, 1.0)
        h, w = arr.shape

        valid = arr[np.isfinite(arr)]
        min_val = float(np.min(valid)) if valid.size > 0 else 0.0
        max_val = float(np.max(valid)) if valid.size > 0 else 1.0
        mean_val = float(np.mean(valid)) if valid.size > 0 else 0.0

        # Apply continuous colormap
        cmap = matplotlib.colormaps.get_cmap(colormap)
        rgba_heatmap = (cmap(arr) * 255.0).astype(np.uint8)

        # Pixels below 0.05 can have reduced opacity so background remains visible
        opacity_channel = np.clip((arr / 0.5) * alpha * 255.0, 0, int(alpha * 255)).astype(np.uint8)
        rgba_heatmap[..., 3] = opacity_channel

        heatmap_img = Image.fromarray(rgba_heatmap, "RGBA")

        if base_image is not None:
            base_rgba = base_image.convert("RGBA").resize((w, h), Image.Resampling.BILINEAR)
            composite_img = Image.alpha_composite(base_rgba, heatmap_img)
        else:
            composite_img = heatmap_img

        # Create colorbar legend with threshold marker
        legend_img = cls._generate_probability_legend(threshold=threshold, cmap_name=colormap)

        layer_meta = LayerMetadata(
            layer_id="model_probability_heatmap",
            layer_type=VisualizationType.PROBABILITY_HEATMAP,
            title=title,
            provenance=LayerProvenance.MODEL_PROBABILITY,
            source_model=source_model,
            units="Probability [0.0 - 1.0]",
            min_value=round(min_val, 4),
            max_value=round(max_val, 4),
            mean_value=round(mean_val, 4),
            colormap=colormap,
            legend_labels={"0.0": "Low/No change", "1.0": "High change", "threshold": f"{threshold:.2f}"},
            raw_stats={
                "threshold": threshold,
                "model": source_model,
                "above_threshold_pct": round(float(np.mean(arr >= threshold) * 100.0), 2),
                "scientific_disclaimer": "Model probability heatmap; not a calibrated accuracy metric."
            }
        )

        return composite_img, legend_img, layer_meta

    @classmethod
    def render_binary_prediction_mask(
        cls,
        mask: np.ndarray,
        base_image: Optional[Image.Image] = None,
        source_model: str = "ChangeFormer",
        color_rgb: Tuple[int, int, int] = (239, 68, 68),  # Red
        alpha: float = 0.5
    ) -> Tuple[Image.Image, LayerMetadata]:
        """
        Renders discrete binary prediction mask (0=Unchanged, 1=Changed).
        """
        arr = np.squeeze(mask).astype(np.uint8)
        bin_mask = (arr > 0).astype(np.uint8)
        h, w = bin_mask.shape

        changed_pixels = int(np.sum(bin_mask > 0))
        total_pixels = int(bin_mask.size)
        changed_pct = round((changed_pixels / total_pixels) * 100.0, 3)

        overlay_np = np.zeros((h, w, 4), dtype=np.uint8)
        overlay_np[bin_mask > 0] = [color_rgb[0], color_rgb[1], color_rgb[2], int(alpha * 255)]
        overlay_img = Image.fromarray(overlay_np, "RGBA")

        if base_image is not None:
            base_rgba = base_image.convert("RGBA").resize((w, h), Image.Resampling.NEAREST)
            composite_img = Image.alpha_composite(base_rgba, overlay_img)
        else:
            composite_img = overlay_img

        layer_meta = LayerMetadata(
            layer_id="binary_prediction_mask",
            layer_type=VisualizationType.BINARY_MASK,
            title="Binary Prediction Mask (0=Unchanged, 1=Changed)",
            provenance=LayerProvenance.MODEL_OUTPUT,
            source_model=source_model,
            units="Discrete Binary State",
            min_value=0.0,
            max_value=1.0,
            mean_value=round(float(changed_pixels / total_pixels), 4),
            legend_labels={"0": "Unchanged", "1": "Changed"},
            raw_stats={
                "changed_pixel_count": changed_pixels,
                "total_pixel_count": total_pixels,
                "changed_percentage": changed_pct,
                "model": source_model
            }
        )

        return composite_img, layer_meta

    @classmethod
    def _generate_probability_legend(
        cls,
        threshold: float = 0.5,
        cmap_name: str = "turbo",
        width_px: int = 300,
        height_px: int = 70
    ) -> Image.Image:
        """Generates colorbar legend with threshold marker."""
        fig, ax = plt.subplots(figsize=(width_px / 100, height_px / 100), dpi=100)
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        norm = matplotlib.colors.Normalize(vmin=0.0, vmax=1.0)
        cmap = matplotlib.colormaps.get_cmap(cmap_name)

        cbar = fig.colorbar(
            matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
            cax=ax,
            orientation="horizontal"
        )
        cbar.set_label("Change Probability [0.0 → 1.0]", color="#cbd5e1", fontsize=8, labelpad=4)
        cbar.ax.tick_params(labelsize=7, colors="#94a3b8")

        # Add vertical line for threshold
        ax.axvline(threshold, color="#f87171", linestyle="--", linewidth=1.5)
        ax.text(threshold, 1.25, f"Threshold {threshold:.2f}", color="#f87171", fontsize=7, ha="center", transform=ax.get_xaxis_transform())

        import io
        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", dpi=100)
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).convert("RGBA")
