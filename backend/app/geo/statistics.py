from typing import Optional
import numpy as np
import pyproj
from backend.app.geo.metadata import RasterMetadata
from backend.app.schemas.evidence import AreaStatistics
from backend.app.logging import logger


def calculate_area_statistics(
    binary_mask: np.ndarray,
    metadata: Optional[RasterMetadata] = None,
    nodata_mask: Optional[np.ndarray] = None
) -> AreaStatistics:
    """
    Computes exact pixel counts and metric ground area (m^2 and km^2) from a binary change/segmentation mask.
    Strictly uses metric projected CRS or UTM calculations; NEVER naively multiplies geographic degrees.
    """
    if binary_mask.ndim > 2:
        binary_mask = np.squeeze(binary_mask)

    h, w = binary_mask.shape
    total_pixels = h * w

    if nodata_mask is not None:
        valid_pixels = int(np.sum(~nodata_mask))
        changed_pixels = int(np.sum((binary_mask > 0) & (~nodata_mask)))
    else:
        valid_pixels = total_pixels
        changed_pixels = int(np.sum(binary_mask > 0))

    ratio = (changed_pixels / valid_pixels) if valid_pixels > 0 else 0.0

    area_sq_m: Optional[float] = None
    area_sq_km: Optional[float] = None
    metric_crs: Optional[str] = None

    if metadata and metadata.is_georeferenced and metadata.resolution:
        rx, ry = abs(metadata.resolution[0]), abs(metadata.resolution[1])
        crs_str = metadata.crs or ""

        # Check if CRS is already projected in linear metric units (e.g. UTM, WebMercator, EqualArea)
        try:
            crs_obj = pyproj.CRS.from_user_input(crs_str)
            if crs_obj.is_projected:
                # Pixel area in meters^2
                pixel_area_m2 = rx * ry
                area_sq_m = changed_pixels * pixel_area_m2
                area_sq_km = area_sq_m / 1e6
                metric_crs = crs_str
            else:
                # Geographic CRS (e.g. EPSG:4326 in degrees) -> compute geodesic ground resolution at scene center
                if metadata.bounds:
                    center_lat = (metadata.bounds[1] + metadata.bounds[3]) / 2.0
                    # 1 deg lat ~ 111,320 m; 1 deg lon ~ 111,320 * cos(lat) m
                    m_per_deg_lat = 111320.0
                    m_per_deg_lon = 111320.0 * np.cos(np.radians(center_lat))
                    pixel_area_m2 = (rx * m_per_deg_lon) * (ry * m_per_deg_lat)
                    area_sq_m = changed_pixels * pixel_area_m2
                    area_sq_km = area_sq_m / 1e6
                    metric_crs = f"Geodesic (approx centered at {center_lat:.2f}N)"
        except Exception as e:
            logger.warning(f"Could not parse CRS for area calculation ({crs_str}): {e}")

    return AreaStatistics(
        changed_pixels=changed_pixels,
        total_valid_pixels=valid_pixels,
        change_ratio=round(ratio, 6),
        estimated_area_sq_m=round(area_sq_m, 2) if area_sq_m is not None else None,
        estimated_area_sq_km=round(area_sq_km, 4) if area_sq_km is not None else None,
        area_unit="sq_meters",
        metric_crs=metric_crs
    )
