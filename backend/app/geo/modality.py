import re
from typing import Dict, Any, Optional, Tuple
from backend.app.geo.metadata import RasterMetadata


class ModalityDetector:
    """
    Robust priority-based modality detector for remote sensing data.
    Evaluates:
      1. Explicit user/metadata declaration
      2. GeoTIFF band descriptions and tags
      3. Sensor and platform metadata
      4. Filename naming conventions
      5. Band statistical characteristics
      6. Fallback to 'unknown'
    Never overconfidently classifies optical vs SAR from band count alone.
    """
    SAR_SENSORS = ["sentinel-1", "s1", "terrasar", "terrasar-x", "cosmo-skymed", "radarsat", "alos-palsar", "palsar", "iceye", "capella"]
    OPTICAL_SENSORS = ["sentinel-2", "s2", "landsat", "landsat-8", "landsat-9", "planetscope", "worldview", "spot", "naip", "gaofen"]
    
    SAR_POLARIZATIONS = ["vv", "vh", "hh", "hv", "sigma0", "gamma0", "beta0", "amplitude", "intensity"]
    OPTICAL_BANDS = ["red", "green", "blue", "rgb", "nir", "swir", "coastal", "panchromatic", "b01", "b02", "b03", "b04", "b08", "b11", "b12"]

    @classmethod
    def detect(cls, metadata: RasterMetadata, user_override: Optional[str] = None) -> Tuple[str, float, str]:
        """
        Returns (modality, confidence, reason)
        Modality can be: 'optical', 'multispectral', 'sar', or 'unknown'.
        """
        # 1. User Override
        if user_override and user_override.lower() in ["optical", "multispectral", "sar", "unknown"]:
            return user_override.lower(), 1.0, f"Explicitly specified by user as '{user_override}'."

        # 2. Band descriptions & metadata tags
        band_desc_str = " ".join(metadata.band_descriptions).lower()
        tags_str = " ".join([f"{k}:{v}" for k, v in metadata.tags.items()]).lower()

        # Check for SAR indicators in tags or descriptions
        for pol in cls.SAR_POLARIZATIONS:
            if re.search(rf"\b{pol}\b", band_desc_str) or re.search(rf"\b{pol}\b", tags_str):
                return "sar", 0.95, f"Detected SAR polarization/indicator '{pol}' in band descriptions or metadata tags."

        # Check for Optical indicators in tags or descriptions
        optical_hits = [b for b in cls.OPTICAL_BANDS if re.search(rf"\b{b}\b", band_desc_str) or re.search(rf"\b{b}\b", tags_str)]
        if optical_hits:
            if len(optical_hits) >= 4 or metadata.bands > 3:
                return "multispectral", 0.90, f"Detected multispectral band markers {optical_hits} in metadata."
            return "optical", 0.90, f"Detected optical band markers {optical_hits} in metadata."

        # 3. Sensor / Platform Metadata
        sensor_text = f"{metadata.sensor or ''} {metadata.platform or ''}".lower()
        for s in cls.SAR_SENSORS:
            if s in sensor_text:
                return "sar", 0.95, f"Sensor/Platform metadata identified SAR instrument '{s}'."
        for o in cls.OPTICAL_SENSORS:
            if o in sensor_text:
                if metadata.bands > 3:
                    return "multispectral", 0.92, f"Sensor/Platform metadata identified optical/multispectral instrument '{o}'."
                return "optical", 0.92, f"Sensor/Platform metadata identified optical instrument '{o}'."

        # 4. Filename Conventions
        filename_lower = metadata.filename.lower()
        # SAR filename patterns (e.g. S1A_IW_GRDH, SAR_*, *_VV_*, etc.)
        if any(p in filename_lower for p in ["_vv", "_vh", "_hh", "_hv", "s1a", "s1b", "grd", "slc", "sar"]):
            return "sar", 0.85, f"Filename '{metadata.filename}' matched known SAR naming convention."
        
        # Optical filename patterns (e.g. S2A_MSIL2A, LC08_L1TP, *_RGB, *_NIR, etc.)
        if any(p in filename_lower for p in ["s2a", "s2b", "msi", "lc08", "lc09", "rgb", "optical", "naip"]):
            if metadata.bands > 3:
                return "multispectral", 0.85, f"Filename '{metadata.filename}' matched known multispectral naming convention."
            return "optical", 0.85, f"Filename '{metadata.filename}' matched known optical naming convention."

        # 5. Band characteristics heuristic (conservative)
        if metadata.format in ["PNG", "JPEG", "JPG"] and metadata.bands in [3, 4]:
            return "optical", 0.70, f"Standard {metadata.bands}-channel visual benchmark image format."

        # 6. Fallback to unknown
        return (
            "unknown",
            0.0,
            f"Insufficient metadata to distinguish modality for {metadata.bands}-band file '{metadata.filename}'."
        )
