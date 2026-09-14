import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

try:
    from shapely.geometry import shape, mapping, Polygon, MultiPolygon
    from shapely.ops import transform as shapely_transform
except ImportError:
    shape, mapping, Polygon, MultiPolygon, shapely_transform = None, None, None, None, None

try:
    import pyproj
except ImportError:
    pyproj = None

try:
    import rasterio.features
    from rasterio.transform import Affine
except ImportError:
    rasterio = None

from backend.app.geo.metadata import RasterMetadata
from backend.app.logging import logger


def mask_to_geojson(
    binary_mask: np.ndarray,
    metadata: Optional[RasterMetadata] = None,
    min_area_pixels: int = 16,
    simplify_tolerance: float = 1.0,
    target_crs: str = "EPSG:4326"
) -> Dict[str, Any]:
    """
    Converts a 2D binary numpy mask (0 and 1) into a valid GeoJSON FeatureCollection.
    Reprojects coordinates to EPSG:4326 for interactive web map rendering.
    Supports Shapely/Rasterio when available, with pure-Python connected component fallback.
    """
    if binary_mask.ndim > 2:
        binary_mask = np.squeeze(binary_mask)

    h, w = binary_mask.shape
    uint8_mask = (binary_mask > 0).astype(np.uint8)
    features: List[Dict[str, Any]] = []

    # Path A: rasterio & shapely available
    if rasterio is not None and shape is not None and metadata and metadata.transform:
        aff = Affine(*metadata.transform[:6])
        shapes_gen = rasterio.features.shapes(uint8_mask, mask=(uint8_mask == 1), transform=aff)
        
        transformer = None
        if pyproj is not None and metadata.crs and metadata.crs != target_crs:
            try:
                src_p = pyproj.CRS.from_user_input(metadata.crs)
                dst_p = pyproj.CRS.from_user_input(target_crs)
                transformer = pyproj.Transformer.from_crs(src_p, dst_p, always_xy=True).transform
            except Exception as e:
                logger.warning(f"Could not initialize CRS transformer ({metadata.crs} -> {target_crs}): {e}")

        for geom_dict, val in shapes_gen:
            if val == 1:
                geom = shape(geom_dict)
                pixel_scale = abs(metadata.resolution[0] * metadata.resolution[1]) if metadata.resolution else 1.0
                if geom.area < (min_area_pixels * pixel_scale):
                    continue
                if simplify_tolerance > 0:
                    geom = geom.simplify(simplify_tolerance, preserve_topology=True)
                if transformer is not None and shapely_transform is not None:
                    geom = shapely_transform(transformer, geom)

                features.append({
                    "type": "Feature",
                    "geometry": mapping(geom),
                    "properties": {
                        "class": "detected_object",
                        "value": 1,
                        "source_crs": metadata.crs if (metadata and metadata.is_georeferenced) else None,
                        "target_crs": target_crs if (metadata and metadata.is_georeferenced) else "image_coordinates",
                        "coordinate_space": "geographic" if (metadata and metadata.is_georeferenced) else "image_coordinates"
                    }
                })
    else:
        # Path B (no rasterio): real contour polygons with holes via OpenCV, mapped through the
        # raster's affine transform and reprojected. Previously each component was reduced to its
        # bounding rectangle, which misstated shape and area (project/qna.md Q-009).
        import cv2

        geo = bool(metadata and metadata.is_georeferenced and (metadata.transform or metadata.bounds))
        transformer = None
        if geo and pyproj is not None and metadata.crs and metadata.crs.upper() != target_crs:
            try:
                transformer = pyproj.Transformer.from_crs(
                    pyproj.CRS.from_user_input(metadata.crs), pyproj.CRS.from_user_input(target_crs), always_xy=True
                ).transform
            except Exception as e:
                logger.warning(f"Could not initialize CRS transformer in Path B ({metadata.crs} -> {target_crs}): {e}")

        if geo and metadata.transform:
            a, b, c, d, e, f = metadata.transform[:6]
        elif geo:
            gb = metadata.bounds
            a, b, c, d, e, f = (gb[2] - gb[0]) / w, 0.0, gb[0], 0.0, -(gb[3] - gb[1]) / h, gb[3]

        def to_output(pts: np.ndarray) -> List[List[float]]:
            # OpenCV contour vertices are pixel indices; +0.5 places them at pixel centres.
            cols = pts[:, 0].astype(float) + 0.5
            rows = pts[:, 1].astype(float) + 0.5
            if not geo:
                ring = np.stack([cols, rows], axis=1)
            else:
                xs = a * cols + b * rows + c
                ys = d * cols + e * rows + f
                if transformer is not None:
                    xs, ys = transformer(xs, ys)
                ring = np.stack([np.asarray(xs, float), np.asarray(ys, float)], axis=1)
            ring = ring.tolist()
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
            return ring

        contours, hierarchy = cv2.findContours(uint8_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        hierarchy = hierarchy[0] if hierarchy is not None else []
        for i, cnt in enumerate(contours):
            if hierarchy[i][3] != -1:
                continue  # holes are attached to their parent below
            holes = []
            child = hierarchy[i][2]
            while child != -1:
                holes.append(contours[child])
                child = hierarchy[child][0]

            # Holes are already 0 in the mask, so filling the outer ring and intersecting counts exactly
            # this component's pixels. Areas are reported from pixel counts (statistics.py), not from
            # the polygon, whose vertices sit on pixel centres and so trace ~half a pixel inside.
            fill = np.zeros_like(uint8_mask)
            cv2.drawContours(fill, [cnt], -1, 1, thickness=cv2.FILLED)
            pix_count = int(np.sum(fill & uint8_mask))
            if pix_count < min_area_pixels:
                continue

            rings = []
            for ring_pts in [cnt] + holes:
                approx = cv2.approxPolyDP(ring_pts, simplify_tolerance, True) if simplify_tolerance > 0 else ring_pts
                pts = approx.reshape(-1, 2)
                if len(pts) < 3:
                    pts = ring_pts.reshape(-1, 2)
                if len(pts) >= 3:
                    rings.append(to_output(pts))
            if not rings:
                continue

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": rings
                },
                "properties": {
                    "class": "detected_object",
                    "pixel_count": pix_count,
                    "holes": len(rings) - 1,
                    "source_crs": metadata.crs if geo else None,
                    "target_crs": target_crs if geo else "image_coordinates",
                    "coordinate_space": "geographic" if geo else "image_coordinates"
                }
            })

    geojson_doc = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84" if (metadata and metadata.is_georeferenced) else "image_coordinates",
                "source_crs": metadata.crs if (metadata and metadata.is_georeferenced) else None,
                "target_crs": "EPSG:4326" if (metadata and metadata.is_georeferenced) else "image_coordinates"
            }
        },
        "features": features
    }
    return geojson_doc


def save_geojson(geojson_data: Dict[str, Any], output_path: str | Path) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)
    return out
