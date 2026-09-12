#!/usr/bin/env python3
"""
SATQUERY AI — VRSBench Grounding Benchmark Evaluation Script

Executes the production grounding workflow (Grounding DINO + V4 Reasoning + SAM 2)
against Visual Reasoning for Remote Sensing (VRSBench) evaluation records.

Strict Rules:
- Calls the actual production grounding workflow (run_grounding_pipeline).
- Ground truth is NEVER passed into runtime inference.
- IoU is calculated strictly post-prediction.
- Outputs Mean IoU, Median IoU, Recall@0.25, and Recall@0.50.
- Saves evaluation results separately from production runtime results.
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
from backend.app.ml.adapters.sam2 import SAM2Adapter
from backend.app.workflows.grounding import run_grounding_pipeline


def compute_box_iou(box1: List[float], box2: List[float]) -> float:
    """
    Computes Intersection over Union (IoU) between two 2D boxes [x1, y1, x2, y2].
    Strictly evaluated post-prediction without modifying model outputs.
    """
    if not box1 or not box2 or len(box1) != 4 or len(box2) != 4:
        return 0.0

    b1_x1, b1_y1, b1_x2, b1_y2 = float(box1[0]), float(box1[1]), float(box1[2]), float(box1[3])
    b2_x1, b2_y1, b2_x2, b2_y2 = float(box2[0]), float(box2[1]), float(box2[2]), float(box2[3])

    # Ensure coordinates are ordered [minx, miny, maxx, maxy]
    b1_minx, b1_maxx = min(b1_x1, b1_x2), max(b1_x1, b1_x2)
    b1_miny, b1_maxy = min(b1_y1, b1_y2), max(b1_y1, b1_y2)
    b2_minx, b2_maxx = min(b2_x1, b2_x2), max(b2_x1, b2_x2)
    b2_miny, b2_maxy = min(b2_y1, b2_y2), max(b2_y1, b2_y2)

    inter_x1 = max(b1_minx, b2_minx)
    inter_y1 = max(b1_miny, b2_miny)
    inter_x2 = min(b1_maxx, b2_maxx)
    inter_y2 = min(b1_maxy, b2_maxy)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    intersection = inter_w * inter_h

    area1 = (b1_maxx - b1_minx) * (b1_maxy - b1_miny)
    area2 = (b2_maxx - b2_minx) * (b2_maxy - b2_miny)
    union = area1 + area2 - intersection

    if union <= 0.0:
        return 0.0

    return float(intersection / union)


def normalize_gt_box(raw_box: Any, box_format: str = "xyxy", img_w: int = 256, img_h: int = 256) -> Optional[List[float]]:
    """
    Normalizes ground-truth box representations into absolute pixel coordinates [x1, y1, x2, y2].
    """
    if not raw_box or not isinstance(raw_box, (list, tuple)) or len(raw_box) != 4:
        return None

    vals = [float(v) for v in raw_box]

    # Handle relative [0, 1] coords
    if max(vals) <= 1.0 and any(v > 0 for v in vals):
        if box_format.lower() in ("ymin_xmin_ymax_xmax", "yxyx"):
            ymin, xmin, ymax, xmax = vals
            return [xmin * img_w, ymin * img_h, xmax * img_w, ymax * img_h]
        elif box_format.lower() in ("xywh",):
            x, y, w, h = vals
            return [x * img_w, y * img_h, (x + w) * img_w, (y + h) * img_h]
        else:  # xyxy
            x1, y1, x2, y2 = vals
            return [x1 * img_w, y1 * img_h, x2 * img_w, y2 * img_h]

    # Absolute pixel coords
    if box_format.lower() in ("xywh",):
        x, y, w, h = vals
        return [x, y, x + w, y + h]
    elif box_format.lower() in ("ymin_xmin_ymax_xmax", "yxyx"):
        ymin, xmin, ymax, xmax = vals
        return [xmin, ymin, xmax, ymax]
    else:  # xyxy
        return vals


def resolve_image_path(image_id: str, search_dirs: List[Path]) -> Optional[Path]:
    """
    Resolves image_id to an authentic local image file.
    Supports filenames with/without extensions and direct paths.
    """
    # 1. Direct path check
    direct_p = Path(image_id)
    if direct_p.is_file():
        return direct_p

    # 2. Candidate suffixes
    valid_exts = ["", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".PNG", ".JPG"]

    for d in search_dirs:
        if not d.is_dir():
            continue

        for ext in valid_exts:
            candidate = d / f"{image_id}{ext}"
            if candidate.is_file():
                return candidate

        # Recursive search within directory
        matches = list(d.rglob(f"{image_id}.*")) + list(d.rglob(image_id))
        for m in matches:
            if m.is_file() and m.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
                return m

    return None


def load_evaluation_records(records_path: Path) -> List[Dict[str, Any]]:
    """
    Loads VRSBench evaluation records from JSON, JSONL, or YAML.
    """
    if not records_path.is_file():
        raise FileNotFoundError(f"Evaluation records file not found at: '{records_path}'")

    suffix = records_path.suffix.lower()

    if suffix == ".jsonl":
        records = []
        with open(records_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    elif suffix in (".yaml", ".yml"):
        import yaml
        with open(records_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Check manifest structure
            ann_p = data.get("annotations", {}).get("path")
            if ann_p:
                ann_path = Path(ann_p)
                if not ann_path.is_absolute():
                    ann_path = records_path.parent / ann_path
                return load_evaluation_records(ann_path)
            return data.get("records", data.get("annotations", []))

    else:  # Default .json
        with open(records_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Standard COCO or VRSBench dict formats
            for key in ["annotations", "records", "data", "samples", "items"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # Single dict wrapper
            return [data]

    return []


def evaluate_grounding_vrsbench(
    records: List[Dict[str, Any]],
    search_dirs: List[Path],
    output_dir: Path,
    box_threshold: float = 0.20,
    max_samples: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes actual production grounding pipeline over VRSBench records and computes metrics.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir

    print("================================================================================")
    print("SATQUERY AI -- VRSBENCH REAL GROUNDING BENCHMARK EVALUATION")
    print("================================================================================")
    print(f"Total input records:      {len(records)}")
    if max_samples:
        print(f"Evaluation limit:         {max_samples} samples")
        records = records[:max_samples]

    # Pre-instantiate shared model adapters to avoid repeated weight reloading
    print("\n[1/3] Initializing production model adapters (Lazy Loading)...")
    shared_gd = GroundingDINOAdapter()
    shared_sam2 = SAM2Adapter()

    eval_samples = []
    ious = []
    r25_hits = 0
    r50_hits = 0
    start_time = time.perf_counter()

    print("\n[2/3] Executing production inference (Grounding DINO + V4 + SAM 2)...")
    print("-" * 80)
    print(f"{'Idx':<4} | {'Image ID':<16} | {'IoU':<7} | {'GD Score':<9} | {'SAM2 Score':<10} | {'Strategy':<14}")
    print("-" * 80)

    for idx, rec in enumerate(records, start=1):
        rec_id = str(rec.get("id", f"sample_{idx:04d}"))
        image_id = str(rec.get("image_id", rec.get("filename", rec.get("image", ""))))
        query = str(rec.get("query", rec.get("caption", rec.get("expression", rec.get("prompt", "")))))
        raw_gt_box = rec.get("bbox", rec.get("box", rec.get("ground_truth_box", rec.get("gt_box"))))
        box_fmt = rec.get("bbox_format", "xyxy")

        # 1. Resolve image_id
        resolved_img = resolve_image_path(image_id, search_dirs)
        if resolved_img is None:
            print(f"{idx:<4} | {image_id[:16]:<16} | {'SKIPPED':<7} | Image not found in search paths.")
            eval_samples.append({
                "id": rec_id,
                "image_id": image_id,
                "query": query,
                "status": "SKIPPED_IMAGE_NOT_FOUND",
                "iou": 0.0
            })
            continue

        # 2. Run actual production Grounding DINO + V4 + SAM2
        # CRITICAL INTEGRITY CHECK: Ground truth is NEVER passed into runtime inference.
        sample_t0 = time.perf_counter()
        try:
            pipeline_res = run_grounding_pipeline(
                image=resolved_img,
                query=query,
                box_threshold=box_threshold,
                grounding_adapter=shared_gd,
                sam2_adapter=shared_sam2
            )
            pred_box = pipeline_res.get("selected_box")
            gd_score = pipeline_res.get("grounding_score")
            sam2_score = pipeline_res.get("sam2_score")
            strategy = pipeline_res.get("strategy", "UNKNOWN")
            answer = pipeline_res.get("answer")
            ev_data = pipeline_res.get("evidence", {})
        except Exception as e:
            print(f"{idx:<4} | {image_id[:16]:<16} | {'ERROR':<7} | Inference error: {e}")
            eval_samples.append({
                "id": rec_id,
                "image_id": image_id,
                "query": query,
                "status": f"ERROR: {str(e)}",
                "iou": 0.0
            })
            ious.append(0.0)
            continue

        sample_duration = time.perf_counter() - sample_t0

        # 3. Calculate IoU ONLY AFTER prediction has completed
        # Resolve dimensions for relative boxes
        img_w = ev_data.get("width", 256)
        img_h = ev_data.get("height", 256)
        gt_box = normalize_gt_box(raw_gt_box, box_format=box_fmt, img_w=img_w, img_h=img_h)

        if pred_box and gt_box:
            iou = compute_box_iou(pred_box, gt_box)
        else:
            iou = 0.0

        ious.append(iou)
        if iou >= 0.25:
            r25_hits += 1
        if iou >= 0.50:
            r50_hits += 1

        gd_str = f"{gd_score:.4f}" if gd_score is not None else "None"
        s2_str = f"{sam2_score:.4f}" if sam2_score is not None else "None"
        print(f"{idx:<4} | {image_id[:16]:<16} | {iou:.4f}  | {gd_str:<9} | {s2_str:<10} | {strategy:<14}")

        eval_samples.append({
            "id": rec_id,
            "image_id": image_id,
            "image_path": str(resolved_img),
            "query": query,
            "ground_truth_box": gt_box,
            "predicted_box": pred_box,
            "iou": round(float(iou), 4),
            "iou_ge_025": bool(iou >= 0.25),
            "iou_ge_050": bool(iou >= 0.50),
            "grounding_score": round(float(gd_score), 4) if gd_score is not None else None,
            "sam2_score": round(float(sam2_score), 4) if sam2_score is not None else None,
            "strategy": strategy,
            "answer": answer,
            "mask_pixel_count": ev_data.get("mask_pixel_count"),
            "duration_s": round(float(sample_duration), 2),
            "status": "SUCCESS" if pred_box else "NO_BOX_SELECTED"
        })

    total_eval_time = time.perf_counter() - start_time
    total_valid = len(ious)

    # 4. Calculate Aggregate Benchmark Metrics
    mean_iou = float(np.mean(ious)) if total_valid > 0 else 0.0
    median_iou = float(np.median(ious)) if total_valid > 0 else 0.0
    recall_25 = float(r25_hits / total_valid) if total_valid > 0 else 0.0
    recall_50 = float(r50_hits / total_valid) if total_valid > 0 else 0.0

    print("-" * 80)
    print("\n[3/3] VRSBench Grounding Evaluation Summary:")
    print("=" * 50)
    print(f"Total Evaluated Samples:  {total_valid}")
    print(f"Mean IoU:                 {mean_iou:.4f} ({mean_iou * 100:.2f}%)")
    print(f"Median IoU:               {median_iou:.4f} ({median_iou * 100:.2f}%)")
    print(f"Recall@0.25 (IoU >= 0.25): {recall_25:.4f} ({recall_25 * 100:.2f}%) [{r25_hits}/{total_valid}]")
    print(f"Recall@0.50 (IoU >= 0.50): {recall_50:.4f} ({recall_50 * 100:.2f}%) [{r50_hits}/{total_valid}]")
    print(f"Total Evaluation Time:    {total_eval_time:.2f}s")
    print("=" * 50)

    # 5. Save evaluation results separately from production runtime results
    report = {
        "benchmark": "VRSBench",
        "task": "visual_grounding",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metrics": {
            "mean_iou": round(mean_iou, 4),
            "median_iou": round(median_iou, 4),
            "recall_at_025": round(recall_25, 4),
            "recall_at_050": round(recall_50, 4),
            "total_evaluated": total_valid,
            "hits_at_025": r25_hits,
            "hits_at_050": r50_hits,
            "evaluation_time_seconds": round(total_eval_time, 2)
        },
        "evaluation_config": {
            "box_threshold": box_threshold,
            "pipeline": "GroundingDINO + V4 Reasoning + SAM2",
            "models": ["IDEA-Research/grounding-dino-base", "facebook/sam2.1-hiera-small"]
        },
        "samples": eval_samples
    }

    # Save detailed evaluation file
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    eval_filepath = results_dir / f"vrsbench_grounding_eval_{timestamp_str}.json"
    summary_filepath = results_dir / "vrsbench_grounding_summary.json"

    with open(eval_filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    with open(summary_filepath, "w", encoding="utf-8") as f:
        json.dump({
            "benchmark": "VRSBench",
            "metrics": report["metrics"],
            "latest_run": str(eval_filepath.name)
        }, f, indent=2)

    print(f"\nEvaluation results saved separately at:")
    print(f" - Detailed Log: {eval_filepath}")
    print(f" - Summary:      {summary_filepath}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="SATQUERY AI -- VRSBench Grounding Benchmark Evaluation"
    )
    parser.add_argument(
        "--records",
        type=str,
        default="datasets/samples/vrsbench_sample_records.json",
        help="Path to VRSBench evaluation records file (JSON, JSONL, or YAML manifest)"
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default="datasets/samples",
        help="Root directory containing benchmark satellite imagery"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/evaluations",
        help="Directory to save evaluation reports separately from runtime results"
    )
    parser.add_argument(
        "--box-threshold",
        type=float,
        default=0.20,
        help="Grounding DINO candidate box threshold"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Optional limit on number of samples to evaluate"
    )
    args = parser.parse_args()

    records_p = Path(args.records)
    if not records_p.is_file():
        # Check relative to PROJECT_ROOT
        alt_p = PROJECT_ROOT / args.records
        if alt_p.is_file():
            records_p = alt_p
        else:
            print(f"[ERROR] Evaluation records file not found at '{records_p}'.", file=sys.stderr)
            sys.exit(1)

    images_dir = Path(args.images_dir)
    if not images_dir.is_dir():
        images_dir = PROJECT_ROOT / args.images_dir

    search_dirs = [
        images_dir,
        images_dir / "real_pair",
        PROJECT_ROOT / "datasets/samples/real_pair",
        PROJECT_ROOT / "datasets/samples"
    ]

    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = PROJECT_ROOT / args.output_dir

    records = load_evaluation_records(records_p)
    evaluate_grounding_vrsbench(
        records=records,
        search_dirs=search_dirs,
        output_dir=out_dir,
        box_threshold=args.box_threshold,
        max_samples=args.max_samples
    )


if __name__ == "__main__":
    main()
