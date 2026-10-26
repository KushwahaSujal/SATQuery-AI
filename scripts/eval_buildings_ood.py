"""Buildings models on cities *neither* was trained on: LoveDA and OpenEarthMap test, building class only.

Q-071 compared the served `buildings_whu_ma_r50` with `buildings_whu_ma_inria_r50` on Inria test pieces,
which favours the Inria model (other tiles of the same five cities). This is the even-handed test:
- LoveDA official val (= our land-cover test, 1,669 tiles, Nanjing/Changzhou/Wuhan, 0.3 m):
  raw mask 2 = building, 0 = no-data (ignored);
- OpenEarthMap official val (= our test, 500 tiles, 44 countries, resampled to 0.5 m):
  raw mask 8 = building, 0 = unknown (ignored).
Neither model saw either set. Same infer_prob, each checkpoint's own val-frozen threshold, pooled IoU,
tiles resampled to the 0.5 m the models were trained at.

    .venv/bin/python scripts/eval_buildings_ood.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.segmentation.datasets import LANDCOVER_SOURCES, MEAN, STD  # noqa: E402
from training.segmentation.train_seg import build_model, infer_prob  # noqa: E402

MODELS = {"served_whu_ma_r50": ROOT / "checkpoints/buildings_whu_ma_r50_seg/best.pt",
          "whu_ma_inria_r50": ROOT / "checkpoints/buildings_whu_ma_inria_r50_seg/best.pt"}
BUILDING = {"loveda": 2, "openearthmap": 8}
TARGET_GSD = 0.5


def tile(img_path: Path, mask_path: Path, gsd: float, building: int):
    img = cv2.cvtColor(cv2.imread(str(img_path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    raw = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
    if raw.ndim == 3:
        raw = raw[..., 0]
    f = gsd / TARGET_GSD
    if abs(f - 1) > 1e-6:
        size = (round(img.shape[1] * f), round(img.shape[0] * f))
        img = cv2.resize(img, size, interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_LINEAR)
        raw = cv2.resize(raw, size, interpolation=cv2.INTER_NEAREST)
    x = torch.from_numpy(((img.astype(np.float32) - MEAN) / STD).transpose(2, 0, 1).copy())[None]
    return x, raw == building, raw != 0


@torch.no_grad()
def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    nets = {}
    for name, path in MODELS.items():
        ck = torch.load(path, map_location=device, weights_only=False)
        m = build_model(ck["arch"], ck["encoder"]).to(device).eval()
        m.load_state_dict(ck["model"])
        nets[name] = (m, ck["threshold"])
    report = {}
    for source, building in BUILDING.items():
        items = LANDCOVER_SOURCES[source]("test")
        tp = {k: 0 for k in nets}; fp = dict(tp); fn = dict(tp)
        for i, (img, mask, gsd, _) in enumerate(items, 1):
            x, gt, valid = tile(Path(img), Path(mask), gsd, building)
            x = x.to(device)
            for name, (m, thr) in nets.items():
                pred = infer_prob(m, x)[0, 0].cpu().numpy() >= thr
                tp[name] += int((pred & gt & valid).sum())
                fp[name] += int((pred & ~gt & valid).sum())
                fn[name] += int((~pred & gt & valid).sum())
            if i % 200 == 0:
                print(f"{source} {i}/{len(items)}", flush=True)
        report[source] = {"tiles": len(items), **{
            name: {"iou": round(tp[name] / max(tp[name] + fp[name] + fn[name], 1), 4),
                   "precision": round(tp[name] / max(tp[name] + fp[name], 1), 4),
                   "recall": round(tp[name] / max(tp[name] + fn[name], 1), 4),
                   "threshold": nets[name][1]} for name in nets}}
        print(json.dumps({source: report[source]}), flush=True)
    out = ROOT / "results/eval/buildings_ood_loveda_oem.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
