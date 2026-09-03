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
        tifffile.imwrite(str(out), uint8_mask)
    else:
        Image.fromarray(uint8_mask).save(str(out))

    return out
