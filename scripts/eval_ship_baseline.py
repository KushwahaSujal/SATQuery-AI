"""Zero-shot Grounding DINO ("ship.") vs the trained YOLO ship detector on MASATI-v2 test, same AP code.

Reuses eval_crater_baseline.py's matching and AP50 (COCO-style 101-point, greedy at IoU >= 0.5), so
the numbers are comparable across the two head-to-heads. All 453 MASATI test tiles are scored;
about half have no ship, so "negative tiles with a box" at each detector's serving threshold
(Grounding DINO 0.35, YOLO 0.25) is reported alongside AP50 - a ship detector that boxes open sea
is worse than its AP suggests.

    .venv/bin/python scripts/eval_ship_baseline.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter  # noqa: E402
from scripts.eval_crater_baseline import ap50, load_gt, match  # noqa: E402

LIST = ROOT / "datasets/processed/ships/test.txt"
SERVING_THR = {"grounding_dino": 0.35, "yolo": 0.25}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(ROOT / "checkpoints/ships_yolo/weights/best.pt"))
    ap.add_argument("--box-threshold", type=float, default=0.05)
    ap.add_argument("--grounding-model-id", default=None, help="Grounding DINO id or local dir (default: config)")
    ap.add_argument("--out", default=str(ROOT / "results/training/ship_h2h.json"))
    args = ap.parse_args()

    from ultralytics import YOLO

    gd, yolo = GroundingDINOAdapter(), YOLO(args.weights)
    if args.grounding_model_id:
        gd.model_id = args.grounding_model_id
    paths = [Path(p) for p in LIST.read_text().split()]
    recs = {"grounding_dino": [], "yolo": []}
    neg_hits = {"grounding_dino": 0, "yolo": 0}
    n_gt = n_neg = 0
    t_gd = 0.0
    for i, p in enumerate(paths, 1):
        img = Image.open(p).convert("RGB")
        gt = load_gt(p, *img.size)
        n_gt += len(gt)
        t = time.time()
        res = gd.predict(img, "ship.", box_threshold=args.box_threshold, text_threshold=args.box_threshold)
        t_gd += time.time() - t
        boxes = res["boxes"] if isinstance(res, dict) else getattr(res, "boxes", [])
        out = {"grounding_dino": (np.array([b["xyxy"] for b in boxes]).reshape(-1, 4), np.array([b["score"] for b in boxes]))}
        r = yolo.predict(str(p), imgsz=640, conf=0.001, verbose=False)[0]
        out["yolo"] = (r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy())
        for k, (pb, ps) in out.items():
            recs[k] += match(pb, ps, gt)
            if not len(gt):
                neg_hits[k] += int((ps >= SERVING_THR[k]).any()) if len(ps) else 0
        n_neg += int(not len(gt))
        if i % 50 == 0:
            print(f"{i}/{len(paths)}", flush=True)
    summary = {"tiles": len(paths), "gt_ships": n_gt, "negative_tiles": n_neg}
    for k in recs:
        summary[k] = ap50(recs[k], n_gt) | {
            "negative_tiles_with_a_box_at_serving_threshold": round(neg_hits[k] / max(n_neg, 1), 4),
            "serving_threshold": SERVING_THR[k]}
    summary["grounding_dino"]["sec_per_tile"] = round(t_gd / len(paths), 2)
    out_path = Path(args.out)
    out_path.write_text(json.dumps({"args": vars(args), "summary": summary}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
