#!/usr/bin/env python3
"""
SatQuery AI — End-to-end workflow showcase.

Runs ONE real query through the complete production agent pipeline
(AgentController.run_pipeline) on a real VRSBench image with a real
ground-truth box, and prints every observable stage.

This is the material for the presentation's "workflow" slide: every number
printed is measured on this run, nothing is illustrative.

Usage:
    python scripts/showcase_workflow.py
    python scripts/showcase_workflow.py --image P0331_0012.png --query "..."
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

IMG_DIR = PROJECT_ROOT / "datasets/raw/vrsbench/images/Images_val"
ANN = PROJECT_ROOT / "datasets/raw/vrsbench/VRSBench_EVAL_referring.json"
GT_RE = re.compile(r"<\s*(\d+(?:\.\d+)?)\s*>")

# Default: 4 DINO candidates, so the V4 reasoner's selection is actually exercised.
DEFAULT_IMAGE = "07359_0000.png"
DEFAULT_QUERY = "The stadium is located at the bottom middle of the frame."


def gt_for(image_id: str, query: str, w: int, h: int):
    for r in json.loads(ANN.read_text()):
        if r["image_id"] == image_id and r["question"].strip() == query.strip():
            v = [float(x) for x in GT_RE.findall(r["ground_truth"])]
            if len(v) == 4:
                return [v[0] / 100 * w, v[1] / 100 * h, v[2] / 100 * w, v[3] / 100 * h]
    return None


def iou(a, b):
    if not a or not b:
        return 0.0
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def rule(t=""):
    print("\n" + "=" * 78)
    if t:
        print(t)
        print("=" * 78)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    args = ap.parse_args()

    from PIL import Image
    from backend.app.agent.state import AgentState
    from backend.app.agent.controller import agent_controller
    from backend.app.artifacts.manager import artifact_manager

    src = IMG_DIR / args.image
    if not src.is_file():
        print(f"[ERROR] image not found: {src}", file=sys.stderr)
        return 1

    with Image.open(src) as im:
        W, H = im.size

    job_id = f"showcase-{uuid.uuid4().hex[:8]}"
    dirs = artifact_manager.init_job_workspace(job_id)
    dst = dirs["input"] / args.image if "input" in dirs else PROJECT_ROOT / "results" / job_id / args.image
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)

    rule("SATQUERY AI — END-TO-END WORKFLOW SHOWCASE")
    print(f"  job id   : {job_id}")
    print(f"  image    : {args.image}   ({W}x{H} px, VRSBench official val split)")
    print(f"  query    : \"{args.query}\"")

    state = AgentState(request_id=job_id, query=args.query, image_paths=[str(dst)])

    t0 = time.perf_counter()
    resp = await agent_controller.run_pipeline(state)
    total_ms = (time.perf_counter() - t0) * 1000

    # ---- Stage 1: agentic routing decision -------------------------------
    rule("STAGE 1 — AGENTIC ROUTING (no model weights involved)")
    orch = resp.orchestration or {}
    ent = orch.get("query_entities", {})
    print(f"  capability selected : {orch.get('capability_id')}  ({orch.get('capability_name')})")
    print(f"  routing confidence  : {orch.get('routing_confidence')}")
    print(f"  task type           : {resp.task.value if hasattr(resp.task,'value') else resp.task}")
    print(f"  workflow            : {resp.workflow_id}")
    print(f"  why                 : {resp.workflow_reason}")
    print(f"  entities extracted  :")
    for k, v in ent.items():
        if v not in (None, False, "", []):
            print(f"      {k:<18} = {v}")

    # ---- Stage 2: execution DAG ------------------------------------------
    rule("STAGE 2 — EXECUTION PLAN (DAG)")
    dag = orch.get("dag_plan", {})
    print(f"  plan id  : {dag.get('plan_id')}")
    print(f"  budget   : {dag.get('total_estimated_timeout')} s")
    for i, stage in enumerate(dag.get("execution_order", []), 1):
        print(f"    stage {i}: {', '.join(stage)}")
    print(f"  models   : {', '.join(resp.models_used) or '(none)'}")

    # ---- Stage 3: observable trace ---------------------------------------
    rule("STAGE 3 — OBSERVABLE EXECUTION TRACE")
    print(f"  {'#':<3} {'step':<34} {'tool/model':<18} {'status':<8} {'ms':>8}")
    print("  " + "-" * 74)
    for i, s in enumerate(resp.execution_trace, 1):
        d = s.model_dump() if hasattr(s, "model_dump") else dict(s)
        dur = d.get("duration_ms")
        who = d.get("tool") or d.get("model") or ""
        print(f"  {i:<3} {str(d.get('step'))[:34]:<34} {str(who)[:18]:<18} "
              f"{str(d.get('status')):<8} {(f'{dur:.1f}' if isinstance(dur,(int,float)) else '-'):>8}")

    # ---- Stage 4: evidence + accuracy ------------------------------------
    rule("STAGE 4 — EVIDENCE & MEASURED ACCURACY")
    sp = resp.evidence.spatial if resp.evidence else None
    pred = None
    if sp and sp.boxes:
        b = sp.boxes[0]
        bd = b.model_dump() if hasattr(b, "model_dump") else dict(b)
        for key in ("xyxy", "box", "bbox", "coordinates"):
            if bd.get(key):
                pred = list(bd[key])
                break
    print(f"  answer      : {resp.answer}")
    print(f"  confidence  : {resp.confidence}")
    print(f"  has mask    : {getattr(sp,'has_mask',None)}")
    if getattr(sp, "statistics", None):
        st = sp.statistics
        st = st.model_dump() if hasattr(st, "model_dump") else st
        for k in ("estimated_area_sq_m", "changed_pixels", "mask_pixel_count"):
            if st.get(k) is not None:
                print(f"  {k:<12}: {st[k]}")

    gt = gt_for(args.image, args.query, W, H)
    if gt and pred:
        print(f"\n  predicted box : {[round(v,1) for v in pred]}")
        print(f"  ground truth  : {[round(v,1) for v in gt]}   (VRSBench official)")
        print(f"  IoU           : {iou(pred, gt):.4f}")
    elif gt:
        print(f"\n  ground truth  : {[round(v,1) for v in gt]}   (no predicted box exposed in evidence)")

    # ---- Stage 5: artifacts ----------------------------------------------
    rule("STAGE 5 — ARTIFACTS WRITTEN TO DISK")
    for kind, files in (resp.artifacts or {}).items():
        for f in files:
            print(f"  {kind:<12} {f}")
    ws = PROJECT_ROOT / "results" / job_id
    if ws.is_dir():
        for p in sorted(ws.rglob("*")):
            if p.is_file():
                print(f"  [{p.stat().st_size/1024:8.1f} KB] {p.relative_to(PROJECT_ROOT)}")

    rule("SUMMARY")
    print(f"  status            : {resp.status.value if hasattr(resp.status,'value') else resp.status}")
    print(f"  end-to-end latency: {total_ms:.0f} ms")
    print(f"  warnings          : {len(resp.warnings)}  errors: {len(resp.errors)}")
    for w in resp.warnings:
        print(f"      ! {w}")
    for e in resp.errors:
        print(f"      X {e}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
