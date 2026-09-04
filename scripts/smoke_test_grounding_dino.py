#!/usr/bin/env python3
"""
SATQUERY AI — Production Grounding DINO Real Smoke Test
Runs real inference using GroundingDINOAdapter on an authentic local satellite image.
Visualizes candidate bounding boxes and saves overlay artifact.
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
from backend.app.exceptions import ModelUnavailableError, InferenceError


def main():
    parser = argparse.ArgumentParser(description="Real Grounding DINO Smoke Test")
    parser.add_argument(
        "--image",
        type=str,
        default="datasets/samples/real_pair/real_image_b.png",
        help="Path to real local satellite image"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="small vehicle.",
        help="Target text prompt (e.g. 'small vehicle.')"
    )
    parser.add_argument(
        "--box-threshold",
        type=float,
        default=0.25,
        help="Confidence threshold for candidate bounding boxes"
    )
    parser.add_argument(
        "--text-threshold",
        type=float,
        default=0.20,
        help="Confidence threshold for text token association"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Directory to save output artifacts"
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.is_file():
        print(f"[ERROR] INVALID_INPUT: Image file not found at '{image_path}'.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("============================================================")
    print("GROUNDING DINO REAL SMOKE TEST")
    print("============================================================")
    print(f"Image: {image_path}")
    print(f"Query: '{args.query}'")
    print(f"Box Threshold: {args.box_threshold}")
    print(f"Text Threshold: {args.text_threshold}")
    print("")

    # 1. Instantiate Adapter
    adapter = GroundingDINOAdapter()
    print(f"Adapter: {adapter.__class__.__name__} ({adapter.name})")
    print(f"Device:  {adapter.device}")

    # 2. Explicit Model Loading
    print("Loading Grounding DINO model and processor...")
    load_start = time.perf_counter()
    try:
        adapter.load()
    except (ModelUnavailableError, Exception) as e:
        print(f"[FAIL] MODEL_LOAD_ERROR: Failed to load Grounding DINO: {e}", file=sys.stderr)
        sys.exit(2)
    load_time = time.perf_counter() - load_start
    print(f"Model loaded successfully in {load_time:.2f} seconds.")
    print("")

    # 3. Real Inference
    print("Executing real Grounding DINO detector inference...")
    infer_start = time.perf_counter()
    try:
        result = adapter.predict(
            image_or_context=str(image_path),
            prompt=args.query,
            box_threshold=args.box_threshold,
            text_threshold=args.text_threshold
        )
    except InferenceError as e:
        print(f"[FAIL] MODEL_INFERENCE_ERROR: Grounding DINO inference failed: {e}", file=sys.stderr)
        sys.exit(3)
    infer_time = time.perf_counter() - infer_start

    boxes = result.get("boxes", [])
    print(f"Inference completed in {infer_time:.3f} seconds.")
    print(f"Candidate boxes detected: {len(boxes)}")
    print("")

    # 4. Print all returned candidate boxes with genuine scores
    print("Detected Candidate Boxes:")
    print("------------------------------------------------------------")
    if not boxes:
        print("  (No candidate boxes detected above threshold)")
    for i, b in enumerate(boxes, start=1):
        x1, y1, x2, y2 = b["xyxy"]
        score = b["score"]
        label = b["label"]
        w = round(x2 - x1, 1)
        h = round(y2 - y1, 1)
        print(f"  [{i}] Label: '{label}' | Score: {score:.4f} | Box: [{x1}, {y1}, {x2}, {y2}] | Size: {w}x{h} px")
    print("------------------------------------------------------------")
    print("")

    # 5. Create and Save Overlay Image
    image_pil = Image.open(image_path).convert("RGB")
    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    ax.imshow(image_pil)

    colors = ["#00FF66", "#00E5FF", "#FFD700", "#FF3366", "#FF9900"]
    for i, b in enumerate(boxes):
        x1, y1, x2, y2 = b["xyxy"]
        score = b["score"]
        label = b["label"]
        color = colors[i % len(colors)]

        # Add rectangle patch
        rect = patches.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            linewidth=2.0,
            edgecolor=color,
            facecolor="none",
            linestyle="-"
        )
        ax.add_patch(rect)

        # Label annotation
        caption = f"{label} ({score:.2f})"
        ax.text(
            x1,
            max(0, y1 - 4),
            caption,
            color="black",
            fontsize=8.5,
            fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.2", facecolor=color, edgecolor="none", alpha=0.85)
        )

    ax.set_title(
        f"Grounding DINO Real Detection: '{args.query}'\n"
        f"Detected: {len(boxes)} candidates | Avg Score: {result.get('confidence', 0.0) or 0.0:.3f} | Time: {infer_time:.2f}s",
        fontsize=11,
        fontweight="bold"
    )
    ax.axis("off")

    overlay_path = out_dir / "grounding_dino_smoke_test.png"
    plt.savefig(overlay_path, bbox_inches="tight", dpi=180)
    plt.close(fig)

    # 6. Save JSON Audit
    json_path = out_dir / "grounding_dino_smoke_test.json"
    audit_data = {
        "status": "PASS",
        "model_name": adapter.name,
        "model_id": adapter.model_id,
        "device": str(adapter.device),
        "image": str(image_path),
        "query": args.query,
        "box_threshold": args.box_threshold,
        "text_threshold": args.text_threshold,
        "inference_time_seconds": round(infer_time, 4),
        "candidate_count": len(boxes),
        "boxes": boxes,
        "confidence": result.get("confidence")
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print("Artifacts Saved:")
    print(f"  Overlay Image: {overlay_path}")
    print(f"  JSON Audit:    {json_path}")
    print("============================================================")
    print("STATUS: GROUNDING_DINO_SMOKE_TEST_PASS")


if __name__ == "__main__":
    main()
