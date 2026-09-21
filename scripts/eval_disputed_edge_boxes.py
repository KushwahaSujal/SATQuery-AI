#!/usr/bin/env python3
"""
SatQuery AI — the two DISPUTED answers on `05945_0000.png`, under each verifier crop geometry.

Q-009 §3 recorded that "segment the largest building" and "find the white car at the bottom left"
return the single agent's correct box labelled DISPUTED, that both boxes touch the image edge, and
that "the black-padded crop is the likely cause". This runs the real grounding pipeline (Grounding
DINO + V4 reasoner + SAM 2 + RemoteCLIP verifier) for both queries once per crop geometry, with the
detector and segmenter loaded once and shared, so the only thing that differs between runs is
`DetectionVerifier.crop`.

Usage: .venv/bin/python scripts/eval_disputed_edge_boxes.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.evidence.verifier import DetectionVerifier
from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
from backend.app.ml.adapters.sam2 import SAM2Adapter
from backend.app.workflows.grounding import run_grounding_pipeline

IMAGE = PROJECT_ROOT / "tests/data/grounding/05945_0000.png"
QUERIES = ["segment the largest building", "find the white car at the bottom left"]
OUT = PROJECT_ROOT / "results/evaluations/disputed_edge_boxes_05945_20260921.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=list(DetectionVerifier.CROP_MODES))
    ap.add_argument("--image", default=str(IMAGE))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    img = Image.open(args.image).convert("RGB")
    print(f"image {args.image} size {img.size}")
    gd, sam = GroundingDINOAdapter(), SAM2Adapter()
    results = {}
    try:
        for mode in args.modes:
            verifier = DetectionVerifier(crop_mode=mode)
            results[mode] = {}
            for query in QUERIES:
                res = run_grounding_pipeline(
                    image=np.asarray(img), query=query,
                    grounding_adapter=gd, sam2_adapter=sam, verifier=verifier,
                )
                delib = res.get("agent_deliberation", {}) or {}
                attempts = delib.get("attempts", [])
                last = attempts[-1] if attempts else {}
                box = res.get("selected_box")
                crop_box = None
                if box:
                    _, crop_box = verifier.crop(img, box)
                results[mode][query] = {
                    "decision": delib.get("decision"),
                    "mode": delib.get("mode"),
                    "verifier_status": last.get("verifier_status"),
                    "verifier_confidence": last.get("verifier_confidence"),
                    "verifier_rank": last.get("verifier_rank"),
                    "verifier_top_matches": last.get("verifier_top_matches"),
                    "selected_box": [round(float(v), 1) for v in box] if box else None,
                    "crop_box": crop_box,
                    "crop_out_of_frame": bool(crop_box and (
                        crop_box[0] < 0 or crop_box[1] < 0
                        or crop_box[2] > img.size[0] or crop_box[3] > img.size[1])),
                    "detector_confidence": last.get("detector_confidence"),
                    "answer": res.get("answer"),
                }
                print(f"\n[{mode}] {query}")
                print(json.dumps(results[mode][query], indent=2))
    finally:
        for a in (gd, sam):
            try:
                a.unload()
            except Exception:
                pass
        try:
            DetectionVerifier().clip.unload()
        except Exception:
            pass

    Path(args.out).write_text(json.dumps({"image": args.image, "modes": results}, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
