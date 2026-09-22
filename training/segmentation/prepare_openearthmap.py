"""Unpack the OpenEarthMap parquet mirror (EVER-Z/open_earth_map) into image/mask PNG pairs.

Writes datasets/raw/openearthmap/prepared/{train,val}/{images,masks}/<image_name>.png, one row
group at a time so RAM stays flat. Masks keep OpenEarthMap's own class indices (0 unknown …
8 building); datasets.py maps them to the shared land-cover classes. Idempotent.

    .venv/bin/python -m training.segmentation.prepare_openearthmap
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[2] / "datasets/raw/openearthmap"
OUT = ROOT / "prepared"


def main() -> None:
    written = skipped = 0
    for part in sorted((ROOT / "data").glob("*.parquet")):
        split = "val" if part.name.startswith("val") else "train"
        (OUT / split / "images").mkdir(parents=True, exist_ok=True)
        (OUT / split / "masks").mkdir(parents=True, exist_ok=True)
        pf = pq.ParquetFile(part)
        for g in range(pf.num_row_groups):
            for rec in pf.read_row_group(g, columns=["image", "mask", "image_name"]).to_pylist():
                name = Path(rec["image_name"]).stem + ".png"
                if (OUT / split / "masks" / name).exists():
                    skipped += 1
                    continue
                img = Image.open(io.BytesIO(rec["image"]["bytes"])).convert("RGB")
                mask = np.array(Image.open(io.BytesIO(rec["mask"]["bytes"])))
                if mask.ndim == 3:
                    mask = mask[..., 0]
                img.save(OUT / split / "images" / name)
                Image.fromarray(mask.astype(np.uint8)).save(OUT / split / "masks" / name)
                written += 1
    print(f"openearthmap: wrote {written}, skipped {skipped} existing")


if __name__ == "__main__":
    main()
