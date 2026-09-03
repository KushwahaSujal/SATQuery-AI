from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.geo.metadata import RasterMetadata
from backend.app.config import settings


class AlignmentReport(BaseModel):
    crs_compatible: bool = False
    bounds_overlap: bool = False
    overlap_iou: float = 0.0
    resolution_compatible: bool = False
    grid_compatible: bool = False
    co_registered: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


def check_alignment(meta1: RasterMetadata, meta2: RasterMetadata) -> AlignmentReport:
    """
    Detailed geometric compatibility analysis between two rasters.
    Distinguishes CRS compatibility, bounds overlap, resolution ratio,
    transform grid alignment, and overall co-registration status.
    """
    report = AlignmentReport()
    warnings = []

    # 1. Non-georeferenced images (e.g. standard benchmark images)
    if not meta1.is_georeferenced or not meta2.is_georeferenced:
        dim_match = (meta1.width == meta2.width and meta1.height == meta2.height)
        report.crs_compatible = True  # Both in pixel coordinate space
        report.bounds_overlap = True
        report.overlap_iou = 1.0 if dim_match else 0.0
        report.resolution_compatible = dim_match
        report.grid_compatible = dim_match
        report.co_registered = dim_match
        report.details = {
            "coordinate_system": "pixel_space",
            "dimensions_1": [meta1.width, meta1.height],
            "dimensions_2": [meta2.width, meta2.height],
        }
        if not dim_match:
            warnings.append(
                f"Pixel dimensions differ: ({meta1.width}x{meta1.height}) vs ({meta2.width}x{meta2.height})."
            )
        report.warnings = warnings
        return report

    # 2. CRS Compatibility
    crs1 = (meta1.crs or "").strip().upper()
    crs2 = (meta2.crs or "").strip().upper()
    report.crs_compatible = (crs1 == crs2)
    if not report.crs_compatible:
        warnings.append(f"CRS mismatch: '{crs1}' vs '{crs2}'.")

    # 3. Bounds Overlap & Intersection over Union (IOU)
    if meta1.bounds and meta2.bounds:
        b1 = meta1.bounds  # [minx, miny, maxx, maxy]
        b2 = meta2.bounds

        ix_min = max(b1[0], b2[0])
        iy_min = max(b1[1], b2[1])
        ix_max = min(b1[2], b2[2])
        iy_max = min(b1[3], b2[3])

        if ix_max > ix_min and iy_max > iy_min:
            inter_area = (ix_max - ix_min) * (iy_max - iy_min)
            area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
            area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
            union_area = area1 + area2 - inter_area
            iou = inter_area / union_area if union_area > 0 else 0.0
            report.bounds_overlap = True
            report.overlap_iou = round(iou, 4)
        else:
            report.bounds_overlap = False
            report.overlap_iou = 0.0
            warnings.append("Geospatial bounds have zero overlap.")
    else:
        report.bounds_overlap = False
        warnings.append("Missing bounding box information in one or both files.")

    # 4. Resolution Compatibility
    if meta1.resolution and meta2.resolution:
        res1 = meta1.resolution[0]
        res2 = meta2.resolution[0]
        max_diff = settings.geospatial.co_registration.max_resolution_diff_ratio
        if res1 > 0 and res2 > 0:
            diff_ratio = abs(res1 - res2) / max(res1, res2)
            report.resolution_compatible = (diff_ratio <= max_diff)
            if not report.resolution_compatible:
                warnings.append(f"Spatial resolution difference is {diff_ratio*100:.1f}% (threshold {max_diff*100}%).")
    else:
        report.resolution_compatible = (meta1.width == meta2.width and meta1.height == meta2.height)

    # 5. Transform / Grid Alignment
    if meta1.transform and meta2.transform:
        # Check affine origin alignment within tolerance
        t1 = meta1.transform
        t2 = meta2.transform
        origin_diff = abs(t1[0] - t2[0]) + abs(t1[3] - t2[3])
        grid_tol = (meta1.resolution[0] if meta1.resolution else 1.0) * 0.1
        report.grid_compatible = (origin_diff <= grid_tol)
    else:
        report.grid_compatible = (meta1.width == meta2.width and meta1.height == meta2.height)

    # 6. Overall Strict Co-registration Status
    min_iou = settings.geospatial.co_registration.min_bounds_iou
    report.co_registered = (
        report.crs_compatible
        and report.bounds_overlap
        and report.overlap_iou >= min_iou
        and report.resolution_compatible
    )

    report.details = {
        "crs_1": crs1,
        "crs_2": crs2,
        "bounds_1": meta1.bounds,
        "bounds_2": meta2.bounds,
        "resolution_1": meta1.resolution,
        "resolution_2": meta2.resolution,
        "overlap_iou": report.overlap_iou,
    }
    report.warnings = warnings
    return report
