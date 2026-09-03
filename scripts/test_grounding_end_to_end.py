#!/usr/bin/env python3
"""
SATQUERY AI — End-to-End Real Grounding Integration Test
Executes the full chain on authentic local satellite imagery:
Natural Query -> Grounding DINO -> Candidates -> V4 Reasoning -> Selected Box -> SAM 2 -> Final Mask.
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

from backend.app.models.grounding_dino import GroundingDINOAdapter
from backend.app.models.sam2 import SAM2Adapter
from backend.app.workflows.grounding_reasoner import parse_v4_query, run_v4_reasoning


def main():
    parser = argparse.ArgumentParser(description="End-to-End Real Grounding Integration Test")
    parser.add_argument(
        "--image",
        type=str,
        default="datasets/samples/real_pair/real_image_b.png",
        help="Path to real satellite image"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="The small dark-colored vehicle located at the top-right corner of the image.",
        help="Natural language referring expression query"
    )
    parser.add_argument(
        "--box-threshold",
        type=float,
        default=0.20,
        help="Grounding DINO box detection threshold"
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
        print(f"[ERROR] Satellite image not found at '{image_path}'.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("============================================================")
    print("SATQUERY AI — END-TO-END REAL GROUNDING INTEGRATION TEST")
    print("============================================================")
    total_start = time.perf_counter()

    # Step 1: Load and validate image
    image_pil = Image.open(image_path).convert("RGB")
    width, height = image_pil.size
    print(f"Satellite image: {image_path} ({width}x{height} pixels)")
    print(f"Input Query:     \"{args.query}\"")
    print("")

    # Step 2: Parse natural-language query
    parsed = parse_v4_query(args.query)
    clean_prompt = parsed.get("clean_prompt") or f"{parsed.get('category', 'object')}."

    # Step 3: Run Grounding DINO Detection
    print("1. Executing Grounding DINO Detection...")
    gd_adapter = GroundingDINOAdapter()
    t_gd_start = time.perf_counter()
    gd_adapter.load()
    det_res = gd_adapter.predict(
        image_or_context=image_pil,
        prompt=clean_prompt,
        box_threshold=args.box_threshold
    )
    t_gd = time.perf_counter() - t_gd_start
    raw_candidates = det_res.get("boxes", [])
    print(f"   Detector finished in {t_gd:.2f}s.")
    print(f"   Candidates detected: {len(raw_candidates)}")
    print("")

    # Step 4: Run V4 Multi-Attribute Spatial Reasoning
    print("2. Executing V4 Multi-Attribute Reasoning...")
    t_v4_start = time.perf_counter()
    reasoning_res = run_v4_reasoning(
        candidates=raw_candidates,
        query=args.query,
        img_shape=(height, width),
        image=image_pil,
        adapter=gd_adapter,
        iou_nms_threshold=0.50
    )
    t_v4 = time.perf_counter() - t_v4_start

    selected_cand = reasoning_res.get("selected_box")
    strategy = reasoning_res.get("strategy", "unknown")
    ranked_candidates = reasoning_res.get("candidates", [])

    if not selected_cand:
        print("[FAIL] Reasoning layer could not select a candidate.", file=sys.stderr)
        sys.exit(2)

    selected_box = selected_cand["xyxy"]
    det_score = float(selected_cand.get("score", 0.0))
    reasoning_score = float(selected_cand.get("reasoning_score", 0.0))
    reasoning_scores = selected_cand.get("reasoning_scores", {})

    print(f"   Reasoning finished in {t_v4:.4f}s.")
    print(f"   Strategy: {strategy}")
    print(f"   Selected Candidate Box: {selected_box}")
    print(f"   Detector Score:         {det_score:.4f}")
    print(f"   Reasoning Score:        {reasoning_score:.4f}")
    print(f"   Component Scores:       {reasoning_scores}")
    print("")

    # Step 5: Run SAM 2 Promptable Segmentation with Real Selected Box
    print("3. Executing SAM 2 High-Precision Segmentation...")
    sam2_adapter = SAM2Adapter()
    t_sam_start = time.perf_counter()
    sam2_adapter.load()
    sam2_res = sam2_adapter.predict(
        image_or_context=image_pil,
        box=selected_box,
        multimask_output=True
    )
    t_sam = time.perf_counter() - t_sam_start

    final_mask = sam2_res.mask
    sam2_score = float(sam2_res.score)
    mask_h, mask_w = final_mask.shape
    pixel_count = int(sam2_res.pixel_count)

    total_runtime = time.perf_counter() - total_start

    # ============================================================
    # PRINT REQUIRED METRICS EXACTLY AS REQUESTED
    # ============================================================
    print("============================================================")
    print("END-TO-END GROUNDING RESULTS")
    print("============================================================")
    print(f"- parsed query: {json.dumps(parsed, indent=2)}")
    print(f"- number of Grounding DINO candidates: {len(raw_candidates)}")
    print("- each candidate score:")
    for idx, cand in enumerate(raw_candidates):
        b = cand["xyxy"]
        sc = cand.get("score", 0.0)
        lbl = cand.get("label", "vehicle")
        print(f"    [{idx+1:02d}] box: [{b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}] | score: {sc:.4f} | label: {lbl}")
    print(f"- selected candidate: {selected_box} (score: {det_score:.4f}, reasoning: {reasoning_score:.4f})")
    print(f"- V4 strategy: {strategy}")
    print(f"- SAM2 score: {sam2_score:.4f}")
    print(f"- final mask dimensions: {mask_w}x{mask_h} ({pixel_count:,} pixels)")
    print(f"- total runtime: {total_runtime:.2f}s (detector: {t_gd:.2f}s, reasoning: {t_v4*1000:.1f}ms, SAM2: {t_sam:.2f}s)")
    print("============================================================")
    print("")

    # ============================================================
    # GENERATE 4-PANEL VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(1, 4, figsize=(24, 6), dpi=150)
    plt.subplots_adjust(wspace=0.15)

    # Panel 1: Original Image + All Candidate Boxes
    axes[0].imshow(image_pil)
    for c in raw_candidates:
        bx = c["xyxy"]
        rect = patches.Rectangle(
            (bx[0], bx[1]), bx[2] - bx[0], bx[3] - bx[1],
            linewidth=1.2, edgecolor="#FFCC00", facecolor="none", linestyle="--"
        )
        axes[0].add_patch(rect)
    axes[0].set_title(f"1. Grounding DINO Candidates ({len(raw_candidates)})\nPrompt: '{clean_prompt}'", fontsize=11, fontweight="bold")
    axes[0].axis("off")

    # Panel 2: Selected Candidate Box (V4 Spatial Reasoning)
    axes[1].imshow(image_pil)
    # Background candidates faint
    for c in raw_candidates:
        bx = c["xyxy"]
        rect = patches.Rectangle(
            (bx[0], bx[1]), bx[2] - bx[0], bx[3] - bx[1],
            linewidth=0.8, edgecolor="#888888", facecolor="none", linestyle=":"
        )
        axes[1].add_patch(rect)
    # Selected candidate bold green
    sx1, sy1, sx2, sy2 = selected_box
    rect_sel = patches.Rectangle(
        (sx1, sy1), sx2 - sx1, sy2 - sy1,
        linewidth=2.5, edgecolor="#00FF66", facecolor="none", linestyle="-"
    )
    axes[1].add_patch(rect_sel)
    axes[1].set_title(
        f"2. V4 Reasoning Selection\nTarget: [{sx1:.1f}, {sy1:.1f}, {sx2:.1f}, {sy2:.1f}]",
        fontsize=11,
        fontweight="bold"
    )
    axes[1].axis("off")

    # Panel 3: Real SAM 2 Binary Segmentation Mask
    axes[2].imshow(final_mask, cmap="Blues_r", vmin=0, vmax=1)
    axes[2].set_title(f"3. SAM 2 Binary Mask\nScore: {sam2_score:.4f} | Area: {pixel_count:,} px", fontsize=11, fontweight="bold")
    axes[2].axis("off")

    # Panel 4: Final Overlay
    axes[3].imshow(image_pil)
    colored_mask = np.zeros((height, width, 4), dtype=np.float32)
    colored_mask[final_mask > 0] = [0.0, 0.9, 1.0, 0.60] # Semi-transparent Cyan
    axes[3].imshow(colored_mask)

    rect_fin = patches.Rectangle(
        (sx1, sy1), sx2 - sx1, sy2 - sy1,
        linewidth=2.0, edgecolor="#00FF66", facecolor="none", linestyle="-"
    )
    axes[3].add_patch(rect_fin)
    axes[3].set_title(f"4. Final Grounding + Segmentation Overlay\nSAM 2 Confidence: {sam2_score:.4f}", fontsize=11, fontweight="bold")
    axes[3].axis("off")

    plt.suptitle(
        f"SATQUERY AI — End-to-End Real Grounding Pipeline\n"
        f"Query: \"{args.query}\"\n"
        f"Selected Box: [{sx1:.1f}, {sy1:.1f}, {sx2:.1f}, {sy2:.1f}] | SAM 2 Score: {sam2_score:.4f} | Total Time: {total_runtime:.2f}s",
        fontsize=12,
        fontweight="heavy",
        y=0.98
    )

    vis_path = out_dir / "grounding_end_to_end_test.png"
    plt.savefig(vis_path, bbox_inches="tight", dpi=180)
    plt.close(fig)

    # Save JSON Audit
    json_path = out_dir / "grounding_end_to_end_test.json"
    audit_data = {
        "status": "PASS",
        "query": args.query,
        "parsed_query": parsed,
        "image": str(image_path),
        "image_dimensions": {"width": width, "height": height},
        "candidates_count": len(raw_candidates),
        "candidates": [
            {
                "xyxy": c["xyxy"],
                "score": round(float(c.get("score", 0.0)), 4),
                "label": c.get("label", "vehicle")
            }
            for c in raw_candidates
        ],
        "v4_strategy": strategy,
        "selected_candidate": {
            "xyxy": selected_box,
            "detector_score": round(det_score, 4),
            "reasoning_score": round(reasoning_score, 4),
            "reasoning_scores": reasoning_scores
        },
        "sam2_score": round(sam2_score, 4),
        "final_mask_dimensions": {"width": mask_w, "height": mask_h},
        "final_mask_pixel_count": pixel_count,
        "timing_seconds": {
            "grounding_dino": round(t_gd, 3),
            "v4_reasoning": round(t_v4, 5),
            "sam2": round(t_sam, 3),
            "total": round(total_runtime, 3)
        }
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print(f"Artifacts Saved:")
    print(f"  Visualization: {vis_path}")
    print(f"  JSON Audit:    {json_path}")
    print("STATUS: GROUNDING_END_TO_END_PASS")


if __name__ == "__main__":
    main()
