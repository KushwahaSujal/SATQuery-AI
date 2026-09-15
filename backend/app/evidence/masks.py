from pathlib import Path
from typing import Any, Optional
import numpy as np
from PIL import Image

try:
    import tifffile
except ImportError:
    tifffile = None


def save_mask_as_geotiff(
    mask: np.ndarray,
    output_path: str | Path,
    metadata: Optional[Any] = None
) -> Path:
    """
    Saves a 2D change or segmentation mask as a GeoTIFF or standard TIFF.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    uint8_mask = (mask > 0).astype(np.uint8) * 255

    if tifffile is not None:
        tifffile.imwrite(str(out), uint8_mask, extratags=_geotiff_tags(metadata))
    else:
        Image.fromarray(uint8_mask).save(str(out))

    return out


def _geotiff_tags(metadata: Optional[Any]) -> list:
    """
    GeoTIFF tags so a saved mask carries the source raster's CRS and transform (round-trips through
    RasterInspector). Only EPSG CRSs are written; anything else is saved as a plain TIFF.
    """
    if metadata is None or not getattr(metadata, "is_georeferenced", False):
        return []
    crs, tr = getattr(metadata, "crs", None), getattr(metadata, "transform", None)
    if not crs or not tr or not str(crs).upper().startswith("EPSG:"):
        return []
    try:
        import pyproj

        epsg = int(str(crs).split(":")[1])
        geographic = pyproj.CRS.from_epsg(epsg).is_geographic
    except Exception:
        return []
    a, b, c, d, e, f = [float(v) for v in tr[:6]]
    keys = [(1024, 0, 1, 2 if geographic else 1), (1025, 0, 1, 1), (2048 if geographic else 3072, 0, 1, epsg)]
    directory = (1, 1, 0, len(keys)) + tuple(v for k in keys for v in k)
    tags = [(34735, "H", len(directory), directory, False)]
    if b == 0.0 and d == 0.0:
        tags += [(33550, "d", 3, (a, -e, 0.0), False), (33922, "d", 6, (0.0, 0.0, 0.0, c, f, 0.0), False)]
    else:
        tags += [(34264, "d", 16, (a, b, 0.0, c, d, e, 0.0, f, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0), False)]
    return tags
