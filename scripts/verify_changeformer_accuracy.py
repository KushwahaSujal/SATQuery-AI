#!/usr/bin/env python3
"""
SATQUERY AI — ChangeFormer Final Real Accuracy Sanity Check
Compares production ChangeFormer inference on the authentic LEVIR-CD image pair
against the official benchmark ground-truth label.
"""

import sys
import os
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Production import - strictly using production adapter
from backend.app.ml.adapters.changeformer import ChangeFormerAdapter


def main():
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    img_a_path = Path("datasets/samples/real_pair/real_image_a.png")
    img_b_path = Path("datasets/samples/real_pair/real_image_b.png")
    gt_path = Path("datasets/samples/real_pair/ground_truth_label.png")

    # 1. Verify Ground Truth Label
    if not gt_path.is_file():
        print("[ERROR] GROUND_TRUTH_NOT_FOUND: Authentic benchmark ground truth label not found.", file=sys.stderr)
        sys.exit(1)

    image_a = Image.open(img_a_path).convert("RGB")
    image_b = Image.open(img_b_path).convert("RGB")
    gt_img = Image.open(gt_path)

    width_a, height_a = image_a.size
    width_b, height_b = image_b.size
    gt_w, gt_h = gt_img.size

    assert (width_a, height_a) == (gt_w, gt_h), f"Dimension mismatch: Input ({width_a}x{height_a}) vs GT ({gt_w}x{gt_h})"

    # Ground truth binary array (255 -> 1, 0 -> 0)
    gt_arr = (np.array(gt_img) > 128).astype(np.uint8)

    # 2. Run EXACT Production Inference
    adapter = ChangeFormerAdapter()
    adapter.load_model()

    result = adapter.predict(image_a, image_b, threshold=0.5)
    pred_mask = result.masks[0]["binary_mask"]
    change_prob_map = result.masks[0]["change_prob_map"]

    # 3. Calculate Confusion Matrix & Accuracy Metrics
    total_pixels = int(gt_arr.size)
    tp = int(np.sum((pred_mask == 1) & (gt_arr == 1)))
    fp = int(np.sum((pred_mask == 1) & (gt_arr == 0)))
    fn = int(np.sum((pred_mask == 0) & (gt_arr == 1)))
    tn = int(np.sum((pred_mask == 0) & (gt_arr == 0)))

    gt_changed_pixels = int(np.sum(gt_arr == 1))
    pred_changed_pixels = int(np.sum(pred_mask == 1))

    gt_changed_pct = (gt_changed_pixels / total_pixels) * 100.0
    pred_changed_pct = (pred_changed_pixels / total_pixels) * 100.0

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    iou = float(tp / (tp + fp + fn)) if (tp + fp + fn) > 0 else 0.0

    # 4. Generate 5-Panel Visualization
    fig, axes = plt.subplots(1, 5, figsize=(25, 5.5))
    plt.subplots_adjust(wspace=0.2)

    # Panel 1: Image A
    axes[0].imshow(image_a)
    axes[0].set_title(f"1. Image A (Earlier)\n({width_a}x{height_a})", fontsize=11, fontweight="bold")
    axes[0].axis("off")

    # Panel 2: Image B
    axes[1].imshow(image_b)
    axes[1].set_title(f"2. Image B (Later)\n({width_b}x{height_b})", fontsize=11, fontweight="bold")
    axes[1].axis("off")

    # Panel 3: Ground Truth Label
    axes[2].imshow(gt_arr, cmap="gray", vmin=0, vmax=1)
    axes[2].set_title(f"3. Benchmark Ground Truth\nChanged: {gt_changed_pixels:,} px ({gt_changed_pct:.2f}%)", fontsize=11, fontweight="bold")
    axes[2].axis("off")

    # Panel 4: Predicted Mask
    axes[3].imshow(pred_mask, cmap="gray", vmin=0, vmax=1)
    axes[3].set_title(f"4. ChangeFormer Prediction\nChanged: {pred_changed_pixels:,} px ({pred_changed_pct:.2f}%)", fontsize=11, fontweight="bold")
    axes[3].axis("off")

    # Panel 5: Confusion Overlay
    # Colors:
    # TP = Green [0.0, 0.85, 0.2]
    # FP = Red [0.95, 0.15, 0.15]
    # FN = Blue/Cyan [0.15, 0.55, 0.95]
    # TN = Dark Gray [0.12, 0.12, 0.14]
    overlay_rgb = np.zeros((height_a, width_a, 3), dtype=np.float32)
    overlay_rgb[(pred_mask == 0) & (gt_arr == 0)] = [0.12, 0.12, 0.14] # TN
    overlay_rgb[(pred_mask == 1) & (gt_arr == 1)] = [0.0, 0.85, 0.2]   # TP (Green)
    overlay_rgb[(pred_mask == 1) & (gt_arr == 0)] = [0.95, 0.15, 0.15] # FP (Red)
    overlay_rgb[(pred_mask == 0) & (gt_arr == 1)] = [0.15, 0.55, 0.95] # FN (Blue)

    axes[4].imshow(overlay_rgb)
    axes[4].set_title(f"5. Prediction vs Ground Truth\nF1: {f1:.4f} • IoU: {iou:.4f}", fontsize=11, fontweight="bold")
    axes[4].axis("off")

    # Add Legend to Panel 5
    legend_patches = [
        mpatches.Patch(color=[0.0, 0.85, 0.2], label=f"TP: True Positive ({tp:,})"),
        mpatches.Patch(color=[0.95, 0.15, 0.15], label=f"FP: False Positive ({fp:,})"),
        mpatches.Patch(color=[0.15, 0.55, 0.95], label=f"FN: False Negative ({fn:,})"),
        mpatches.Patch(color=[0.12, 0.12, 0.14], label=f"TN: True Negative ({tn:,})"),
    ]
    axes[4].legend(handles=legend_patches, loc="lower center", bbox_to_anchor=(0.5, -0.32), fontsize=8.5, framealpha=0.9)

    plt.suptitle(
        f"ChangeFormer Real Accuracy Sanity Check (Authentic LEVIR-CD Benchmark Scene test_2_0000_0000)\n"
        f"Precision: {precision:.4f} • Recall: {recall:.4f} • F1-Score: {f1:.4f} • IoU: {iou:.4f}",
        fontsize=13,
        fontweight="heavy",
        y=1.04
    )

    vis_path = results_dir / "changeformer_accuracy_check.png"
    plt.savefig(vis_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 5. Save JSON Results
    accuracy_results = {
        "dataset": "LEVIR-CD",
        "sample_name": "test_2_0000_0000",
        "image_a": str(img_a_path),
        "image_b": str(img_b_path),
        "ground_truth_label": str(gt_path),
        "checkpoint": str(adapter._resolve_checkpoint_path()),
        "model_class": "ChangeFormerV6",
        "dimensions": {"width": width_a, "height": height_a},
        "confusion_matrix": {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
            "total_pixels": total_pixels
        },
        "metrics": {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "iou": round(iou, 6)
        },
        "change_distribution": {
            "ground_truth_changed_pixels": gt_changed_pixels,
            "ground_truth_changed_percentage": round(gt_changed_pct, 4),
            "predicted_changed_pixels": pred_changed_pixels,
            "predicted_changed_percentage": round(pred_changed_pct, 4)
        },
        "preprocessing_audit": {
            "production_normalization": "ImageNet (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])",
            "production_input_size": [512, 512],
            "benchmark_native_size": [256, 256],
            "benchmark_native_normalization": "[-1, 1] (mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])"
        }
    }

    json_path = results_dir / "changeformer_accuracy_check.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(accuracy_results, f, indent=2)

    # Print Summary Report
    print("============================================================")
    print("CHANGEFORMER REAL ACCURACY SANITY CHECK")
    print("============================================================")
    print(f"Benchmark Scene: LEVIR-CD test_2_0000_0000")
    print(f"Image Dimensions: {width_a}x{height_a}")
    print(f"Ground Truth Label: {gt_path}")
    print("")
    print("Confusion Matrix:")
    print(f"  TP (True Positive):  {tp:,} px")
    print(f"  FP (False Positive): {fp:,} px")
    print(f"  FN (False Negative): {fn:,} px")
    print(f"  TN (True Negative):  {tn:,} px")
    print(f"  Total Pixels:        {total_pixels:,} px")
    print("")
    print("Accuracy Metrics:")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  IoU:       {iou:.4f}")
    print("")
    print(f"Ground-Truth Changed %: {gt_changed_pct:.2f}% ({gt_changed_pixels:,} px)")
    print(f"Predicted Changed %:    {pred_changed_pct:.2f}% ({pred_changed_pixels:,} px)")
    print("")
    print("Artifacts Saved:")
    print(f"  Visualization: {vis_path}")
    print(f"  JSON Results:  {json_path}")
    print("============================================================")

    # Final Conclusion determination
    if precision < 0.50 or f1 < 0.50:
        print("\nCONCLUSION: OPERATIONAL_ONLY")
    else:
        print("\nCONCLUSION: ACCURACY_SANITY_CHECK_PASS")


if __name__ == "__main__":
    main()
