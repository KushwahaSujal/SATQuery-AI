"""
SatQuery AI — SAR Polarization & Radar Backscatter Visualization Engine
Visualizes authentic SAR polarizations (VV, VH, HH, HV, Dual-Pol composites).
Preserves radiometric backscatter units without arbitrary dB conversions.
"""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.app.geo.metadata import RasterMetadata
from backend.app.visualization.provenance import LayerProvenance, VisualizationType, LayerMetadata
from backend.app.visualization.composites import generate_colorbar_legend, _apply_percentile_stretch
from backend.app.logging import logger


class SARVisualizationEngine:
    """
    Handles radar backscatter visualization for authenticated SAR polarizations.
    """

    @classmethod
    def resolve_polarization_bands(
        cls,
        arr: np.ndarray,
        metadata: Optional[RasterMetadata]
    ) -> Dict[str, Optional[int]]:
        """
        Maps radar polarization channels (VV, VH, HH, HV) to array channel indices.
        """
        num_bands = arr.shape[0] if arr.ndim == 3 else 1
        pol_map: Dict[str, Optional[int]] = {
            "vv": None,
            "vh": None,
            "hh": None,
            "hv": None
        }

        if metadata and metadata.band_descriptions:
            for idx, desc in enumerate(metadata.band_descriptions):
                if idx >= num_bands:
                    break
                d = desc.lower().strip()
                if "vv" in d:
                    pol_map["vv"] = idx
                elif "vh" in d:
                    pol_map["vh"] = idx
                elif "hh" in d:
                    pol_map["hh"] = idx
                elif "hv" in d:
                    pol_map["hv"] = idx

        # Standard dual-pol convention if not explicitly tagged (Sentinel-1 default: Band 1=VV, Band 2=VH)
        if num_bands == 2 and pol_map["vv"] is None and pol_map["vh"] is None:
            pol_map["vv"] = 0
            pol_map["vh"] = 1

        return pol_map

    @classmethod
    def render_polarization_layer(
        cls,
        arr: np.ndarray,
        pol_key: str,
        metadata: Optional[RasterMetadata] = None,
        to_db: bool = False
    ) -> Tuple[Image.Image, Image.Image, LayerMetadata]:
        """
        Renders a single polarization backscatter layer with percentile stretching.
        Applies logarithmic dB transformation ONLY if to_db is explicitly requested
        and input values are strictly positive linear power/intensity.
        """
        pol_map = cls.resolve_polarization_bands(arr, metadata)
        band_idx = pol_map.get(pol_key.lower())

        if band_idx is None:
            raise ValueError(f"Polarization '{pol_key.upper()}' is not present in this SAR raster.")

        data = arr[band_idx].astype(np.float32)
        valid = data[np.isfinite(data)]
        units = metadata.tags.get("UNITS", "Linear Intensity") if metadata else "Linear Intensity"

        if to_db:
            # Validate values are positive linear power before log10
            pos = valid[valid > 0]
            if pos.size > 0:
                with np.errstate(divide="ignore", invalid="ignore"):
                    data = np.where(data > 0, 10.0 * np.log10(data), -30.0)
                units = "dB (decibels)"
            else:
                to_db = False

        norm_uint8, raw_min, raw_max, raw_mean = _apply_percentile_stretch(data, p_min=1.0, p_max=99.0)

        # Grayscale / high-contrast radar backscatter
        cmap = matplotlib.colormaps.get_cmap("gray")
        rgba = (cmap(norm_uint8 / 255.0) * 255.0).astype(np.uint8)
        img = Image.fromarray(rgba, "RGBA")

        legend = generate_colorbar_legend(
            vmin=round(raw_min, 2),
            vmax=round(raw_max, 2),
            cmap_name="gray",
            title=f"SAR {pol_key.upper()} Backscatter",
            units=units
        )

        layer_meta = LayerMetadata(
            layer_id=f"sar_{pol_key.lower()}",
            layer_type=VisualizationType.SAR_POLARIZATION,
            title=f"SAR Backscatter — {pol_key.upper()}",
            provenance=LayerProvenance.SOURCE_DATA,
            units=units,
            min_value=round(raw_min, 4),
            max_value=round(raw_max, 4),
            mean_value=round(raw_mean, 4),
            colormap="gray",
            crs=metadata.crs if metadata else None,
            bounds=metadata.bounds if metadata else None,
            resolution=metadata.resolution if metadata else None,
            raw_stats={
                "polarization": pol_key.upper(),
                "band_index": band_idx,
                "db_transformed": to_db,
                "scientific_note": "Polarized radar backscatter intensity. Color indicates radar reflectivity; not optical surface color."
            }
        )

        return img, legend, layer_meta

    @classmethod
    def render_dual_pol_composite(
        cls,
        arr: np.ndarray,
        metadata: Optional[RasterMetadata] = None
    ) -> Tuple[Image.Image, LayerMetadata]:
        """
        Renders standard dual-pol false-color composite:
        Red = VV, Green = VH, Blue = VV / (VH + eps) ratio.
        """
        pol_map = cls.resolve_polarization_bands(arr, metadata)
        vv_idx = pol_map.get("vv")
        vh_idx = pol_map.get("vh")

        if vv_idx is None or vh_idx is None:
            raise ValueError("Dual-pol composite requires both VV and VH polarization bands.")

        vv = arr[vv_idx].astype(np.float32)
        vh = arr[vh_idx].astype(np.float32)

        eps = 1e-6
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(vh > 0, vv / (vh + eps), 0.0)

        ch_vv, min_vv, max_vv, mean_vv = _apply_percentile_stretch(vv, p_min=1.0, p_max=99.0)
        ch_vh, min_vh, max_vh, mean_vh = _apply_percentile_stretch(vh, p_min=1.0, p_max=99.0)
        ch_ratio, _, _, _ = _apply_percentile_stretch(ratio, p_min=2.0, p_max=98.0)

        rgb_stack = np.stack([ch_vv, ch_vh, ch_ratio], axis=-1)
        img = Image.fromarray(rgb_stack, "RGB")

        layer_meta = LayerMetadata(
            layer_id="sar_dual_pol_composite",
            layer_type=VisualizationType.SAR_POLARIZATION,
            title="SAR Dual-Pol Composite (R: VV, G: VH, B: VV/VH)",
            provenance=LayerProvenance.DERIVED_INDEX,
            units="Composite Display",
            min_value=0.0,
            max_value=255.0,
            crs=metadata.crs if metadata else None,
            bounds=metadata.bounds if metadata else None,
            resolution=metadata.resolution if metadata else None,
            raw_stats={
                "red_channel": f"VV (Band {vv_idx + 1})",
                "green_channel": f"VH (Band {vh_idx + 1})",
                "blue_channel": "VV/VH Ratio",
                "scientific_note": "Dual-polarization SAR decomposition emphasizing volumetric vs surface backscatter."
            }
        )
        return img, layer_meta
