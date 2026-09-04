#!/usr/bin/env python3
"""
SatQuery AI — ChangeFormer evaluation on the real LEVIR-CD test split.

WHY
---
satquery_changeformer_best.pt self-reports its own validation metrics:

    epoch 10 | precision 0.857  recall 0.776  f1 0.814  IoU 0.687

The production pipeline scores IoU ~0.21 on datasets/samples/real_pair/, and a
sweep over every candidate normalisation moved that by only 0.014 — so the
normalisation contract is NOT the difference. Either the single sample pair is
unrepresentative, or the inference path is wrong.

This runs the production adapter over the genuine LEVIR-CD test split
(2,048 256x256 pairs, ericyu/LEVIRCD_Cropped256) and reports IoU/F1 against the
official labels, so the two hypotheses can be told apart:

  IoU near 0.687  -> the pipeline is fine; the sample pair is the odd one out
  IoU near 0.21   -> the inference path is genuinely wrong; keep investigating

Usage:
    python scripts/evaluate_changeformer_levircd.py --limit 200
    python scripts/evaluate_changeformer_levircd.py --limit 200 --swap   # T1/T2 swapped
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PARQUET = PROJECT_ROOT / "datasets/raw/levircd/data/test-00000-of-00001-31d7c3e3444e5b5d.parquet"
OUT_DIR = PROJECT_ROOT / "results/evaluations"


def metrics(pred: np.ndarray, gt: np.ndarray) -> tuple[int, int, int]:
    p, g = pred.astype(bool), gt.astype(bool)
    return (
        int(np.logical_and(p, g).sum()),
        int(np.logical_and(p, ~g).sum()),
        int(np.logical_and(~p, g).sum()),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--swap", action="store_true", help="feed T2 as image A (tests temporal order)")
    args = ap.parse_args()

    if not PARQUET.is_file():
        print(f"[ERROR] missing {PARQUET}", file=sys.stderr)
        return 1

    import pyarrow.parquet as pq
    from backend.app.ml.adapters.changeformer import ChangeFormerAdapter

    adapter = ChangeFormerAdapter()
    if not adapter.is_available():
        print("[BLOCKED] ChangeFormer checkpoint not found.", file=sys.stderr)
        return 2
    adapter.load_model()

    ck_meta = {}
    try:
        import torch

        ck_meta = torch.load(
            str(adapter._resolve_checkpoint_path()), map_location="cpu", weights_only=False
        ).get("metadata", {})
    except Exception:
        pass
    if ck_meta.get("validation_metrics"):
        vm = ck_meta["validation_metrics"]
        print(f"checkpoint self-reported validation: IoU {vm.get('iou'):.4f}  F1 {vm.get('f1'):.4f}  "
              f"P {vm.get('precision'):.4f}  R {vm.get('recall'):.4f}  (epoch {ck_meta.get('epoch')})\n")

    rows = pq.ParquetFile(PARQUET).read().to_pylist()[: args.limit]
    print(f"evaluating {len(rows)} LEVIR-CD test pairs "
          f"(threshold {args.threshold}{', T1/T2 SWAPPED' if args.swap else ''})\n")

    TP = FP = FN = 0
    per_pair, t0 = [], time.perf_counter()
    for i, r in enumerate(rows, 1):
        a = Image.open(io.BytesIO(r["imageA"]["bytes"])).convert("RGB")
        b = Image.open(io.BytesIO(r["imageB"]["bytes"])).convert("RGB")
        lab = np.array(Image.open(io.BytesIO(r["label"]["bytes"])).convert("L"))
        gt = (lab > 128).astype(np.uint8)

        if args.swap:
            a, b = b, a
        res = adapter.predict(a, b, threshold=args.threshold)
        pred = res.masks[0]["binary_mask"]
        if pred.shape != gt.shape:
            pred = np.array(
                Image.fromarray(pred * 255).resize(gt.shape[::-1], Image.NEAREST)
            ) > 128

        tp, fp, fn = metrics(pred, gt)
        TP, FP, FN = TP + tp, FP + fp, FN + fn
        per_pair.append(tp / (tp + fp + fn) if (tp + fp + fn) else 1.0)

        if i % 50 == 0 or i == len(rows):
            iou = TP / (TP + FP + FN) if (TP + FP + FN) else 0.0
            print(f"  [{i}/{len(rows)}] cumulative IoU {iou:.4f}")

    iou = TP / (TP + FP + FN) if (TP + FP + FN) else 0.0
    prec = TP / (TP + FP) if (TP + FP) else 0.0
    rec = TP / (TP + FN) if (TP + FN) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    dur = time.perf_counter() - t0

    print("\n" + "=" * 62)
    print("LEVIR-CD TEST SPLIT — MEASURED")
    print("=" * 62)
    print(f"  pairs            : {len(rows)}")
    print(f"  threshold        : {args.threshold}{'  (T1/T2 swapped)' if args.swap else ''}")
    print(f"  IoU  (aggregate) : {iou:.4f}")
    print(f"  IoU  (mean/pair) : {np.mean(per_pair):.4f}")
    print(f"  F1               : {f1:.4f}")
    print(f"  precision        : {prec:.4f}")
    print(f"  recall           : {rec:.4f}")
    print(f"  seconds/pair     : {dur/len(rows):.3f}")

    if ck_meta.get("validation_metrics"):
        target = ck_meta["validation_metrics"]["iou"]
        print(f"\n  checkpoint's own : {target:.4f}   delta {iou - target:+.4f}")
        if iou >= target * 0.85:
            print("  VERDICT: pipeline reproduces training-time accuracy. The sample pair in\n"
                  "           datasets/samples/real_pair/ is unrepresentative — not a code bug.")
        else:
            print("  VERDICT: pipeline is well below the checkpoint's own validation score.\n"
                  "           The inference path is wrong — keep investigating.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_DIR / f"changeformer_levircd_{stamp}.json"
    out.write_text(json.dumps({
        "dataset": "LEVIR-CD test (ericyu/LEVIRCD_Cropped256)",
        "pairs": len(rows), "threshold": args.threshold, "swapped": args.swap,
        "iou_aggregate": round(iou, 4), "iou_mean_per_pair": round(float(np.mean(per_pair)), 4),
        "f1": round(f1, 4), "precision": round(prec, 4), "recall": round(rec, 4),
        "checkpoint_reported": ck_meta.get("validation_metrics"),
        "seconds_per_pair": round(dur / len(rows), 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    print(f"\n  written -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
