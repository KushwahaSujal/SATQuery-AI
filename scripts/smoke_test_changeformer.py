#!/usr/bin/env python3
"""
SATQUERY AI — ChangeFormer Real Visual Smoke Test
Loads real local remote-sensing images and executes inference using the
production ChangeFormerAdapter and the verified ChangeFormerV6 checkpoint.
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
import numpy as np
from PIL import Image

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Production import - strictly using production adapter
from backend.app.models.changeformer import ChangeFormerAdapter
from backend.app.exceptions import ModelUnavailableError, InferenceError, InvalidInputError


def parse_args():
    parser = argparse.ArgumentParser(description="ChangeFormer Visual Smoke Test")
    parser.add_argument(
        "--image-a",
        type=str,
        default="datasets/samples/real_pair/real_image_a.png",
        help="Path to real earlier satellite image A"
    )
    parser.add_argument(
        "--image-b",
        type=str,
        default="datasets/samples/real_pair/real_image_b.png",
        help="Path to real later satellite image B"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Change probability threshold (default: 0.5)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Directory to save visual and JSON artifacts"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img_a_path = Path(args.image_a)
    img_b_path = Path(args.image_b)

    # 1. Input Validation
    if not img_a_path.is_file():
        print(f"\n[ERROR] INVALID_INPUT_PAIR: Real image A not found at '{img_a_path}'.", file=sys.stderr)
        print("Real sample images are required. Do not use synthetic or fabricated images.", file=sys.stderr)
        sys.exit(1)

    if not img_b_path.is_file():
        print(f"\n[ERROR] INVALID_INPUT_PAIR: Real image B not found at '{img_b_path}'.", file=sys.stderr)
        print("Real sample images are required. Do not use synthetic or fabricated images.", file=sys.stderr)
        sys.exit(1)

    try:
        image_a = Image.open(img_a_path).convert("RGB")
        image_b = Image.open(img_b_path).convert("RGB")
    except Exception as e:
        print(f"\n[ERROR] INVALID_INPUT_PAIR: Failed to load input images: {e}", file=sys.stderr)
        sys.exit(1)

    width_a, height_a = image_a.size
    width_b, height_b = image_b.size

    # 2. Checkpoint & Adapter Initialization
    try:
        adapter = ChangeFormerAdapter()
    except Exception as e:
        print(f"\n[ERROR] MODEL_LOAD_ERROR: Failed to instantiate ChangeFormerAdapter: {e}", file=sys.stderr)
        sys.exit(1)

    ckpt_path = adapter._resolve_checkpoint_path()
    if not ckpt_path.is_file():
        print(f"\n[ERROR] MODEL_CHECKPOINT_MISSING: Checkpoint not found at '{ckpt_path}'.", file=sys.stderr)
        sys.exit(1)

    try:
        adapter.load_model()
    except ModelUnavailableError as e:
        print(f"\n[ERROR] MODEL_CHECKPOINT_MISSING: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] MODEL_LOAD_ERROR: Failed to load checkpoint weights: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Actual Inference Execution (timed)
    start_time = time.perf_counter()
    try:
        result = adapter.predict(image_a, image_b, threshold=args.threshold)
    except InferenceError as e:
        print(f"\n[ERROR] MODEL_INFERENCE_ERROR: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] MODEL_INFERENCE_ERROR: Unexpected failure during inference: {e}", file=sys.stderr)
        sys.exit(1)
    inference_time = time.perf_counter() - start_time

    # 4. Output Validation
    if not result.masks or len(result.masks) == 0:
        print("\n[ERROR] INVALID_OUTPUT_SHAPE: No change mask produced by ChangeFormer.", file=sys.stderr)
        sys.exit(1)

    mask_dict = result.masks[0]
    binary_mask = mask_dict.get("binary_mask")
    change_prob_map = mask_dict.get("change_prob_map")
    logits = mask_dict.get("logits")

    if binary_mask is None or change_prob_map is None or logits is None:
        print("\n[ERROR] INVALID_OUTPUT_SHAPE: Incomplete model output tensors.", file=sys.stderr)
        sys.exit(1)

    expected_hw = (height_a, width_a)
    if binary_mask.shape != expected_hw or change_prob_map.shape != expected_hw:
        print(
            f"\n[ERROR] INVALID_OUTPUT_SHAPE: Output shape {binary_mask.shape} does not match input dimensions {expected_hw}.",
            file=sys.stderr
        )
        sys.exit(1)

    # Finite values check
    if not (np.all(np.isfinite(logits)) and np.all(np.isfinite(change_prob_map))):
        print("\n[ERROR] MODEL_INFERENCE_ERROR: Non-finite values (NaN or Inf) detected in model output.", file=sys.stderr)
        sys.exit(1)

    # Bounded probabilities check
    if np.any(change_prob_map < 0.0) or np.any(change_prob_map > 1.0):
        print("\n[ERROR] MODEL_INFERENCE_ERROR: Softmax probabilities out of bounds [0, 1].", file=sys.stderr)
        sys.exit(1)

    total_pixels = int(binary_mask.size)
    changed_pixels = int(np.sum(binary_mask > 0))
    changed_pct = (changed_pixels / total_pixels) * 100.0

    min_prob = float(np.min(change_prob_map))
    max_prob = float(np.max(change_prob_map))
    mean_prob = float(np.mean(change_prob_map))

    # 5. Generate Visualizations using Matplotlib
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 4-Panel Visualization
    fig, axes = plt.subplots(2, 2, figsize=(12, 12))
    plt.subplots_adjust(wspace=0.15, hspace=0.2)

    # Panel 1: Image A
    axes[0, 0].imshow(image_a)
    axes[0, 0].set_title(f"Earlier Image A\n({width_a}x{height_a})", fontsize=12, fontweight="bold", pad=8)
    axes[0, 0].axis("off")

    # Panel 2: Image B
    axes[0, 1].imshow(image_b)
    axes[0, 1].set_title(f"Later Image B\n({width_b}x{height_b})", fontsize=12, fontweight="bold", pad=8)
    axes[0, 1].axis("off")

    # Panel 3: Change Mask
    axes[1, 0].imshow(binary_mask, cmap="gray", vmin=0, vmax=1)
    axes[1, 0].set_title(
        f"Predicted Change Mask (Threshold {args.threshold:.2f})\n"
        f"Changed: {changed_pixels:,} px ({changed_pct:.2f}%)",
        fontsize=12,
        fontweight="bold",
        pad=8
    )
    axes[1, 0].axis("off")

    # Panel 4: Change Overlay on Image B
    img_b_np = np.array(image_b, dtype=np.float32) / 255.0
    overlay = img_b_np.copy()
    # Apply red mask overlay (R=1.0, G=0.1, B=0.1) with 0.45 alpha
    change_idx = binary_mask > 0
    if np.any(change_idx):
        overlay[change_idx] = (0.55 * overlay[change_idx]) + (0.45 * np.array([1.0, 0.15, 0.15]))

    axes[1, 1].imshow(np.clip(overlay, 0.0, 1.0))
    axes[1, 1].set_title(
        f"Change Overlay on Later Image B\n"
        f"Confidence: {result.confidence:.3f}" if result.confidence else "Change Overlay on Later Image B",
        fontsize=12,
        fontweight="bold",
        pad=8
    )
    axes[1, 1].axis("off")

    plt.suptitle(
        f"SatQuery AI — ChangeFormer Visual Smoke Test (Model: ChangeFormerV6)\n"
        f"Real LEVIR-CD Bi-temporal Scene • Checkpoint: {ckpt_path.name}",
        fontsize=14,
        fontweight="heavy",
        y=0.98
    )

    vis_path = output_dir / "changeformer_smoke_test.png"
    plt.savefig(vis_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 6. Optional Probability Heatmap
    prob_fig, prob_ax = plt.subplots(1, 1, figsize=(8, 8))
    im = prob_ax.imshow(change_prob_map, cmap="inferno", vmin=0.0, vmax=1.0)
    prob_ax.set_title(
        f"ChangeFormer Change Probability Heatmap\n"
        f"Min: {min_prob:.4f} • Mean: {mean_prob:.4f} • Max: {max_prob:.4f}",
        fontsize=12,
        fontweight="bold",
        pad=10
    )
    prob_ax.axis("off")
    cbar = prob_fig.colorbar(im, ax=prob_ax, fraction=0.046, pad=0.04)
    cbar.set_label("Change Probability (Softmax)", fontsize=10)

    prob_path = output_dir / "changeformer_probability_map.png"
    prob_fig.savefig(prob_path, dpi=180, bbox_inches="tight")
    plt.close(prob_fig)

    # 7. Save JSON Metadata Artifact
    json_path = output_dir / "changeformer_smoke_test.json"
    smoke_summary = {
        "checkpoint_path": str(ckpt_path),
        "model_name": adapter.name,
        "model_class": "ChangeFormerV6",
        "device": str(adapter.device),
        "image_a_path": str(img_a_path),
        "image_b_path": str(img_b_path),
        "input_dimensions": {"width": width_a, "height": height_a, "channels": 3},
        "output_shape": list(logits.shape),
        "minimum_output_value": min_prob,
        "maximum_output_value": max_prob,
        "mean_output_value": mean_prob,
        "finite_value_check": True,
        "predicted_changed_pixel_count": changed_pixels,
        "predicted_changed_pixel_percentage": round(changed_pct, 4),
        "threshold": args.threshold,
        "inference_time_seconds": round(inference_time, 4),
        "confidence": result.confidence,
        "test_status": "PASS"
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(smoke_summary, f, indent=2)

    # 8. Print Formatted CLI Output (exact specified format)
    print("============================================================")
    print("CHANGEFORMER VISUAL SMOKE TEST")
    print("============================================================")
    print(f"Checkpoint: {ckpt_path}")
    print(f"Device: {adapter.device}")
    print(f"Image A: {img_a_path}")
    print(f"Image B: {img_b_path}")
    print("")
    print("Checkpoint loaded: PASS")
    print("Inference executed: PASS")
    print(f"Output shape: {list(logits.shape)}")
    print("Finite values: PASS")
    print("Change mask generated: PASS")
    print("")
    print(f"Predicted changed pixels: {changed_pixels:,} / {total_pixels:,}")
    print(f"Predicted changed percentage: {changed_pct:.2f}%")
    print(f"Inference time: {inference_time:.3f} seconds")
    print("")
    print("Visualization:")
    print(f"{vis_path}")
    print("============================================================")


if __name__ == "__main__":
    main()
