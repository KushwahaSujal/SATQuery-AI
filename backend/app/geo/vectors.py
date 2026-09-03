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
        # Path B: Scipy/Pure Python connected component polygon fallback
        from scipy import ndimage
        labeled, num_features = ndimage.label(uint8_mask)

        transformer = None
        if pyproj is not None and metadata and metadata.is_georeferenced and metadata.crs and metadata.crs.upper() != target_crs:
            try:
                src_p = pyproj.CRS.from_user_input(metadata.crs)
                dst_p = pyproj.CRS.from_user_input(target_crs)
                transformer = pyproj.Transformer.from_crs(src_p, dst_p, always_xy=True).transform
            except Exception as e:
                logger.warning(f"Could not initialize CRS transformer in Path B ({metadata.crs} -> {target_crs}): {e}")

        for idx in range(1, num_features + 1):
            comp_mask = (labeled == idx)
            pix_count = np.sum(comp_mask)
            if pix_count < min_area_pixels:
                continue

            ys, xs = np.where(comp_mask)
            min_y, max_y = float(np.min(ys)), float(np.max(ys))
            min_x, max_x = float(np.min(xs)), float(np.max(xs))

            # If georeferenced metadata exists, map to geographic coords in EPSG:4326
            if metadata and metadata.is_georeferenced and metadata.bounds:
                gb = metadata.bounds  # [minx, miny, maxx, maxy] in source CRS
                geo_minx = gb[0] + (min_x / w) * (gb[2] - gb[0])
                geo_maxx = gb[0] + (max_x / w) * (gb[2] - gb[0])
                geo_miny = gb[1] + (1.0 - max_y / h) * (gb[3] - gb[1])
                geo_maxy = gb[1] + (1.0 - min_y / h) * (gb[3] - gb[1])

                if transformer is not None:
                    try:
                        p1_x, p1_y = transformer(geo_minx, geo_miny)
                        p2_x, p2_y = transformer(geo_maxx, geo_miny)
                        p3_x, p3_y = transformer(geo_maxx, geo_maxy)
                        p4_x, p4_y = transformer(geo_minx, geo_maxy)
                        coords = [
                            [
                                [p1_x, p1_y],
                                [p2_x, p2_y],
                                [p3_x, p3_y],
                                [p4_x, p4_y],
                                [p1_x, p1_y]
                            ]
                        ]
                    except Exception:
                        coords = [
                            [
                                [geo_minx, geo_miny],
                                [geo_maxx, geo_miny],
                                [geo_maxx, geo_maxy],
                                [geo_minx, geo_maxy],
                                [geo_minx, geo_miny]
                            ]
                        ]
                else:
                    coords = [
                        [
                            [geo_minx, geo_miny],
                            [geo_maxx, geo_miny],
                            [geo_maxx, geo_maxy],
                            [geo_minx, geo_maxy],
                            [geo_minx, geo_miny]
                        ]
                    ]
            else:
                # Non-georeferenced benchmark PNG/JPEG: strictly keep in image coordinates
                coords = [
                    [
                        [min_x, min_y],
                        [max_x, min_y],
                        [max_x, max_y],
                        [min_x, max_y],
                        [min_x, min_y]
                    ]
                ]

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coords
                },
                "properties": {
                    "class": "detected_object",
                    "pixel_count": int(pix_count),
                    "source_crs": metadata.crs if (metadata and metadata.is_georeferenced) else None,
                    "target_crs": target_crs if (metadata and metadata.is_georeferenced) else "image_coordinates",
                    "coordinate_space": "geographic" if (metadata and metadata.is_georeferenced) else "image_coordinates"
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
