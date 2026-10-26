#!/usr/bin/env python3
"""Which grounding path should serve referring expressions? Base vs DIOR-RSVG fine-tune, measured per query.

Q-079 measured the fine-tune at detector level (full referring expression -> top-1 box): VRSBench Acc@0.5
0.300 -> 0.553. The audit (Q-080) showed that number cannot reach production by swapping model_id, because the
pipeline sends the detector only parse_v4_query's clean_prompt ("vehicle.") and picks among boxes with the
reasoner + verifier. So this compares the real options on the same queries:

  pipe_base   production pipeline, base weights                       (what serves today)
  pipe_ft     production pipeline, fine-tuned weights                 (option B: config swap)
  pipe_ref    production entry point after Q-084: nothing injected, the pipeline's own routing sends single-target
              referring queries to the fine-tuned detector (option C, as built) and the rest to the base path
  det_ft      fine-tuned detector, full expression, top-1 + its score (option C: a referring-expression path)
  det_base    base detector, full expression, top-1 + its score       (control for C)

Queries (fixed, seeded; VRSBench val referring):
  present  600 = 150 each of DIOR-image unique / DIOR non-unique / DOTA unique / DOTA non-unique
           (the fine-tune saw DIOR images only, and never these: training excluded every VRSBench-val image)
  absent   300 = present queries with the object class word replaced by a class not referred to anywhere in
           that image, rotating through a 12-class pool so no class dominates (Q-080: Q-009's absent set was
           88 % "airplane"). VRSBench's referring records are not an exhaustive label set, so "absent" is
           "never referred to in the image" - a stated limitation, identical for every condition.

Scored against both ground-truth conventions: VRSBench's floor-quantised `ground_truth` (official) and the
clipped axis-aligned box of `obj_corner` (the Q-008/Q-009 convention). For pipelines, "returned a box" is
whether selected_box is set; for detectors, whether the top-1 score clears a threshold, reported at a sweep so
an operating point can be chosen. Every per-query result goes to a JSONL next to the summary, so any number
can be re-scored or split later.

    .venv/bin/python scripts/eval_grounding_options.py --out results/eval/grounding_options
"""
from __future__ import annotations

import argparse
import collections
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

REFERRING = ROOT / "datasets/raw/vrsbench/VRSBench_EVAL_referring.json"
IMAGES = ROOT / "datasets/raw/vrsbench/images/Images_val"
FT = ROOT / "checkpoints/grounding_dino_rsvg"
BASE = "IDEA-Research/grounding-dino-base"
ABSENT_POOL = ["airplane", "ship", "storage tank", "tennis court", "bridge", "harbor", "windmill",
               "roundabout", "swimming pool", "helicopter", "chimney", "dam"]
THRESHOLDS = [0.15, 0.25, 0.35, 0.5]


def iou(a, b) -> float:
    if not a or not b:
        return 0.0
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def build_queries(seed: int = 0, exclude: set | None = None) -> tuple[list[dict], list[dict]]:
    """exclude: question_ids (and their images) already used, so a confirmation sample is disjoint."""
    recs = json.loads(REFERRING.read_text())
    used_images = set()
    if exclude:
        used_images = {r["image_id"] for r in recs if r["question_id"] in exclude}
    referred = collections.defaultdict(set)
    for r in recs:
        referred[r["image_id"]].add(r["obj_cls"].replace("-", " "))
    strata = collections.defaultdict(list)
    for r in recs:
        if r["image_id"] in used_images:
            continue
        src = "dior" if r["image_id"][0].isdigit() else "dota"
        strata[f"{src}_{'unique' if r['unique'] else 'nonunique'}"].append(r)
    present = []
    for name in sorted(strata):
        for r in random.Random(seed).sample(strata[name], 150):
            present.append({**r, "stratum": name})
    absent, k = [], 0
    for r in present:
        if len(absent) == 300:
            break
        cls = r["obj_cls"].replace("-", " ")
        q = r["question"]
        hit = next((w for w in (cls + "s", cls) if w in q.lower()), None)
        if not hit:
            continue
        for j in range(len(ABSENT_POOL)):
            miss = ABSENT_POOL[(k + j) % len(ABSENT_POOL)]
            if miss not in referred[r["image_id"]] and miss != cls:
                break
        else:
            continue
        k += 1
        i = q.lower().index(hit)
        absent.append({"question_id": r["question_id"], "image_id": r["image_id"], "stratum": r["stratum"],
                       "question": q[:i] + miss + q[i + len(hit):], "absent_class": miss, "true_class": cls})
    return present, absent


def gts(r: dict, w: int, h: int) -> dict:
    x1, y1, x2, y2 = (float(v) for v in r["ground_truth"].strip("{}<>").split("><"))
    xs, ys = r["obj_corner"][0::2], r["obj_corner"][1::2]
    c = [max(0.0, min(xs)) * w, max(0.0, min(ys)) * h, min(1.0, max(xs)) * w, min(1.0, max(ys)) * h]
    return {"floored": [x1 * w / 100, y1 * h / 100, x2 * w / 100, y2 * h / 100], "corner": c}


def progress(tag: str, i: int, n: int, t0: float) -> None:
    if i % 25 == 0 or i == n:
        el = time.time() - t0
        print(f"eval tag={tag} step={i}/{n} elapsed={el:.1f}s rate={i / max(el, 1e-6):.2f}it/s", flush=True)


def run_pipeline(tag: str, model_id: str, present: list[dict], absent: list[dict], out) -> None:
    from backend.app.evidence.verifier import DetectionVerifier
    from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
    from backend.app.ml.adapters.sam2 import SAM2Adapter
    from backend.app.workflows.grounding import run_grounding_pipeline

    sam, ver = SAM2Adapter(), DetectionVerifier(crop_mode="inset")
    # pipe_ref injects no detector, so the pipeline's own routing picks base or referring from the model registry,
    # exactly as the run_grounding tool calls it; the other pipe_* conditions inject one detector (today's path).
    gd = None if tag == "pipe_ref" else GroundingDINOAdapter()
    if gd is not None:
        gd.model_id = model_id
    for kind, qs in (("present", present), ("absent", absent)):
        t0 = time.time()
        for i, r in enumerate(qs, 1):
            img = np.asarray(Image.open(IMAGES / r["image_id"]).convert("RGB"))
            res = run_grounding_pipeline(image=img, query=r["question"], grounding_adapter=gd,
                                         sam2_adapter=sam, verifier=ver)
            box = res.get("selected_box")
            d = res.get("agent_deliberation") or {}
            out.write(json.dumps({"cond": tag, "kind": kind, "question_id": r["question_id"], "stratum": r["stratum"],
                                  "box": box, "decision": d.get("decision"), "mode": d.get("mode"),
                                  "strategy": res.get("strategy"), "detector": res.get("detector"),
                                  "score": res.get("grounding_score")}) + "\n")
            progress(f"{tag}_{kind}", i, len(qs), t0)
    if gd is not None:
        gd.unload()
    sam.unload()
    if tag == "pipe_ref":
        from backend.app.ml.registry import model_registry
        model_registry.unload_all()
    torch.cuda.empty_cache()


@torch.no_grad()
def run_detector(tag: str, model_id: str, present: list[dict], absent: list[dict], out) -> None:
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    proc = AutoProcessor.from_pretrained(BASE)  # one processor for both, as in the fine-tune's own evaluation
    model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(dev).eval()
    for kind, qs in (("present", present), ("absent", absent)):
        t0 = time.time()
        for i, r in enumerate(qs, 1):
            img = Image.open(IMAGES / r["image_id"]).convert("RGB")
            w, h = img.size
            text = r["question"].lower().strip().rstrip(".").strip() + "."
            enc = {k: v.to(dev) for k, v in proc(images=img, text=[text], return_tensors="pt").items()}
            with torch.autocast("cuda", dtype=torch.float16, enabled=dev.type == "cuda"):
                o = model(**enc)
            s = o.logits.sigmoid().float().max(-1).values[0]
            q = int(s.argmax())
            cx, cy, bw, bh = o.pred_boxes[0, q].float().tolist()
            box = [max(0.0, (cx - bw / 2) * w), max(0.0, (cy - bh / 2) * h), min(w, (cx + bw / 2) * w), min(h, (cy + bh / 2) * h)]
            out.write(json.dumps({"cond": tag, "kind": kind, "question_id": r["question_id"], "stratum": r["stratum"],
                                  "box": [round(v, 2) for v in box], "score": round(float(s[q]), 4)}) + "\n")
            progress(f"{tag}_{kind}", i, len(qs), t0)
    del model
    torch.cuda.empty_cache()


def mcnemar(a: list[bool], b: list[bool]) -> dict:
    """Exact two-sided McNemar on paired correct/incorrect outcomes."""
    from math import comb
    n01 = sum(1 for x, y in zip(a, b) if not x and y)
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n = n01 + n10
    p = min(1.0, 2 * sum(comb(n, k) for k in range(0, min(n01, n10) + 1)) / 2 ** n) if n else 1.0
    return {"only_b_correct": n01, "only_a_correct": n10, "p_value": p}


def summarise(rows: list[dict], present: list[dict]) -> dict:
    by_q = {r["question_id"]: r for r in present}
    sizes = {qid: Image.open(IMAGES / r["image_id"]).size for qid, r in by_q.items()}
    res, correct = {}, {}
    for cond in sorted({r["cond"] for r in rows}):
        pr = [r for r in rows if r["cond"] == cond and r["kind"] == "present"]
        ab = [r for r in rows if r["cond"] == cond and r["kind"] == "absent"]
        out = {}
        for conv in ("floored", "corner"):
            hits = {r["question_id"]: iou(r["box"], gts(by_q[r["question_id"]], *sizes[r["question_id"]])[conv]) >= 0.5
                    for r in pr}
            correct[(cond, conv)] = hits
            per = collections.defaultdict(list)
            for r in pr:
                per[r["stratum"]].append(hits[r["question_id"]])
            out[f"acc@0.5_{conv}"] = round(float(np.mean(list(hits.values()))), 4)
            out[f"acc@0.5_{conv}_by_stratum"] = {k: round(float(np.mean(v)), 4) for k, v in sorted(per.items())}
        if cond == "pipe_ref":  # which path served each query
            out["served_by"] = dict(collections.Counter(f"{r['kind']}:{r.get('detector')}" for r in pr + ab))
        if cond.startswith("pipe"):
            out["absent_returned_a_box"] = round(float(np.mean([bool(r["box"]) for r in ab])), 4)
            out["present_returned_a_box"] = round(float(np.mean([bool(r["box"]) for r in pr])), 4)
        else:  # detector: an operating point is a score threshold below which it answers "not found"
            sweep = {}
            for t in THRESHOLDS:
                kept = [r["score"] >= t for r in pr]
                hit_and_kept = [k and correct[(cond, "floored")][r["question_id"]] for k, r in zip(kept, pr)]
                sweep[str(t)] = {"present_answered": round(float(np.mean(kept)), 4),
                                 "present_acc@0.5_floored_counting_not_found_as_wrong": round(float(np.mean(hit_and_kept)), 4),
                                 "absent_returned_a_box": round(float(np.mean([r["score"] >= t for r in ab])), 4)}
            out["threshold_sweep"] = sweep
        res[cond] = out
    tests = {}
    for a, b in (("pipe_base", "det_ft"), ("pipe_base", "pipe_ft"), ("det_base", "det_ft"),
                 ("pipe_base", "pipe_ref"), ("det_ft", "pipe_ref")):
        if (a, "floored") in correct and (b, "floored") in correct:
            qs = sorted(correct[(a, "floored")])
            tests[f"{a}_vs_{b}"] = mcnemar([correct[(a, "floored")][q] for q in qs], [correct[(b, "floored")][q] for q in qs])
    return {"conditions": res, "paired_tests_floored": tests}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results/eval/grounding_options"))
    ap.add_argument("--only", nargs="*", default=["det_base", "det_ft", "pipe_base", "pipe_ft"])
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--exclude", default=None, help="queries.json of an earlier run: its images are excluded")
    args = ap.parse_args()
    excl = None
    if args.exclude:
        q = json.loads(Path(args.exclude).read_text())
        excl = {r["question_id"] for r in q["present"]} | {r["question_id"] for r in q["absent"]}
    present, absent = build_queries(args.seed, excl)
    if args.smoke:
        present, absent = present[::60][:10], absent[:6]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "queries.json").write_text(json.dumps({"present": present, "absent": absent}, indent=1))
    n = {"present": len(present), "absent": len(absent)}
    print("tiles:", json.dumps({"vrsbench_referring": {"train": 0, "val": n["absent"], "test": n["present"]}}), flush=True)
    evals = {f"{c}_{k}": n[k] for c in args.only for k in ("present", "absent")}
    print("plan:", json.dumps({"epochs": 0, "train_steps": 0, "eval": evals, "baseline": list(evals),
                               "per_epoch": [], "final": []}), flush=True)
    rows_path = out_dir / "per_query.jsonl"
    done = {(r["cond"], r["kind"], r["question_id"]) for r in map(json.loads, rows_path.read_text().splitlines())} \
        if rows_path.exists() else set()
    with rows_path.open("a") as out:
        for cond in args.only:
            if all((cond, k, r["question_id"]) in done for k, qs in (("present", present), ("absent", absent)) for r in qs):
                continue  # resumable: a finished condition is not re-run
            model_id = str(FT) if cond.endswith("_ft") else BASE
            (run_pipeline if cond.startswith("pipe") else run_detector)(cond, model_id, present, absent, out)
            out.flush()
            (out_dir / f"{cond}.complete").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    rows = list({(r["cond"], r["kind"], r["question_id"]): r  # a resumed run may repeat a row; last one wins
                 for r in map(json.loads, rows_path.read_text().splitlines())}.values())
    summary = summarise(rows, present) | {"queries": n, "absent_pool": ABSENT_POOL,
                                          "ground_truth": "floored = VRSBench ground_truth (official); corner = clipped obj_corner AABB"}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
