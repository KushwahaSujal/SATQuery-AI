#!/usr/bin/env python3
"""
SatQuery AI — Q-009's headline deliberation numbers, re-measured under each verifier crop geometry.

Q-009 reported, on "300 present + 300 absent VRSBench queries": present R@0.5 40.7%, present mIoU
0.371, absent queries that still return a box 28.0%, with the present set splitting into 206
attribute and 94 plain-category queries. The script that produced those numbers was never committed
and neither was the per-query cache it replayed, so this rebuilds the measurement from the same
source data with a stated, deterministic selection rule and runs the real pipeline. The absolute
values are therefore expected to sit near, not exactly on, the 2026-09-14 figures; what is
like-for-like is the comparison between crop geometries, which share one sample and one process.

Selection:
  present  first 300 `unique` VRSBench referring records (unambiguous ground-truth box), in file
           order; the reasoner decides on its own which are attribute and which are plain.
  absent   the same 300 images, each queried "find the {class}" for the first class of a fixed list
           that the image's own records do not contain.
  absent-attribute (Q-009 §3, 220 queries) — the first 220 of the present records with the object
           class token replaced by a class absent from that image.

Usage: .venv/bin/python scripts/eval_grounding_verdicts_vrsbench.py [--modes pad inset] [--n 300]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.evidence.verifier import DetectionVerifier
from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
from backend.app.ml.adapters.sam2 import SAM2Adapter
from backend.app.workflows.grounding import run_grounding_pipeline

REFERRING = PROJECT_ROOT / "datasets/raw/vrsbench/VRSBench_EVAL_referring.json"
IMAGES = PROJECT_ROOT / "datasets/raw/vrsbench/images/Images_val"
OUT = PROJECT_ROOT / "results/evaluations/grounding_verdicts_crop_geometry_20260921.json"
# Fixed substitution order for the absent-object queries.
ABSENT_POOL = ["airplane", "ship", "windmill", "storage tank", "baseball diamond", "tennis court",
               "swimming pool", "roundabout", "harbor", "stadium", "dam", "chimney", "bridge"]


def iou(a, b) -> float:
    if not a or not b:
        return 0.0
    ax1, ay1, ax2, ay2 = min(a[0], a[2]), min(a[1], a[3]), max(a[0], a[2]), max(a[1], a[3])
    bx1, by1, bx2, by2 = min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3])
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return float(inter / union) if union > 0 else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=["pad", "inset"])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--n-absent-attribute", type=int, default=220)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    records = json.loads(REFERRING.read_text())
    per_image: Dict[str, set] = collections.defaultdict(set)
    for r in records:
        per_image[r["image_id"]].add(r["obj_cls"].replace("-", " "))

    present = [r for r in records if r.get("unique")][: args.n]
    absent = []
    for r in present:
        here = per_image[r["image_id"]]
        miss = next((c for c in ABSENT_POOL if c not in here), None)
        if miss:
            absent.append({"image_id": r["image_id"], "query": f"find the {miss}"})
    abs_attr = []
    for r in present[: args.n_absent_attribute]:
        here = per_image[r["image_id"]]
        miss = next((c for c in ABSENT_POOL if c not in here), None)
        cls = r["obj_cls"].replace("-", " ")
        q = r["question"]
        swapped = q.replace(cls, miss) if cls in q.lower() else f"the {miss} " + q.split(" ", 1)[-1]
        if miss:
            abs_attr.append({"image_id": r["image_id"], "query": swapped})
    print(f"present {len(present)} · absent {len(absent)} · absent-attribute {len(abs_attr)}")

    gd, sam = GroundingDINOAdapter(), SAM2Adapter()
    cache: Dict[str, np.ndarray] = {}

    def arr(image_id: str) -> np.ndarray:
        if image_id not in cache:
            if len(cache) > 8:
                cache.clear()
            with Image.open(IMAGES / image_id) as im:
                cache[image_id] = np.asarray(im.convert("RGB"))
        return cache[image_id]

    results: Dict[str, Dict] = {}
    try:
        for mode in args.modes:
            v = DetectionVerifier(crop_mode=mode)
            t0 = time.time()
            ious: List[float] = []
            found = 0
            by_strategy: Dict[str, List[float]] = collections.defaultdict(list)
            pstatus = collections.Counter()
            for r in present:
                a = arr(r["image_id"])
                h, w = a.shape[:2]
                xs, ys = r["obj_corner"][0::2], r["obj_corner"][1::2]
                gt = [min(xs) * w, min(ys) * h, max(xs) * w, max(ys) * h]
                res = run_grounding_pipeline(image=a, query=r["question"], grounding_adapter=gd,
                                             sam2_adapter=sam, verifier=v)
                box = res.get("selected_box")
                d = res.get("agent_deliberation", {}) or {}
                pstatus[str(d.get("decision"))] += 1
                score = iou(box, gt) if box else 0.0
                ious.append(score)
                found += bool(box)
                key = "attribute" if d.get("mode") == "attribute_query_label_only" else "plain"
                by_strategy[key].append(score)

            astatus = collections.Counter()
            returned = 0
            for q in absent:
                res = run_grounding_pipeline(image=arr(q["image_id"]), query=q["query"],
                                             grounding_adapter=gd, sam2_adapter=sam, verifier=v)
                d = res.get("agent_deliberation", {}) or {}
                astatus[str(d.get("decision"))] += 1
                returned += bool(res.get("selected_box"))

            aa = collections.Counter()
            for q in abs_attr:
                res = run_grounding_pipeline(image=arr(q["image_id"]), query=q["query"],
                                             grounding_adapter=gd, sam2_adapter=sam, verifier=v)
                d = res.get("agent_deliberation", {}) or {}
                att = d.get("attempts") or []
                aa[str(att[-1].get("verifier_status")) if att else "no_candidates"] += 1

            n, na = len(present), len(absent)
            results[mode] = {
                "n_present": n, "n_absent": na, "n_absent_attribute": len(abs_attr),
                "present_found": round(found / n, 4),
                "present_R_at_0_5": round(sum(1 for i in ious if i >= 0.5) / n, 4),
                "present_mIoU": round(float(np.mean(ious)), 4),
                "present_decisions": dict(pstatus),
                "by_strategy": {k: {"n": len(v2),
                                    "R_at_0_5": round(sum(1 for i in v2 if i >= 0.5) / len(v2), 4),
                                    "mIoU": round(float(np.mean(v2)), 4)}
                                for k, v2 in sorted(by_strategy.items())},
                "absent_returned_a_box": round(returned / na, 4),
                "absent_decisions": dict(astatus),
                "absent_attribute_top_candidate_verdict": {
                    k: round(c / len(abs_attr), 4) for k, c in aa.items()},
                "seconds": round(time.time() - t0, 1),
            }
            print(f"\n=== mode {mode}")
            print(json.dumps(results[mode], indent=2))
    finally:
        for a2 in (gd, sam):
            try:
                a2.unload()
            except Exception:
                pass
        try:
            DetectionVerifier().clip.unload()
        except Exception:
            pass

    Path(args.out).write_text(json.dumps(
        {"selection": "first 300 unique VRSBench referring records; absent = fixed-pool substitution",
         "absent_pool": ABSENT_POOL, "modes": results}, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
