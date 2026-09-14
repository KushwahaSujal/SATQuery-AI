import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image

try:
    import tifffile
except ImportError:
    tifffile = None

try:
    import rasterio
    from rasterio.crs import CRS
except ImportError:
    rasterio = None

from backend.app.geo.metadata import RasterMetadata
from backend.app.exceptions import UnsupportedFormatError, InvalidInputError
from backend.app.logging import logger


class RasterInspector:
    """
    Unified raster inspection supporting GeoTIFF, multi-page TIFF, and standard benchmark imagery (PNG, JPEG).
    Extracts complete geometric, spectral, and sensor metadata.
    """
    @staticmethod
    def inspect(filepath: str | Path) -> RasterMetadata:
        path = Path(filepath)
        if not path.exists():
            raise InvalidInputError(f"Raster file not found at path: {path}")

        ext = path.suffix.lower()
        if ext in [".tif", ".tiff"]:
            return RasterInspector._inspect_geotiff(path)
        elif ext in [".png", ".jpg", ".jpeg"]:
            return RasterInspector._inspect_image(path)
        else:
            raise UnsupportedFormatError(
                f"Unsupported raster format '{ext}'. Expected GeoTIFF (.tif, .tiff) or image (.png, .jpg, .jpeg)."
            )

    @staticmethod
    def _inspect_geotiff(path: Path) -> RasterMetadata:
        if rasterio is not None:
            try:
                with rasterio.open(path) as src:
                    crs_str = str(src.crs) if src.crs else None
                    bounds = [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top] if src.bounds else None
                    transform = list(src.transform)[:6] if src.transform else None
                    res = [abs(src.res[0]), abs(src.res[1])] if src.res else None
                    nodata = src.nodata
                    descriptions = [src.descriptions[i] or f"Band {i+1}" for i in range(src.count)] if src.descriptions else []
                    tags = src.tags() or {}
                    
                    acquisition_date = tags.get("ACQUISITION_DATE") or tags.get("TIFFTAG_DATETIME")
                    sensor = tags.get("SENSOR_ID") or tags.get("SENSOR")
                    platform = tags.get("PLATFORM") or tags.get("SATELLITE")

                    return RasterMetadata(
                        filepath=str(path.resolve()),
                        filename=path.name,
                        format="GeoTIFF",
                        width=src.width,
                        height=src.height,
                        bands=src.count,
                        dtype=str(src.dtypes[0]),
                        crs=crs_str,
                        bounds=bounds,
                        transform=transform,
                        resolution=res,
                        nodata=float(nodata) if nodata is not None else None,
                        band_descriptions=descriptions,
                        tags=tags,
                        sensor=sensor,
                        platform=platform,
                        acquisition_date=acquisition_date,
                        is_georeferenced=crs_str is not None
                    )
            except Exception as e:
                logger.warning(f"rasterio failed on {path}: {e}. Falling back to tifffile/PIL.")

        if tifffile is not None:
            try:
                with tifffile.TiffFile(path) as tif:
                    page = tif.pages[0]
                    shape = page.shape
                    dtype = str(page.dtype)
                    
                    if len(shape) == 2:
                        h, w = shape
                        bands = 1
                    elif len(shape) == 3:
                        if shape[0] < shape[2]:  # (bands, h, w)
                            bands, h, w = shape
                        else:  # (h, w, bands)
                            h, w, bands = shape
                    else:
                        h, w, bands = shape[-2], shape[-1], 1

                    tags_dict: Dict[str, Any] = {}
                    for tag in page.tags.values():
                        if tag.code in (33550, 33922, 34264, 34735, 34736, 34737):
                            continue  # GeoTIFF binary tags are parsed below, not stringified
                        tags_dict[tag.name] = str(tag.value)

                    geo = RasterInspector._georeference_from_tifffile(tif, int(w), int(h))

                    return RasterMetadata(
                        filepath=str(path.resolve()),
                        filename=path.name,
                        format="GeoTIFF" if geo["crs"] else "TIFF",
                        width=int(w),
                        height=int(h),
                        bands=int(bands),
                        dtype=dtype,
                        crs=geo["crs"],
                        bounds=geo["bounds"],
                        transform=geo["transform"],
                        resolution=geo["resolution"],
                        nodata=geo["nodata"],
                        band_descriptions=[f"Band {i+1}" for i in range(bands)],
                        tags=tags_dict,
                        acquisition_date=tags_dict.get("DateTime"),
                        is_georeferenced=geo["crs"] is not None and geo["transform"] is not None
                    )
            except Exception as e:
                logger.warning(f"tifffile failed on {path}: {e}. Falling back to PIL.")

        # PIL Fallback
        with Image.open(path) as img:
            bands = len(img.getbands())
            return RasterMetadata(
                filepath=str(path.resolve()),
                filename=path.name,
                format="TIFF",
                width=img.width,
                height=img.height,
                bands=bands,
                dtype="uint8",
                crs=None,
                bounds=None,
                transform=None,
                resolution=None,
                nodata=None,
                band_descriptions=list(img.getbands()),
                tags={},
                is_georeferenced=False
            )

    @staticmethod
    def _georeference_from_tifffile(tif: Any, width: int, height: int) -> Dict[str, Any]:
        """
        Reads GeoTIFF georeferencing without rasterio/GDAL (rules.md §2: no system binaries).

        CRS from ProjectedCSTypeGeoKey (3072) or GeographicTypeGeoKey (2048) as EPSG codes.
        Transform from ModelTransformation (34264), else ModelPixelScale (33550) + ModelTiepoint
        (33922). Returned in rasterio Affine order [a, b, c, d, e, f]:
            x = a*col + b*row + c,   y = d*col + e*row + f
        so metadata is identical whichever reader produced it. PixelIsPoint rasters are shifted by
        half a pixel to the area convention, as GDAL does. User-defined CRSs (32767) are reported
        as not georeferenced rather than guessed.
        """
        out: Dict[str, Any] = {"crs": None, "transform": None, "bounds": None, "resolution": None, "nodata": None}
        try:
            page = tif.pages[0]
            nodata_tag = page.tags.get(42113)
            if nodata_tag is not None:
                try:
                    out["nodata"] = float(str(nodata_tag.value).strip("\x00 "))
                except ValueError:
                    pass
            if not getattr(tif, "is_geotiff", False):
                return out
            g = tif.geotiff_metadata or {}
        except Exception as e:
            logger.warning(f"GeoTIFF key parsing failed: {e}")
            return out

        def code(key: str) -> Optional[int]:
            v = g.get(key)
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        epsg = code("ProjectedCSTypeGeoKey")
        if epsg is None or epsg == 32767:
            epsg = code("GeographicTypeGeoKey")
        if epsg is not None and epsg != 32767:
            out["crs"] = f"EPSG:{epsg}"
        elif g:
            logger.warning("GeoTIFF has a user-defined or missing CRS; treating raster as not georeferenced.")

        a = b = c = d = e = f = None
        if g.get("ModelTransformation") is not None:
            m = np.asarray(g["ModelTransformation"], dtype=float).reshape(4, 4)
            a, b, c, d, e, f = m[0, 0], m[0, 1], m[0, 3], m[1, 0], m[1, 1], m[1, 3]
        elif g.get("ModelPixelScale") is not None and g.get("ModelTiepoint") is not None:
            sx, sy = float(g["ModelPixelScale"][0]), float(g["ModelPixelScale"][1])
            i, j, _, x, y, _ = [float(v) for v in list(g["ModelTiepoint"])[:6]]
            a, b, d, e = sx, 0.0, 0.0, -sy
            c, f = x - i * sx, y + j * sy
        if a is None:
            out["crs"] = None
            return out

        if code("GTRasterTypeGeoKey") == 2:  # RasterPixelIsPoint
            c, f = c - 0.5 * a - 0.5 * b, f - 0.5 * d - 0.5 * e

        out["transform"] = [float(v) for v in (a, b, c, d, e, f)]
        xs = [c, a * width + c, b * height + c, a * width + b * height + c]
        ys = [f, d * width + f, e * height + f, d * width + e * height + f]
        out["bounds"] = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
        out["resolution"] = [float(abs(a) if b == 0 else np.hypot(a, d)), float(abs(e) if d == 0 else np.hypot(b, e))]
        return out

    @staticmethod
    def _inspect_image(path: Path) -> RasterMetadata:
        with Image.open(path) as img:
            bands = len(img.getbands())
            return RasterMetadata(
                filepath=str(path.resolve()),
                filename=path.name,
                format=img.format or path.suffix[1:].upper(),
                width=img.width,
                height=img.height,
                bands=bands,
                dtype="uint8",
                crs=None,
                bounds=None,
                transform=None,
                resolution=None,
                nodata=None,
                band_descriptions=list(img.getbands()),
                tags={},
                is_georeferenced=False
            )

    @staticmethod
    def read_as_array(filepath: str | Path) -> Tuple[np.ndarray, RasterMetadata]:
        """
        Loads raster as a NumPy array with shape (bands, height, width) or (height, width, bands).
        Returns the array and the extracted RasterMetadata.
        """
        meta = RasterInspector.inspect(filepath)
        path = Path(filepath)

        if rasterio is not None and meta.format == "GeoTIFF":
            try:
                with rasterio.open(path) as src:
                    arr = src.read()  # (bands, height, width)
                    return arr, meta
            except Exception as e:
                logger.warning(f"rasterio.read failed: {e}. Using PIL/tifffile fallback.")

        if tifffile is not None and meta.format in ["GeoTIFF", "TIFF"]:
            try:
                arr = tifffile.imread(str(path))
                if arr.ndim == 2:
                    arr = arr[np.newaxis, ...]  # (1, H, W)
                elif arr.ndim == 3 and arr.shape[2] in [1, 2, 3, 4, 8, 12, 16] and arr.shape[0] > arr.shape[2]:
                    arr = np.transpose(arr, (2, 0, 1))  # (H, W, C) -> (C, H, W)
                return arr, meta
            except Exception as e:
                logger.warning(f"tifffile.imread failed: {e}. Using PIL fallback.")

        # Standard PIL loading
        with Image.open(path) as img:
            arr = np.array(img)
            if arr.ndim == 2:
                arr = arr[np.newaxis, ...]
            elif arr.ndim == 3:
                arr = np.transpose(arr, (2, 0, 1))
            return arr, meta
