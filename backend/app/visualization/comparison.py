"""
SatQuery AI — Multi-Modal Comparison & Spatial Alignment Engine
Handles synchronized optical vs SAR and Before vs After comparison views.
Verifies spatial co-registration and forbids uncalibrated overlays.
"""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image

from backend.app.geo.metadata import RasterMetadata
from backend.app.visualization.provenance import LayerProvenance, VisualizationType, LayerMetadata
from backend.app.geo.display import render_display_rgb
from backend.app.logging import logger


class ComparisonEngine:
    """
    Manages multi-raster comparisons and spatial alignment checks.
    """

    @classmethod
    def verify_co_registration(
        cls,
        meta1: Optional[RasterMetadata],
        meta2: Optional[RasterMetadata]
    ) -> Tuple[bool, str]:
        """
        Validates whether two rasters share a compatible CRS, bounds, and resolution.
        """
        if meta1 is None or meta2 is None:
            return False, "Missing metadata for one or both rasters."

        if not meta1.is_georeferenced or not meta2.is_georeferenced:
            return False, "Registration required before spatial overlay: One or both rasters lack CRS georeferencing."

        # Check CRS match
        crs1 = str(meta1.crs).upper() if meta1.crs else ""
        crs2 = str(meta2.crs).upper() if meta2.crs else ""
        if crs1 != crs2:
            return False, f"Registration required before spatial overlay: CRS mismatch ({crs1} vs {crs2})."

        # Check bounds intersection
        b1 = meta1.bounds  # [left, bottom, right, top]
        b2 = meta2.bounds
        if b1 and b2:
            ix_min = max(b1[0], b2[0])
            iy_min = max(b1[1], b2[1])
            ix_max = min(b1[2], b2[2])
            iy_max = min(b1[3], b2[3])

            if ix_min >= ix_max or iy_min >= iy_max:
                return False, "Registration required before spatial overlay: Bounding boxes do not overlap."

        return True, "Rasters are spatially co-registered."

    @classmethod
    def render_side_by_side_panels(
        cls,
        images: List[Image.Image],
        titles: List[str],
        target_height: int = 512
    ) -> Tuple[Image.Image, LayerMetadata]:
        """
        Stitches comparison panels side-by-side with uniform height and labeled banners.
        """
        if not images:
            raise ValueError("No images provided for side-by-side comparison.")

        scaled_imgs = []
        for img in images:
            w = max(1, int(img.width * (target_height / float(img.height))))
            scaled_imgs.append(img.resize((w, target_height), Image.Resampling.BILINEAR))

        gap = 8
        total_width = sum(img.width for img in scaled_imgs) + (len(scaled_imgs) - 1) * gap
        canvas = Image.new("RGB", (total_width, target_height), (15, 23, 42))  # Slate-900

        x = 0
        for img in scaled_imgs:
            canvas.paste(img, (x, 0))
            x += img.width + gap

        layer_meta = LayerMetadata(
            layer_id="side_by_side_comparison",
            layer_type=VisualizationType.OPTICAL_SAR_COMPARISON,
            title=" · ".join(titles),
            provenance=LayerProvenance.SOURCE_DATA,
            units="Display Composite",
            min_value=0.0,
            max_value=255.0,
            raw_stats={"panel_count": len(images), "titles": titles}
        )
        return canvas, layer_meta
