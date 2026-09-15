"""
SatQuery AI — GeoJSON area-of-interest (AOI) input.

Parses a GeoJSON AOI, reprojects it into the raster's CRS, and rasterises it to a pixel mask so
analysis results (change masks, segmentation masks, detections) can be restricted to — and areas
reported for — the region the user actually asked about.

CRS handling follows RFC 7946: GeoJSON coordinates are WGS84 lon/lat (EPSG:4326) unless a legacy
`crs` member names another CRS (pre-2016 GeoJSON, still produced by QGIS/GDAL exports).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import pyproj
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import transform as shp_transform, unary_union

from backend.app.exceptions import SatQueryException
from backend.app.geo.metadata import RasterMetadata


class AOIError(SatQueryException):
    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code, details=details, status_code=422)


@dataclass
class AOI:
    geometry: Union[Polygon, MultiPolygon]  # in `crs`
    crs: str
    feature_count: int


@dataclass
class RasterizedAOI:
    mask: np.ndarray            # bool (H, W), True inside the AOI
    pixel_count: int
    aoi_area_sq_m: float        # full AOI area, including any part outside the raster
    inside_area_sq_m: float     # area of the AOI that falls within the raster footprint
    coverage_of_aoi: float      # inside / full, 0-1
    raster_crs: str

    def summary(self) -> Dict[str, Any]:
        return {
            "aoi_pixel_count": self.pixel_count,
            "aoi_area_sq_m": round(self.aoi_area_sq_m, 2),
            "aoi_area_sq_km": round(self.aoi_area_sq_m / 1e6, 6),
            "aoi_inside_raster_sq_m": round(self.inside_area_sq_m, 2),
            "aoi_coverage_within_raster": round(self.coverage_of_aoi, 4),
            "raster_crs": self.raster_crs,
        }


def _crs_from_member(doc: Dict[str, Any]) -> str:
    name = ((doc.get("crs") or {}).get("properties") or {}).get("name")
    if not name:
        return "EPSG:4326"
    name = str(name)
    if name.upper().endswith("CRS84"):
        return "EPSG:4326"
    try:
        epsg = pyproj.CRS.from_user_input(name).to_epsg()
    except pyproj.exceptions.CRSError as e:
        raise AOIError(f"Unrecognised GeoJSON crs member '{name}'.", "AOI_INVALID", {"crs": name}) from e
    return f"EPSG:{epsg}" if epsg else name


def load_aoi(source: Union[Dict[str, Any], str, Path]) -> AOI:
    """Accepts a GeoJSON dict, a JSON string, or a path to a .geojson file."""
    if isinstance(source, Path) or (isinstance(source, str) and not source.lstrip().startswith("{")):
        try:
            doc = json.loads(Path(source).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise AOIError(f"Could not read AOI GeoJSON: {e}", "AOI_INVALID") from e
    elif isinstance(source, str):
        try:
            doc = json.loads(source)
        except json.JSONDecodeError as e:
            raise AOIError(f"AOI is not valid JSON: {e}", "AOI_INVALID") from e
    else:
        doc = source
    if not isinstance(doc, dict) or "type" not in doc:
        raise AOIError("AOI must be a GeoJSON object with a 'type'.", "AOI_INVALID")

    kind = doc["type"]
    if kind == "FeatureCollection":
        geoms = [f.get("geometry") for f in doc.get("features", []) if f and f.get("geometry")]
    elif kind == "Feature":
        geoms = [doc.get("geometry")] if doc.get("geometry") else []
    else:
        geoms = [doc]

    polys: List[Union[Polygon, MultiPolygon]] = []
    for g in geoms:
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        try:
            geom = shape(g)
        except Exception as e:
            raise AOIError(f"Invalid AOI geometry: {e}", "AOI_INVALID") from e
        if not geom.is_valid:
            geom = geom.buffer(0)
        if not geom.is_empty:
            polys.append(geom)
    if not polys:
        raise AOIError("AOI contains no Polygon or MultiPolygon geometry.", "AOI_INVALID", {"type": kind})

    return AOI(geometry=unary_union(polys), crs=_crs_from_member(doc), feature_count=len(polys))


def _area_sq_m(geom, crs: str) -> float:
    c = pyproj.CRS.from_user_input(crs)
    if c.is_geographic:
        return float(abs(pyproj.Geod(ellps="WGS84").geometry_area_perimeter(geom)[0]))
    return float(geom.area)


def _scanline_fill(rings: List[np.ndarray], h: int, w: int) -> np.ndarray:
    """
    Exact centre-sampling rasteriser: pixel (row r, col c) is inside iff its centre (c + 0.5, r + 0.5)
    is inside the polygon under the even-odd rule over all rings (so holes and multipolygons need no
    special case). Edges are half-open, so a polygon edge on a pixel boundary never claims the pixel
    on both sides. cv2.fillPoly was tried first and rejected: it fills every pixel an edge touches, so
    a 200x200-pixel AOI rasterised to 201x201 (tests/unit/test_aoi.py).
    """
    edges = []
    for ring in rings:
        pts = np.asarray(ring, float)
        a, b = pts, np.roll(pts, -1, axis=0)
        keep = a[:, 1] != b[:, 1]  # horizontal edges never cross a scanline
        edges.append(np.concatenate([a[keep], b[keep]], axis=1))
    mask = np.zeros((h, w), dtype=bool)
    if not edges:
        return mask
    e = np.concatenate(edges)
    x0, y0, x1, y1 = e[:, 0], e[:, 1], e[:, 2], e[:, 3]
    ylo, yhi = np.minimum(y0, y1), np.maximum(y0, y1)
    r_start = max(0, int(np.floor(ylo.min() - 0.5)))
    r_stop = min(h, int(np.ceil(yhi.max() + 0.5)) + 1)
    for r in range(r_start, r_stop):
        yc = r + 0.5
        hit = (ylo <= yc) & (yc < yhi)
        if not hit.any():
            continue
        xs = np.sort(x0[hit] + (yc - y0[hit]) * (x1[hit] - x0[hit]) / (y1[hit] - y0[hit]))
        for xa, xb in zip(xs[0::2], xs[1::2]):
            c0 = max(0, int(np.ceil(xa - 0.5)))
            c1 = min(w, int(np.ceil(xb - 0.5)))
            if c1 > c0:
                mask[r, c0:c1] = True
    return mask


def rasterize_aoi(aoi: AOI, metadata: Optional[RasterMetadata]) -> RasterizedAOI:
    """Mask of raster pixels whose centres fall inside the AOI."""
    if metadata is None or not metadata.is_georeferenced or not metadata.transform or not metadata.crs:
        raise AOIError(
            "A GeoJSON AOI needs a georeferenced raster (GeoTIFF with a CRS); this image has no map coordinates.",
            "AOI_REQUIRES_GEOREFERENCED_RASTER",
            {"filename": getattr(metadata, "filename", None)},
        )

    to_raster = pyproj.Transformer.from_crs(aoi.crs, metadata.crs, always_xy=True).transform
    geom = shp_transform(to_raster, aoi.geometry)

    a, b, c, d, e, f = [float(v) for v in metadata.transform[:6]]
    det = a * e - b * d
    if det == 0:
        raise AOIError("Raster transform is singular.", "AOI_REQUIRES_GEOREFERENCED_RASTER")

    def world_to_pixel(xs, ys):
        xs, ys = np.asarray(xs, float) - c, np.asarray(ys, float) - f
        col = (e * xs - b * ys) / det
        row = (-d * xs + a * ys) / det
        return col, row

    h, w = metadata.height, metadata.width
    rings = []
    for poly in (list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]):
        for ring in [poly.exterior] + list(poly.interiors):
            col, row = world_to_pixel(*ring.xy)
            rings.append(np.stack([col, row], axis=1))
    inside = _scanline_fill(rings, h, w)
    n = int(inside.sum())

    footprint = Polygon([(metadata.bounds[0], metadata.bounds[1]), (metadata.bounds[2], metadata.bounds[1]),
                         (metadata.bounds[2], metadata.bounds[3]), (metadata.bounds[0], metadata.bounds[3])])
    full = _area_sq_m(geom, metadata.crs)
    within = _area_sq_m(geom.intersection(footprint), metadata.crs)
    if n == 0:
        raise AOIError(
            "The AOI does not overlap the raster.",
            "AOI_OUTSIDE_RASTER",
            {"aoi_bounds_in_raster_crs": list(geom.bounds), "raster_bounds": metadata.bounds, "raster_crs": metadata.crs},
        )
    return RasterizedAOI(mask=inside, pixel_count=n, aoi_area_sq_m=full, inside_area_sq_m=within,
                         coverage_of_aoi=within / full if full > 0 else 0.0, raster_crs=metadata.crs)


def resolve_request_aoi(parameters: Dict[str, Any], input_dir: Optional[Path] = None) -> Optional[AOI]:
    """AOI from request parameters: inline `aoi_geojson`, or `aoi_filename` stored in the job input dir."""
    if parameters.get("aoi_geojson"):
        return load_aoi(parameters["aoi_geojson"])
    if parameters.get("aoi_filename") and input_dir is not None:
        p = input_dir / Path(str(parameters["aoi_filename"])).name
        if not p.is_file():
            raise AOIError(f"AOI file '{p.name}' not found in the job workspace.", "AOI_INVALID")
        return load_aoi(p)
    return None


def aoi_bbox_ratio(box: List[float], aoi_mask: np.ndarray) -> Tuple[bool, float]:
    """(centre inside AOI, fraction of box pixels inside AOI) for a pixel-space [x1, y1, x2, y2] box."""
    h, w = aoi_mask.shape
    x1, y1, x2, y2 = [int(round(v)) for v in box[:4]]
    x1, x2 = max(0, min(w, x1)), max(0, min(w, x2))
    y1, y2 = max(0, min(h, y1)), max(0, min(h, y2))
    cx, cy = min(w - 1, max(0, (x1 + x2) // 2)), min(h - 1, max(0, (y1 + y2) // 2))
    sub = aoi_mask[y1:y2, x1:x2]
    return bool(aoi_mask[cy, cx]), float(sub.mean()) if sub.size else 0.0


def draw_aoi_outline(image: "Image.Image", aoi_mask: np.ndarray, color: Tuple[int, int, int] = (255, 214, 0), width: int = 2):
    """Draws the AOI boundary on a PIL image of the same pixel grid as the mask."""
    from PIL import Image

    arr = np.array(image.convert("RGB"))
    contours, _ = cv2.findContours(aoi_mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(arr, contours, -1, color, width)
    return Image.fromarray(arr)
