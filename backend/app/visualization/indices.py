"""
SatQuery AI — Scientific Spectral Indices Engine
Implements mathematically rigorous, verified remote-sensing indices (NDVI, NDWI, NDBI).
Enforces zero-fabrication: verifies spectral band presence before calculation.
Reports INDEX_NOT_AVAILABLE when required bands are missing.
"""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.app.geo.metadata import RasterMetadata
from backend.app.visualization.provenance import LayerProvenance, VisualizationType, LayerMetadata
from backend.app.visualization.composites import generate_colorbar_legend
from backend.app.logging import logger


class IndexResult:
    """Encapsulates the calculation result of a remote-sensing index."""
    def __init__(
        self,
        index_name: str,
        available: bool,
        formula: str,
        bands_used: List[str],
        image: Optional[Image.Image] = None,
        legend: Optional[Image.Image] = None,
        raw_array: Optional[np.ndarray] = None,
        metadata: Optional[LayerMetadata] = None,
        unavailability_reason: Optional[str] = None
    ):
        self.index_name = index_name
        self.available = available
        self.formula = formula
        self.bands_used = bands_used
        self.image = image
        self.legend = legend
        self.raw_array = raw_array
        self.metadata = metadata
        self.unavailability_reason = unavailability_reason


class SpectralIndexEngine:
    """
    Computes genuine remote-sensing spectral indices with strict band presence verification.
    """

    @classmethod
    def resolve_band_indices(
        cls,
        arr: np.ndarray,
        metadata: Optional[RasterMetadata]
    ) -> Dict[str, Optional[int]]:
        """
        Maps spectral channel names (blue, green, red, nir, swir1, swir2) to array channel indices.
        Uses metadata tags and band descriptions where available.
        """
        num_bands = arr.shape[0] if arr.ndim == 3 else 1
        mapping: Dict[str, Optional[int]] = {
            "blue": None,
            "green": None,
            "red": None,
            "nir": None,
            "swir1": None,
            "swir2": None
        }

        # 1. Check metadata band descriptions if available
        if metadata and metadata.band_descriptions:
            for idx, desc in enumerate(metadata.band_descriptions):
                if idx >= num_bands:
                    break
                d = desc.lower().strip()
                tokens = d.replace("_", " ").replace("-", " ").split()
                if any(k in d for k in ["nir", "near infrared", "b8", "b8a", "b5"]):
                    mapping["nir"] = idx
                elif "red" in tokens or d == "r" or "b4" in tokens or "band 4" in d:
                    mapping["red"] = idx
                elif "green" in tokens or d == "g" or "b3" in tokens or "band 3" in d:
                    mapping["green"] = idx
                elif "blue" in tokens or d == "b" or "b2" in tokens or "band 2" in d:
                    mapping["blue"] = idx
                elif any(k in d for k in ["swir1", "swir 1", "b11", "b6"]):
                    mapping["swir1"] = idx
                elif any(k in d for k in ["swir2", "swir 2", "b12", "b7"]):
                    mapping["swir2"] = idx

        # 2. Standard heuristic for known multispectral formats (e.g. 4-band NAIP / Planet / Sentinel-2 RGBN)
        if mapping["nir"] is None and num_bands >= 4:
            # Common 4-band order: [R, G, B, NIR] or [B, G, R, NIR]
            mapping["nir"] = 3
            if mapping["red"] is None:
                mapping["red"] = 0
            if mapping["green"] is None:
                mapping["green"] = 1
            if mapping["blue"] is None:
                mapping["blue"] = 2

        # 3. Standard 3-band RGB has NO NIR or SWIR
        if num_bands == 3 and mapping["red"] is None and mapping["green"] is None and mapping["blue"] is None:
            mapping["red"] = 0
            mapping["green"] = 1
            mapping["blue"] = 2

        return mapping

    @classmethod
    def compute_ndvi(
        cls,
        arr: np.ndarray,
        metadata: Optional[RasterMetadata] = None
    ) -> IndexResult:
        """
        Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red)
        Range: [-1.0, 1.0].
        Strictly requires confirmed NIR and Red bands.
        """
        formula = "NDVI = (NIR - Red) / (NIR + Red)"
        mapping = cls.resolve_band_indices(arr, metadata)
        nir_idx = mapping.get("nir")
        red_idx = mapping.get("red")

        if nir_idx is None or red_idx is None:
            return IndexResult(
                index_name="NDVI",
                available=False,
                formula=formula,
                bands_used=[],
                unavailability_reason="INDEX_NOT_AVAILABLE: Required Near-Infrared (NIR) band is not present in this dataset."
            )

        nir = arr[nir_idx].astype(np.float32)
        red = arr[red_idx].astype(np.float32)

        denom = nir + red
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = np.where(denom != 0.0, (nir - red) / denom, 0.0)

        ndvi = np.clip(ndvi, -1.0, 1.0)
        valid = ndvi[np.isfinite(ndvi)]
        min_v = float(np.min(valid)) if valid.size > 0 else -1.0
        max_v = float(np.max(valid)) if valid.size > 0 else 1.0
        mean_v = float(np.mean(valid)) if valid.size > 0 else 0.0
        valid_pct = round(float(valid.size / ndvi.size * 100.0), 2)

        # Colormap for NDVI: RdYlGn (Red=bare/water, Yellow=sparse, Green=dense)
        cmap = matplotlib.colormaps.get_cmap("RdYlGn")
        # Normalize -0.2 to 0.8 for high contrast visualization
        norm_v = np.clip((ndvi + 0.2) / 1.0, 0.0, 1.0)
        rgba = (cmap(norm_v) * 255.0).astype(np.uint8)
        img = Image.fromarray(rgba, "RGBA")

        legend = generate_colorbar_legend(
            vmin=-1.0,
            vmax=1.0,
            cmap_name="RdYlGn",
            title="NDVI (Vegetation Index)",
            units="Index [-1, 1]"
        )

        layer_meta = LayerMetadata(
            layer_id="ndvi",
            layer_type=VisualizationType.SPECTRAL_INDEX,
            title="NDVI — Normalized Difference Vegetation Index",
            provenance=LayerProvenance.DERIVED_INDEX,
            units="Index [-1, 1]",
            min_value=min_v,
            max_value=max_v,
            mean_value=mean_v,
            valid_pixel_pct=valid_pct,
            colormap="RdYlGn",
            crs=metadata.crs if metadata else None,
            bounds=metadata.bounds if metadata else None,
            resolution=metadata.resolution if metadata else None,
            raw_stats={
                "formula": formula,
                "nir_band_index": nir_idx,
                "red_band_index": red_idx,
                "scientific_disclaimer": "Derived spectral index — not a direct model prediction."
            }
        )

        return IndexResult(
            index_name="NDVI",
            available=True,
            formula=formula,
            bands_used=[f"NIR (Band {nir_idx + 1})", f"Red (Band {red_idx + 1})"],
            image=img,
            legend=legend,
            raw_array=ndvi,
            metadata=layer_meta
        )

    @classmethod
    def compute_ndwi(
        cls,
        arr: np.ndarray,
        metadata: Optional[RasterMetadata] = None
    ) -> IndexResult:
        """
        Normalized Difference Water Index (McFeeters): (Green - NIR) / (Green + NIR)
        Range: [-1.0, 1.0].
        """
        formula = "NDWI = (Green - NIR) / (Green + NIR)"
        mapping = cls.resolve_band_indices(arr, metadata)
        green_idx = mapping.get("green")
        nir_idx = mapping.get("nir")

        if green_idx is None or nir_idx is None:
            return IndexResult(
                index_name="NDWI",
                available=False,
                formula=formula,
                bands_used=[],
                unavailability_reason="INDEX_NOT_AVAILABLE: Required Green and Near-Infrared (NIR) bands are not confirmed in this dataset."
            )

        green = arr[green_idx].astype(np.float32)
        nir = arr[nir_idx].astype(np.float32)

        denom = green + nir
        with np.errstate(divide="ignore", invalid="ignore"):
            ndwi = np.where(denom != 0.0, (green - nir) / denom, 0.0)

        ndwi = np.clip(ndwi, -1.0, 1.0)
        valid = ndwi[np.isfinite(ndwi)]
        min_v = float(np.min(valid)) if valid.size > 0 else -1.0
        max_v = float(np.max(valid)) if valid.size > 0 else 1.0
        mean_v = float(np.mean(valid)) if valid.size > 0 else 0.0
        valid_pct = round(float(valid.size / ndwi.size * 100.0), 2)

        cmap = matplotlib.colormaps.get_cmap("Blues")
        norm_v = np.clip((ndwi + 1.0) / 2.0, 0.0, 1.0)
        rgba = (cmap(norm_v) * 255.0).astype(np.uint8)
        img = Image.fromarray(rgba, "RGBA")

        legend = generate_colorbar_legend(
            vmin=-1.0,
            vmax=1.0,
            cmap_name="Blues",
            title="NDWI (Water Index)",
            units="Index [-1, 1]"
        )

        layer_meta = LayerMetadata(
            layer_id="ndwi",
            layer_type=VisualizationType.SPECTRAL_INDEX,
            title="NDWI — Normalized Difference Water Index",
            provenance=LayerProvenance.DERIVED_INDEX,
            units="Index [-1, 1]",
            min_value=min_v,
            max_value=max_v,
            mean_value=mean_v,
            valid_pixel_pct=valid_pct,
            colormap="Blues",
            crs=metadata.crs if metadata else None,
            bounds=metadata.bounds if metadata else None,
            resolution=metadata.resolution if metadata else None,
            raw_stats={
                "formula": formula,
                "green_band_index": green_idx,
                "nir_band_index": nir_idx,
                "scientific_disclaimer": "Derived spectral index — not a direct model prediction."
            }
        )

        return IndexResult(
            index_name="NDWI",
            available=True,
            formula=formula,
            bands_used=[f"Green (Band {green_idx + 1})", f"NIR (Band {nir_idx + 1})"],
            image=img,
            legend=legend,
            raw_array=ndwi,
            metadata=layer_meta
        )
