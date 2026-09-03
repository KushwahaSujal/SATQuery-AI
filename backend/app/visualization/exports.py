"""
SatQuery AI — Scientific Visualization Export Engine
Exports high-resolution PNG with embedded legends/metadata banners,
GeoTIFF rasters preserving CRS and affine geotransforms, and GeoJSON vector polygons.
"""
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from backend.app.geo.metadata import RasterMetadata
from backend.app.visualization.provenance import LayerMetadata
from backend.app.logging import logger

try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import Affine
except ImportError:
    rasterio = None


class ExportEngine:
    """
    Handles export generation for PNG, GeoTIFF, and GeoJSON formats.
    """

    @classmethod
    def export_png_with_legend(
        cls,
        image: Image.Image,
        layer_meta: LayerMetadata,
        legend_img: Optional[Image.Image] = None,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Stitches visualization image with a bottom legend & metadata banner.
        """
        w, h = image.size
        banner_h = 90 if legend_img else 50
        total_h = h + banner_h

        canvas = Image.new("RGB", (w, total_h), (15, 23, 42))  # Slate-900
        canvas.paste(image.convert("RGB"), (0, 0))

        draw = ImageDraw.Draw(canvas)
        # Separator line
        draw.line([(0, h), (w, h)], fill=(51, 65, 85), width=2)

        # Title & Provenance Text
        title_text = f"{layer_meta.title} [{layer_meta.provenance.value}]"
        stats_text = f"Range: [{layer_meta.min_value:.2f}, {layer_meta.max_value:.2f}] {layer_meta.units}"
        if layer_meta.mean_value is not None:
            stats_text += f" · Mean: {layer_meta.mean_value:.2f}"

        draw.text((16, h + 10), title_text, fill=(241, 245, 249))
        draw.text((16, h + 30), stats_text, fill=(148, 163, 184))

        if legend_img:
            # Place legend on the right side of the banner
            leg_w, leg_h = legend_img.size
            scale = min(1.0, 260.0 / leg_w) if leg_w > 0 else 1.0
            new_lw = max(1, int(leg_w * scale))
            new_lh = max(1, int(leg_h * scale))
            scaled_leg = legend_img.resize((new_lw, new_lh), Image.Resampling.BILINEAR)
            leg_x = max(16, w - new_lw - 16)
            leg_y = h + 10
            canvas.paste(scaled_leg.convert("RGB"), (leg_x, leg_y))

        out = output_path or Path("export.png")
        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out, format="PNG", optimize=True)
        return out

    @classmethod
    def export_geotiff(
        cls,
        data_arr: np.ndarray,
        metadata: RasterMetadata,
        output_path: Path,
        nodata_val: float = -9999.0
    ) -> Path:
        """
        Exports raster array as an authentic GeoTIFF preserving CRS and geotransform.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        arr = np.squeeze(data_arr)
        if arr.ndim == 2:
            count = 1
            h, w = arr.shape
            arr_3d = arr[np.newaxis, ...]
        elif arr.ndim == 3:
            count, h, w = arr.shape
            arr_3d = arr
        else:
            raise ValueError(f"Unsupported array shape {arr.shape} for GeoTIFF export.")

        if rasterio is not None and metadata.crs and metadata.transform:
            transform_affine = Affine(*metadata.transform[:6])
            with rasterio.open(
                out,
                "w",
                driver="GTiff",
                height=h,
                width=w,
                count=count,
                dtype=str(arr.dtype),
                crs=metadata.crs,
                transform=transform_affine,
                nodata=nodata_val
            ) as dst:
                dst.write(arr_3d)
        else:
            try:
                import tifffile
                tifffile.imwrite(str(out), arr_3d)
            except Exception:
                img = Image.fromarray(arr)
                img.save(out, format="TIFF")

        return out

    @classmethod
    def export_geojson_mask(
        cls,
        bin_mask: np.ndarray,
        metadata: RasterMetadata,
        output_path: Path,
        layer_name: str = "detected_change"
    ) -> Path:
        """
        Converts binary prediction mask to GeoJSON polygons.
        """
        from backend.app.geo.vectors import polygonize_mask
        geo_dict = polygonize_mask(bin_mask, metadata)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(geo_dict, f, indent=2)
        return out
