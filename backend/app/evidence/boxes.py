from typing import Any, Dict, List, Optional
from backend.app.schemas.evidence import BoundingBoxEvidence
from backend.app.geo.metadata import RasterMetadata


def normalize_box(
    box: List[float],
    img_width: int,
    img_height: int,
    label: str = "detected_object",
    score: Optional[float] = None,
    metadata: Optional[RasterMetadata] = None
) -> BoundingBoxEvidence:
    """
    Normalizes 2D bounding boxes into [ymin, xmin, ymax, xmax] format in [0, 1] relative coordinates.
    For georeferenced rasters:
      - transforms image-space box into geographic bounds in EPSG:4326;
      - preserves source CRS metadata;
      - sets coordinate_space to 'geographic'.
    For non-georeferenced benchmark imagery (PNG/JPEG):
      - keeps evidence strictly in image coordinates;
      - sets geo_bounds to None;
      - sets coordinate_space to 'image_coordinates';
      - never assumes pixel coordinates are geographic coordinates.
    """
    if len(box) == 4:
        # Standardize relative [ymin, xmin, ymax, xmax]
        if max(box) > 1.0:  # Absolute pixel coords [x1, y1, x2, y2]
            b_ymin = max(0.0, min(1.0, float(box[1]) / float(img_height)))
            b_xmin = max(0.0, min(1.0, float(box[0]) / float(img_width)))
            b_ymax = max(0.0, min(1.0, float(box[3]) / float(img_height)))
            b_xmax = max(0.0, min(1.0, float(box[2]) / float(img_width)))
        else:
            b_ymin, b_xmin, b_ymax, b_xmax = float(box[0]), float(box[1]), float(box[2]), float(box[3])
    else:
        b_ymin, b_xmin, b_ymax, b_xmax = 0.0, 0.0, 1.0, 1.0

    geo_bounds = None
    source_crs = None
    target_crs = None
    coord_space = "image_coordinates"

    # Transform to map coordinates ONLY if authentic georeferencing is present
    if metadata and metadata.is_georeferenced and metadata.bounds:
        gb = metadata.bounds  # [minx, miny, maxx, maxy] in source CRS
        geo_minx = gb[0] + b_xmin * (gb[2] - gb[0])
        geo_maxx = gb[0] + b_xmax * (gb[2] - gb[0])
        geo_miny = gb[1] + (1.0 - b_ymax) * (gb[3] - gb[1])
        geo_maxy = gb[1] + (1.0 - b_ymin) * (gb[3] - gb[1])
        source_crs = metadata.crs
        coord_space = "geographic"

        # Transform to EPSG:4326 if source CRS is different
        if source_crs and source_crs.upper() != "EPSG:4326":
            try:
                import pyproj
                transformer = pyproj.Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
                lon_min, lat_min = transformer.transform(geo_minx, geo_miny)
                lon_max, lat_max = transformer.transform(geo_maxx, geo_maxy)
                geo_bounds = [
                    min(lon_min, lon_max),
                    min(lat_min, lat_max),
                    max(lon_min, lon_max),
                    max(lat_min, lat_max)
                ]
                target_crs = "EPSG:4326"
            except Exception:
                geo_bounds = [geo_minx, geo_miny, geo_maxx, geo_maxy]
                target_crs = source_crs
        else:
            geo_bounds = [geo_minx, geo_miny, geo_maxx, geo_maxy]
            target_crs = "EPSG:4326"

    return BoundingBoxEvidence(
        label=label,
        box_2d=[round(b_ymin, 4), round(b_xmin, 4), round(b_ymax, 4), round(b_xmax, 4)],
        score=round(score, 4) if score is not None else None,
        geo_bounds=[round(g, 6) for g in geo_bounds] if geo_bounds else None,
        source_crs=source_crs,
        target_crs=target_crs,
        coordinate_space=coord_space
    )
