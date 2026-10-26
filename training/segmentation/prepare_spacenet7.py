"""Turn SpaceNet 7 monthly mosaics + building footprints into PNG image/mask pairs.

60 labelled AOIs x ~24 monthly Planet mosaics, 1024 px at 4.77 m (EPSG:3857 pixel size; ground
size shrinks with latitude). For each month:
- Image: RGB bands of the 4-band uint8 mosaic. Pixels under the month's UDM polygons (cloud /
  unusable data, given in lon/lat) are written pure white, which read_pair() treats as "ignore" -
  the same convention as Massachusetts and SpaceNet 3. Buildings under cloud are unlabelled.
- Mask: labels_match_pix polygons (already in pixel coordinates) rasterised to 255.

SN7_buildings_test_public carries no labels and is not prepared. Names are <aoi>__<yyyy_mm>.png so
datasets.py can split on the AOI. Idempotent: pairs already written are skipped.

    .venv/bin/python -m training.segmentation.prepare_spacenet7
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom
from shapely.geometry import shape

RAW = Path(__file__).resolve().parents[2] / "datasets/raw/spacenet7_multitemporal"
TRAIN = RAW / "SN7_buildings_train/train"
OUT = RAW / "prepared"


def main() -> None:
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    (OUT / "masks").mkdir(parents=True, exist_ok=True)
    done = skipped = 0
    for tif in sorted(TRAIN.glob("*/images/*.tif")):
        aoi = tif.parts[-3]
        month = tif.stem.split("global_monthly_", 1)[1][:7]  # yyyy_mm
        name = f"{aoi}__{month}.png"
        if (OUT / "masks" / name).exists():
            continue
        labels = tif.parent.parent / "labels_match_pix" / f"{tif.stem}_Buildings.geojson"
        udm = tif.parent.parent / "labels" / f"{tif.stem}_UDM.geojson"
        if not labels.exists():
            skipped += 1
            continue
        with rasterio.open(tif) as ds:
            rgb = ds.read((1, 2, 3)).transpose(1, 2, 0).copy()
            h, w, transform, crs = ds.height, ds.width, ds.transform, ds.crs
        polys = [(shape(f["geometry"]), 255) for f in json.loads(labels.read_text())["features"] if f.get("geometry")]
        mask = rasterize(polys, out_shape=(h, w), fill=0, dtype="uint8") if polys else np.zeros((h, w), np.uint8)
        if udm.exists():
            clouds = [transform_geom("OGC:CRS84", crs, f["geometry"])
                      for f in json.loads(udm.read_text())["features"] if f.get("geometry")]
            if clouds:
                bad = rasterize(clouds, out_shape=(h, w), transform=transform, fill=0, dtype="uint8").astype(bool)
                rgb[bad] = 255
                mask[bad] = 0
        cv2.imwrite(str(OUT / "images" / name), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(OUT / "masks" / name), mask)
        done += 1
    print(f"spacenet7: prepared {done} months; {skipped} without labels")


if __name__ == "__main__":
    main()
