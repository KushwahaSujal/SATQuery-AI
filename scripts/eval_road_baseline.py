"""Score the production grounding pipeline ("mark all roads") as a road segmenter.

Same test tiles and the same pixel metrics as training/segmentation/train_seg.py, so the
trained road model and today's Grounding DINO + SAM2 path can be compared directly (Q-020).

    .venv/bin/python scripts/eval_road_baseline.py --source deepglobe_roads --n 100
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter  # noqa: E402
from backend.app.ml.adapters.sam2 import SAM2Adapter  # noqa: E402
from backend.app.workflows.grounding import run_grounding_pipeline  # noqa: E402
from training.segmentation.datasets import MEAN, SOURCES, STD, read_pair  # noqa: E402
from training.segmentation.train_seg import build_model, infer_prob  # noqa: E402


def load_checkpoint(path: Path):
    ckpt = torch.load(path, map_location="cuda")
    model = build_model(ckpt["arch"], ckpt["encoder"])
    model.load_state_dict(ckpt["model"])
    return model.cuda().eval(), ckpt["threshold"]


def predict(model, img: np.ndarray, thr: float) -> np.ndarray:
    x = torch.from_numpy(((img.astype(np.float32) - MEAN) / STD).transpose(2, 0, 1)).cuda()[None]
    return (infer_prob(model, x)[0, 0] > thr).cpu().numpy()


def score(pred: np.ndarray, gt: np.ndarray, valid: np.ndarray) -> tuple[int, int, int]:
    m, v = gt > 0.5, valid > 0.5
    p = pred & v
    return int((p & m).sum()), int((p & ~m).sum()), int((~p & m & v).sum())


def metrics(tp: int, fp: int, fn: int) -> dict:
    return {"iou": round(tp / max(tp + fp + fn, 1), 4),
            "f1": round(2 * tp / max(2 * tp + fp + fn, 1), 4),
            "precision": round(tp / max(tp + fp, 1), 4),
            "recall": round(tp / max(tp + fn, 1), 4)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="deepglobe_roads", choices=sorted(SOURCES))
    ap.add_argument("--query", default="mark all roads")
    ap.add_argument("--n", type=int, default=100, help="random test tiles (seeded)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--checkpoint", default=None, help="also score this trained model on the same tiles")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    items = SOURCES[args.source]("test")
    items = random.Random(args.seed).sample(items, min(args.n, len(items)))
    gd, sam = GroundingDINOAdapter(), SAM2Adapter()

    trained = load_checkpoint(Path(args.checkpoint)) if args.checkpoint else None

    base, ours = np.zeros(3, np.int64), np.zeros(3, np.int64)
    rows, base_sec = [], 0.0
    for i, item in enumerate(items, 1):
        img_path = item[0]
        img, gt, valid = read_pair(*item)
        ts = time.time()
        res = run_grounding_pipeline(Image.fromarray(img), args.query,
                                     grounding_adapter=gd, sam2_adapter=sam)
        base_sec += time.time() - ts
        pred = res.get("segmentation_mask")
        pred = np.zeros(gt.shape, bool) if pred is None else np.squeeze(np.asarray(pred)) > 0
        b = score(pred, gt, valid)
        base += b
        row = {"tile": img_path.name, "baseline_iou": metrics(*b)["iou"], "answer": res.get("answer")}
        if trained:
            o = score(predict(trained[0], img, trained[1]), gt, valid)
            ours += o
            row["trained_iou"] = metrics(*o)["iou"]
        rows.append(row)
        print(f"{i:4d}/{len(items)} {img_path.name:24s} " +
              " ".join(f"{k}={v:.3f}" for k, v in row.items() if k.endswith("iou")), flush=True)

    summary = {
        "source": args.source, "query": args.query, "tiles": len(items), "seed": args.seed,
        "baseline": {"pipeline": "GroundingDINO + V4 reasoning + SAM2 (run_grounding_pipeline defaults)",
                     **metrics(*base), "sec_per_tile": round(base_sec / max(len(items), 1), 2)},
    }
    if trained:
        summary["trained"] = {"checkpoint": args.checkpoint, "threshold": trained[1], **metrics(*ours)}
    out = Path(args.out or ROOT / f"results/training/road_baseline_{args.source}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "tiles": rows}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
