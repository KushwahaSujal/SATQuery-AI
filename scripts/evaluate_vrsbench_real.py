#!/usr/bin/env python3
"""
SatQuery AI — Grounding evaluation on the REAL VRSBench referring split.

Replaces the 2-record fixture in datasets/samples/vrsbench_sample_records.json, whose
records point at a LEVIR-CD crop with hand-drawn boxes (see decisions.md D-115).

The official VRSBench annotation format is not what the existing harness expects:

    existing harness : rec["bbox"]           = [x1,y1,x2,y2] absolute pixels
                       rec["query"]
    real VRSBench    : rec["ground_truth"]   = "{<x1><y1><x2><y2>}" in PERCENT (0-100)
                       rec["question"]

This script adapts the real format and runs the production pipeline
(backend/app/workflows/grounding.run_grounding_pipeline) unmodified.

Usage
-----
    python scripts/evaluate_vrsbench_real.py --limit 100
    python scripts/evaluate_vrsbench_real.py --limit 300 --unique-only
    python scripts/evaluate_vrsbench_real.py --showcase        # detailed single-query trace

Outputs results/evaluations/vrsbench_real_<timestamp>.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ANN = PROJECT_ROOT / "datasets/raw/vrsbench/VRSBench_EVAL_referring.json"
IMG_DIR = PROJECT_ROOT / "datasets/raw/vrsbench/images/Images_val"
OUT_DIR = PROJECT_ROOT / "results/evaluations"

GT_RE = re.compile(r"<\s*(\d+(?:\.\d+)?)\s*>")


def parse_vrsbench_gt(gt: str, width: int, height: int) -> Optional[List[float]]:
    """'{<25><40><33><60>}' in percent -> [x1,y1,x2,y2] absolute pixels."""
    vals = [float(v) for v in GT_RE.findall(gt or "")]
    if len(vals) != 4:
        return None
    x1, y1, x2, y2 = vals
    box = [x1 / 100.0 * width, y1 / 100.0 * height, x2 / 100.0 * width, y2 / 100.0 * height]
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    return box


def iou(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def load_records(limit: int, unique_only: bool, seed: int) -> List[Dict[str, Any]]:
    recs = json.loads(ANN.read_text())
    if unique_only:
        recs = [r for r in recs if r.get("unique")]
    recs = [r for r in recs if (IMG_DIR / r["image_id"]).is_file()]
    random.Random(seed).shuffle(recs)
    return recs[:limit]


def run_one(rec: Dict[str, Any], pipeline) -> Optional[Dict[str, Any]]:
    img_path = IMG_DIR / rec["image_id"]
    with Image.open(img_path) as im:
        w, h = im.size
        img = im.convert("RGB")

    gt = parse_vrsbench_gt(rec.get("ground_truth", ""), w, h)
    if gt is None:
        return None

    t0 = time.perf_counter()
    try:
        res = pipeline(image=img, query=rec["question"])
    except Exception as e:  # noqa: BLE001
        return {"image_id": rec["image_id"], "error": f"{type(e).__name__}: {e}", "iou": 0.0}
    dt = (time.perf_counter() - t0) * 1000.0

    pred = res.get("selected_box")
    return {
        "image_id": rec["image_id"],
        "question": rec["question"],
        "obj_cls": rec.get("obj_cls"),
        "unique": rec.get("unique"),
        "gt_box": [round(v, 1) for v in gt],
        "pred_box": [round(v, 1) for v in pred] if pred else None,
        "iou": round(iou(pred, gt), 4) if pred else 0.0,
        "grounding_score": res.get("grounding_score"),
        "sam2_score": res.get("sam2_score"),
        "strategy": res.get("strategy"),
        "n_candidates": len(res.get("evidence", {}).get("all_candidates", []) or []),
        "latency_ms": round(dt, 1),
        "image_size": [w, h],
        "trace": [s.get("step") for s in res.get("trace", [])],
    }


def summarise(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored = [r for r in rows if "error" not in r]
    ious = [r["iou"] for r in scored]
    n = len(ious)
    if n == 0:
        return {"n": 0}
    mean = sum(ious) / n
    lat = [r["latency_ms"] for r in scored if r.get("latency_ms")]
    return {
        "n_evaluated": n,
        "n_errors": len(rows) - n,
        "mean_iou": round(mean, 4),
        "median_iou": round(sorted(ious)[n // 2], 4),
        "recall@0.5": round(sum(1 for v in ious if v >= 0.5) / n, 4),
        "recall@0.25": round(sum(1 for v in ious if v >= 0.25) / n, 4),
        "recall@0.75": round(sum(1 for v in ious if v >= 0.75) / n, 4),
        "detection_rate": round(sum(1 for r in scored if r["pred_box"]) / n, 4),
        "mean_latency_ms": round(sum(lat) / len(lat), 1) if lat else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--unique-only", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--showcase", action="store_true", help="print a detailed single-query trace")
    args = ap.parse_args()

    if not ANN.is_file():
        print(f"[ERROR] missing annotations: {ANN}", file=sys.stderr)
        return 1
    if not IMG_DIR.is_dir():
        print(f"[ERROR] missing images: {IMG_DIR}", file=sys.stderr)
        return 1

    from backend.app.workflows.grounding import run_grounding_pipeline
    from backend.app.models.registry import model_registry

    print(f"grounding_dino available : {model_registry.is_model_available('grounding_dino')}")
    print(f"sam2 available           : {model_registry.is_model_available('sam2')}")
    print()

    recs = load_records(args.limit, args.unique_only, args.seed)
    print(f"evaluating {len(recs)} records "
          f"({'unique-only' if args.unique_only else 'all types'}, seed={args.seed})\n")

    rows: List[Dict[str, Any]] = []
    t_start = time.perf_counter()
    for i, rec in enumerate(recs, 1):
        r = run_one(rec, run_grounding_pipeline)
        if r is None:
            continue
        rows.append(r)
        if args.showcase and "error" in r:
            print(f"[showcase skipped — first record errored: {r['error']}]")
        if args.showcase and len(rows) == 1 and "error" not in r:
            print("=" * 72)
            print("SHOWCASE QUERY — full observable trace")
            print("=" * 72)
            print(f"  image     : {r['image_id']}  {r['image_size'][0]}x{r['image_size'][1]}")
            print(f"  query     : \"{r['question']}\"")
            print(f"  candidates: {r['n_candidates']} boxes from Grounding DINO")
            print(f"  strategy  : {r['strategy']}")
            print(f"  predicted : {r['pred_box']}")
            print(f"  ground tr.: {r['gt_box']}")
            print(f"  IoU       : {r['iou']}")
            print(f"  DINO score: {r['grounding_score']}   SAM2 score: {r['sam2_score']}")
            print(f"  latency   : {r['latency_ms']} ms")
            print("  pipeline steps:")
            for s in r["trace"]:
                print(f"      - {s}")
            print("=" * 72 + "\n")
        if i % 25 == 0 or i == len(recs):
            s = summarise(rows)
            print(f"  [{i}/{len(recs)}] mean_IoU={s.get('mean_iou')} "
                  f"R@0.5={s.get('recall@0.5')} errors={s.get('n_errors')}")

    total_s = time.perf_counter() - t_start
    summary = summarise(rows)
    summary["total_runtime_s"] = round(total_s, 1)
    summary["dataset"] = "VRSBench referring (official EVAL split)"
    summary["subset"] = "unique-only" if args.unique_only else "all"
    summary["seed"] = args.seed
    summary["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Per-category breakdown
    by_cls: Dict[str, List[float]] = {}
    for r in rows:
        if "error" not in r and r.get("obj_cls"):
            by_cls.setdefault(r["obj_cls"], []).append(r["iou"])
    summary["per_category"] = {
        k: {"n": len(v), "mean_iou": round(sum(v) / len(v), 4)}
        for k, v in sorted(by_cls.items(), key=lambda kv: -len(kv[1]))
    }

    print("\n" + "=" * 72)
    print("VRSBench REFERRING — REAL RESULTS")
    print("=" * 72)
    for k in ("n_evaluated", "n_errors", "mean_iou", "median_iou",
              "recall@0.25", "recall@0.5", "recall@0.75",
              "detection_rate", "mean_latency_ms", "total_runtime_s"):
        print(f"  {k:<18}: {summary.get(k)}")
    print("\n  per-category mean IoU:")
    for k, v in list(summary["per_category"].items())[:10]:
        print(f"    {k:<22} n={v['n']:<4} IoU={v['mean_iou']}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_DIR / f"vrsbench_real_{stamp}.json"
    out.write_text(json.dumps({"summary": summary, "records": rows}, indent=2))
    print(f"\n  written -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
