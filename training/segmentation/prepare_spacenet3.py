"""Turn SpaceNet 3 PS-RGB tiles + road-speed geojson into 8-bit PNG image/mask pairs.

- Image: uint16 → uint8 with a per-band 2–98 % stretch over valid pixels. No-data (all bands 0)
  is written as pure white, which read_pair() treats as "ignore" — the same convention as
  the Massachusetts tiles.
- Mask: each road centreline is buffered to its lane count × 1.75 m half-width (default 2 lanes,
  i.e. a 7 m road) at the 0.3 m ground sampling distance, then rasterised.

Idempotent: tiles already written are skipped.

    .venv/bin/python -m training.segmentation.prepare_spacenet3
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.affinity import affine_transform
from shapely.geometry import shape

RAW = Path(__file__).resolve().parents[2] / "datasets/raw/spacenet3_roads"
OUT = RAW / "prepared"
GSD_M = 0.3
LANE_HALF_WIDTH_M = 1.75


def stretch(bands: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.zeros(bands.shape[1:] + (3,), np.uint8)
    for i in range(3):
        v = bands[i][valid]
        if v.size == 0:
            continue
        lo, hi = np.percentile(v, (2, 98))
        out[..., i] = np.clip((bands[i].astype(np.float32) - lo) / max(hi - lo, 1) * 255, 0, 255)
    out[~valid] = 255
    return out


def lanes(props: dict) -> int:
    try:
        return max(1, int(props.get("lane_number") or 2))
    except (TypeError, ValueError):
        return 2


def main() -> None:
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    (OUT / "masks").mkdir(parents=True, exist_ok=True)
    done = skipped = 0
    for tif in sorted(RAW.glob("AOI_*/PS-RGB/*.tif")):
        aoi = tif.parts[-3]
        img_id = tif.stem.split("_PS-RGB_")[-1]
        name = f"{aoi}_{img_id}.png"
        if (OUT / "masks" / name).exists():
            continue
        gj = tif.parent.parent / "geojson_roads_speed" / tif.name.replace("PS-RGB", "geojson_roads_speed").replace(".tif", ".geojson")
        if not gj.exists():
            skipped += 1
            continue
        with rasterio.open(tif) as ds:
            bands = ds.read()
            inv = ~ds.transform
        valid = bands.any(axis=0)
        # lon/lat → pixel, then buffer in pixels.
        coeffs = [inv.a, inv.b, inv.d, inv.e, inv.c, inv.f]
        shapes = []
        for feat in json.loads(gj.read_text()).get("features", []):
            if not feat.get("geometry"):
                continue
            geom = affine_transform(shape(feat["geometry"]), coeffs)
            half_px = lanes(feat.get("properties") or {}) * LANE_HALF_WIDTH_M / GSD_M
            shapes.append((geom.buffer(half_px, cap_style="flat"), 1))
        h, w = valid.shape
        mask = rasterize(shapes, out_shape=(h, w), fill=0, dtype="uint8") if shapes else np.zeros((h, w), np.uint8)
        cv2.imwrite(str(OUT / "images" / name), cv2.cvtColor(stretch(bands, valid), cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(OUT / "masks" / name), mask * 255)
        done += 1
    print(f"prepared {done} tiles; {skipped} without geojson (yet)")


if __name__ == "__main__":
    main()
