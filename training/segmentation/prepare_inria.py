"""Cut the Inria Aerial Image Labeling training tiles into 1000x1000 PNG image/mask pairs.

The 180 labelled tiles are 5000x5000 at 0.3 m (36 per city: Austin, Chicago, Kitsap, West Tyrol,
Vienna). Reading a whole 75 MB tile for every 256 px training crop would starve the GPU, so each
tile is cut into a 5x5 grid of non-overlapping 1000 px pieces, named <tile>_<row>_<col>.png.
datasets.py splits on the *source* tile id, so all 25 pieces of a tile land in the same split.

Only data/train has ground truth; data/test is the benchmark's withheld set (images only) and is
not prepared. Masks are 0/255 as shipped. Idempotent: pieces already written are skipped.

    .venv/bin/python -m training.segmentation.prepare_inria
"""

from __future__ import annotations

from pathlib import Path

import cv2
import rasterio

RAW = Path(__file__).resolve().parents[2] / "datasets/raw/inria_aerial"
OUT = RAW / "prepared"
PIECE = 1000


def main() -> None:
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    (OUT / "masks").mkdir(parents=True, exist_ok=True)
    done = skipped = 0
    for tif in sorted((RAW / "data/train/images").glob("*.tif")):
        gt = RAW / "data/train/gt" / tif.name
        last = OUT / "masks" / f"{tif.stem}_4_4.png"
        if last.exists():
            skipped += 1
            continue
        with rasterio.open(tif) as ds:
            img = ds.read().transpose(1, 2, 0)
        with rasterio.open(gt) as ds:
            mask = ds.read(1)
        h, w = mask.shape
        for r in range(h // PIECE):
            for c in range(w // PIECE):
                name = f"{tif.stem}_{r}_{c}.png"
                ys, xs = slice(r * PIECE, (r + 1) * PIECE), slice(c * PIECE, (c + 1) * PIECE)
                cv2.imwrite(str(OUT / "images" / name), cv2.cvtColor(img[ys, xs], cv2.COLOR_RGB2BGR))
                cv2.imwrite(str(OUT / "masks" / name), mask[ys, xs])
        done += 1
    print(f"inria: prepared {done} tiles, skipped {skipped} already done")


if __name__ == "__main__":
    main()
