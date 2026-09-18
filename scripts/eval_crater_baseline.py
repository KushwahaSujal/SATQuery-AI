"""Zero-shot Grounding DINO ("crater.") vs the trained YOLO crater detector, same tiles, same AP code.

AP50 is computed here for both (COCO-style 101-point interpolation, one class, greedy matching at
IoU ≥ 0.5 by descending score), so the two numbers are directly comparable. Test tiles come from
datasets/processed/craters/test_<source>.txt written by training/detection/train_craters.py.

    .venv/bin/python scripts/eval_crater_baseline.py --n 150
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter  # noqa: E402

LISTS = ROOT / "datasets/processed/craters"


def load_gt(img_path: Path, w: int, h: int) -> np.ndarray:
    lbl = Path(str(img_path).replace("/images/", "/labels/")).with_suffix(".txt")
    rows = [list(map(float, l.split()[1:5])) for l in lbl.read_text().splitlines() if l.strip()] if lbl.exists() else []
    if not rows:
        return np.zeros((0, 4))
    a = np.array(rows)
    cx, cy, bw, bh = a[:, 0] * w, a[:, 1] * h, a[:, 2] * w, a[:, 3] * h
    return np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 1)


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ix1 = np.maximum(a[:, None, 0], b[None, :, 0]); iy1 = np.maximum(a[:, None, 1], b[None, :, 1])
    ix2 = np.minimum(a[:, None, 2], b[None, :, 2]); iy2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)
    area = lambda x: (x[:, 2] - x[:, 0]) * (x[:, 3] - x[:, 1])  # noqa: E731
    return inter / np.maximum(area(a)[:, None] + area(b)[None, :] - inter, 1e-9)


def match(pred: np.ndarray, scores: np.ndarray, gt: np.ndarray) -> list[tuple[float, int]]:
    """(score, is_true_positive) per prediction."""
    order = np.argsort(-scores)
    used = np.zeros(len(gt), bool)
    ious = iou_matrix(pred[order], gt) if len(gt) and len(pred) else np.zeros((len(pred), 0))
    out = []
    for k, i in enumerate(order):
        tp = 0
        if ious.shape[1]:
            cand = np.where(~used & (ious[k] >= 0.5))[0]
            if len(cand):
                j = cand[np.argmax(ious[k, cand])]
                used[j], tp = True, 1
        out.append((float(scores[i]), tp))
    return out


def ap50(records: list[tuple[float, int]], n_gt: int) -> dict:
    if not records or n_gt == 0:
        return {"ap50": 0.0, "recall_max": 0.0, "detections": len(records)}
    rec = sorted(records, key=lambda r: -r[0])
    tp = np.cumsum([r[1] for r in rec]); fp = np.cumsum([1 - r[1] for r in rec])
    recall, precision = tp / n_gt, tp / np.maximum(tp + fp, 1)
    precision = np.maximum.accumulate(precision[::-1])[::-1]
    pts = np.linspace(0, 1, 101)
    ap = float(np.mean([precision[recall >= p].max() if (recall >= p).any() else 0.0 for p in pts]))
    return {"ap50": round(ap, 4), "recall_max": round(float(recall[-1]), 4), "detections": len(records)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150, help="tiles per source (seeded sample; all if fewer)")
    ap.add_argument("--weights", default=str(ROOT / "checkpoints/craters_yolo/weights/best.pt"))
    ap.add_argument("--box-threshold", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    from ultralytics import YOLO

    gd, yolo = GroundingDINOAdapter(), YOLO(args.weights)
    summary = {}
    for src in ("lu3m6tgt", "mars_moon"):
        paths = [Path(p) for p in (LISTS / f"test_{src}.txt").read_text().split()]
        paths = random.Random(args.seed).sample(paths, min(args.n, len(paths)))
        recs = {"grounding_dino": [], "yolo": []}
        n_gt, t_gd = 0, 0.0
        for i, p in enumerate(paths, 1):
            img = Image.open(p).convert("RGB")
            gt = load_gt(p, *img.size)
            n_gt += len(gt)
            t = time.time()
            res = gd.predict(img, "crater.", box_threshold=args.box_threshold, text_threshold=args.box_threshold)
            t_gd += time.time() - t
            boxes = res["boxes"] if isinstance(res, dict) else getattr(res, "boxes", [])
            pb = np.array([b["xyxy"] for b in boxes]).reshape(-1, 4)
            ps = np.array([b["score"] for b in boxes])
            recs["grounding_dino"] += match(pb, ps, gt)
            r = yolo.predict(str(p), imgsz=832, conf=0.001, max_det=1000, verbose=False)[0]
            recs["yolo"] += match(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), gt)
            if i % 25 == 0:
                print(f"{src} {i}/{len(paths)}", flush=True)
        summary[src] = {"tiles": len(paths), "gt_craters": n_gt,
                        "grounding_dino": ap50(recs["grounding_dino"], n_gt) | {"sec_per_tile": round(t_gd / len(paths), 2)},
                        "yolo": ap50(recs["yolo"], n_gt)}
        print(json.dumps({src: summary[src]}), flush=True)
    out = ROOT / "results/training/crater_h2h.json"
    out.write_text(json.dumps({"args": vars(args), "summary": summary}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
