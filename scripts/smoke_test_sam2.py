#!/usr/bin/env python3
"""
SATQUERY AI — Production SAM 2 Real Smoke Test
Executes real SAM 2 promptable segmentation using SAM2Adapter on an authentic local satellite image.
Visualizes the input bounding box and the resulting high-precision mask.
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

from backend.app.models.sam2 import SAM2Adapter
from backend.app.exceptions import ModelUnavailableError, InferenceError


def main():
    parser = argparse.ArgumentParser(description="Real SAM 2 Smoke Test")
    parser.add_argument(
        "--image",
        type=str,
        default="datasets/samples/real_pair/real_image_b.png",
        help="Path to real local satellite image"
    )
    parser.add_argument(
        "--box",
        type=str,
        default="46.5,177.42,60.9,187.07",
        help="Input bounding box as x1,y1,x2,y2"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Directory to save smoke test artifacts"
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.is_file():
        print(f"[ERROR] Image file not found at '{image_path}'.", file=sys.stderr)
        sys.exit(1)

    try:
        box_coords = [float(v.strip()) for v in args.box.split(",")]
        assert len(box_coords) == 4
    except Exception as e:
        print(f"[ERROR] Invalid box format '{args.box}'. Expected 'x1,y1,x2,y2': {e}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    image_pil = Image.open(image_path).convert("RGB")
    width, height = image_pil.size

    print("============================================================")
    print("SAM 2 REAL SMOKE TEST")
    print("============================================================")
    print(f"Image: {image_path}")
    print(f"Image dimensions: {width}x{height}")
    print(f"Input box: {box_coords}")
    print("")

    # 1. Instantiate Adapter
    adapter = SAM2Adapter()
    print(f"Adapter: {adapter.__class__.__name__} ({adapter.name})")
    print(f"Model ID: {adapter.model_id}")
    print(f"Device:   {adapter.device}")

    # 2. Load Model
    print("Loading SAM 2 predictor...")
    load_start = time.perf_counter()
    try:
        adapter.load()
    except (ModelUnavailableError, Exception) as e:
        print(f"[FAIL] MODEL_LOAD_ERROR: Failed to load SAM 2: {e}", file=sys.stderr)
        sys.exit(2)
    load_time = time.perf_counter() - load_start
    print(f"SAM 2 model loaded in {load_time:.2f} seconds.")
    print("")

    # 3. Run Real Inference
    print("Executing SAM 2 segmentation from bounding box prompt...")
    infer_start = time.perf_counter()
    try:
        result = adapter.predict(
            image_or_context=image_pil,
            box=box_coords
        )
    except InferenceError as e:
        print(f"[FAIL] MODEL_INFERENCE_ERROR: SAM 2 inference failed: {e}", file=sys.stderr)
        sys.exit(3)
    infer_time = time.perf_counter() - infer_start

    mask = result["mask"]
    score = result["score"]
    scores = result.get("scores", [score])
    pixel_count = result["pixel_count"]
    mask_h, mask_w = mask.shape

    print(f"Inference completed in {infer_time:.3f} seconds.")
    print("")
    print("SAM 2 Numerical Results:")
    print("------------------------------------------------------------")
    print(f"  Image dimensions:    {width}x{height}")
    print(f"  Input box:           {box_coords}")
    print(f"  Number of masks:     {len(scores)}")
    print(f"  Candidate scores:    {[round(s, 4) for s in scores]}")
    print(f"  Selected mask score: {score:.4f}")
    print(f"  Mask dimensions:     {mask_w}x{mask_h}")
    print(f"  Mask pixel count:    {pixel_count:,} pixels")
    print("------------------------------------------------------------")
    print("")

    # 4. Generate Visualization
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=150)
    plt.subplots_adjust(wspace=0.15)

    # Panel 1: Original Image + Input Box
    axes[0].imshow(image_pil)
    x1, y1, x2, y2 = box_coords
    rect = patches.Rectangle(
        (x1, y1), x2 - x1, y2 - y1,
        linewidth=2.0, edgecolor="#00FF66", facecolor="none", linestyle="-"
    )
    axes[0].add_patch(rect)
    axes[0].set_title(f"1. Original Image + Prompt Box\nBox: [{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}]", fontsize=11, fontweight="bold")
    axes[0].axis("off")

    # Panel 2: Selected SAM 2 Binary Mask
    axes[1].imshow(mask, cmap="Blues_r", vmin=0, vmax=1)
    axes[1].set_title(f"2. Selected SAM 2 Mask\nArea: {pixel_count:,} px | Model Score: {score:.4f}", fontsize=11, fontweight="bold")
    axes[1].axis("off")

    # Panel 3: Mask + Box Overlay on Original Image
    axes[2].imshow(image_pil)
    # Alpha mask overlay (cyan)
    colored_mask = np.zeros((height, width, 4), dtype=np.float32)
    colored_mask[mask > 0] = [0.0, 0.9, 1.0, 0.55] # Cyan semi-transparent
    axes[2].imshow(colored_mask)

    rect_overlay = patches.Rectangle(
        (x1, y1), x2 - x1, y2 - y1,
        linewidth=2.0, edgecolor="#FFCC00", facecolor="none", linestyle="--"
    )
    axes[2].add_patch(rect_overlay)
    axes[2].set_title(f"3. SAM 2 Mask + Prompt Overlay\nGenuine Score: {score:.4f}", fontsize=11, fontweight="bold")
    axes[2].axis("off")

    plt.suptitle(
        f"SAM 2 Real Visual Smoke Test ({adapter.model_id})\n"
        f"Selected Mask Score: {score:.4f} • Mask Pixel Count: {pixel_count:,} px",
        fontsize=13,
        fontweight="heavy",
        y=0.98
    )

    vis_path = out_dir / "sam2_smoke_test.png"
    plt.savefig(vis_path, bbox_inches="tight", dpi=180)
    plt.close(fig)

    # 5. Save JSON Audit
    json_path = out_dir / "sam2_smoke_test.json"
    audit_data = {
        "status": "PASS",
        "model_name": adapter.name,
        "model_id": adapter.model_id,
        "device": str(adapter.device),
        "image": str(image_path),
        "image_dimensions": {"width": width, "height": height},
        "input_box": box_coords,
        "candidate_masks_count": len(scores),
        "candidate_scores": scores,
        "selected_mask_score": score,
        "mask_dimensions": {"width": mask_w, "height": mask_h},
        "mask_pixel_count": pixel_count,
        "inference_time_seconds": round(infer_time, 4)
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print("Artifacts Saved:")
    print(f"  Visualization: {vis_path}")
    print(f"  JSON Audit:    {json_path}")
    print("============================================================")
    print("STATUS: SAM2_SMOKE_TEST_PASS")


if __name__ == "__main__":
    main()
