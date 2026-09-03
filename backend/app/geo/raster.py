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
                        tags_dict[tag.name] = str(tag.value)

                    return RasterMetadata(
                        filepath=str(path.resolve()),
                        filename=path.name,
                        format="TIFF",
                        width=int(w),
                        height=int(h),
                        bands=int(bands),
                        dtype=dtype,
                        crs=None,
                        bounds=None,
                        transform=None,
                        resolution=None,
                        nodata=None,
                        band_descriptions=[f"Band {i+1}" for i in range(bands)],
                        tags=tags_dict,
                        is_georeferenced=False
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
