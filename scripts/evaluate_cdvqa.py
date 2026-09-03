import os
import sys
import time
import json
import argparse
from collections import defaultdict
from typing import Dict, Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Add satquery-ai root to path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from training.vqa.model import CDVQAModel, CDVQA_ANSWER_CLASSES, IDX2ANSWER, WORD2IDX
from training.vqa.dataset import CDVQADataset


def evaluate_official_cdvqa(
    checkpoint_path: str = "checkpoints/cdvqa/cdvqa_satquery.pt",
    annotations_dir: str = "datasets/cdvqa/annotations",
    images_root: str = "datasets/cdvqa/SECOND",
    test_split: str = "Test",
    batch_size: int = 64,
    max_test_samples: int = None,
    output_predictions_path: str = "results/cdvqa_test_predictions.json",
    output_metrics_path: str = "results/cdvqa_test_metrics.json"
) -> Dict[str, Any]:
    print("=" * 65)
    print(f"SATQUERY AI — CDVQA OFFICIAL TEST EVALUATION ({test_split})")
    print("=" * 65)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Evaluation Device: {device}")

    # 1. Load Checkpoint
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    print(f"Loading checkpoint from: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    # 2. Build Model
    model = CDVQAModel(
        num_classes=len(CDVQA_ANSWER_CLASSES),
        vocab_size=len(WORD2IDX),
        feature_dim=512,
        freeze_backbone=True,
        pretrained=False
    ).to(device)
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()
    print("Model weights loaded and set to eval mode.")

    # 3. Load Test Dataset
    print(f"Loading official {test_split} dataset split from {annotations_dir}...")
    dataset = CDVQADataset(
        annotations_dir=annotations_dir,
        split=test_split,
        images_root=images_root,
        max_samples=max_test_samples
    )
    print(f"Total test instances to evaluate: {len(dataset):,}")

    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # 4. Evaluation Loop
    total_samples = 0
    correct_samples = 0
    type_total = defaultdict(int)
    type_correct = defaultdict(int)
    predictions_record = []

    t0 = time.time()
    with torch.no_grad():
        for batch in dataloader:
            img1 = batch['img1'].to(device)
            img2 = batch['img2'].to(device)
            q_tokens = batch['question_tokens'].to(device)
            labels = batch['label'].to(device)
            q_types = batch['question_type']
            q_texts = batch['question_text']
            a_texts = batch['answer_text']
            file_names = batch['file_name']

            outputs = model(img1, img2, q_tokens)
            logits = outputs['logits']
            probs = torch.softmax(logits, dim=-1)
            confidences, preds = torch.max(probs, dim=-1)

            batch_size = labels.size(0)
            total_samples += batch_size

            preds_list = preds.cpu().tolist()
            labels_list = labels.cpu().tolist()
            confs_list = confidences.cpu().tolist()

            for i in range(batch_size):
                p_idx = preds_list[i]
                l_idx = labels_list[i]
                q_t = q_types[i]
                is_correct = (p_idx == l_idx)

                if is_correct:
                    correct_samples += 1
                    type_correct[q_t] += 1
                type_total[q_t] += 1

                pred_ans = IDX2ANSWER.get(p_idx, str(p_idx))
                true_ans = a_texts[i]

                predictions_record.append({
                    "file_name": file_names[i],
                    "question": q_texts[i],
                    "question_type": q_t,
                    "predicted_answer": pred_ans,
                    "ground_truth_answer": true_ans,
                    "confidence": confs_list[i],
                    "correct": is_correct
                })

    eval_duration = time.time() - t0
    overall_accuracy = correct_samples / total_samples if total_samples > 0 else 0.0

    type_accuracies = {}
    for t in sorted(type_total.keys()):
        acc = type_correct[t] / type_total[t] if type_total[t] > 0 else 0.0
        type_accuracies[t] = acc

    average_accuracy = sum(type_accuracies.values()) / len(type_accuracies) if type_accuracies else 0.0

    # 5. Print Official Metrics Report
    print("\n" + "=" * 65)
    print("OFFICIAL CDVQA EVALUATION METRICS REPORT")
    print("=" * 65)
    print(f"Total Evaluated Samples: {total_samples:,}")
    print(f"Overall Accuracy (OA):   {overall_accuracy * 100:.2f}%")
    print(f"Average Accuracy (AA):   {average_accuracy * 100:.2f}%")
    print("-" * 65)
    print("Per Question-Type Accuracy:")
    for t, acc in type_accuracies.items():
        cnt = type_total[t]
        print(f"  - {t:<24}: {acc * 100:6.2f}% ({type_correct[t]}/{cnt})")
    print("-" * 65)
    print(f"Evaluation Duration: {eval_duration:.1f}s ({eval_duration/total_samples*1000:.2f} ms/sample)")
    print("=" * 65)

    # 6. Save JSON records
    os.makedirs(os.path.dirname(output_metrics_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_predictions_path), exist_ok=True)

    metrics_payload = {
        "split": test_split,
        "checkpoint": checkpoint_path,
        "total_evaluated": total_samples,
        "overall_accuracy": overall_accuracy,
        "average_accuracy": average_accuracy,
        "type_accuracies": type_accuracies,
        "type_sample_counts": dict(type_total),
        "evaluation_duration_seconds": eval_duration,
        "timestamp": time.time()
    }
    with open(output_metrics_path, "w") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"Metrics saved to: {output_metrics_path}")

    # Save a subset or full predictions (cap at 10,000 for compact storage)
    with open(output_predictions_path, "w") as f:
        json.dump(predictions_record[:10000], f, indent=2)
    print(f"Predictions saved to: {output_predictions_path} (entries: {min(len(predictions_record), 10000)})")

    return metrics_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Official CDVQA Model on Test Split")
    parser.add_argument("--checkpoint", type=str, default="checkpoints/cdvqa/cdvqa_satquery.pt")
    parser.add_argument("--annotations_dir", type=str, default="datasets/cdvqa/annotations")
    parser.add_argument("--images_root", type=str, default="datasets/cdvqa/SECOND")
    parser.add_argument("--split", type=str, default="Test")
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--max_samples", type=int, default=None)
    parser.add_argument("--output_metrics", type=str, default="results/cdvqa_test_metrics.json")
    parser.add_argument("--output_preds", type=str, default="results/cdvqa_test_predictions.json")
    args = parser.parse_args()

    evaluate_official_cdvqa(
        checkpoint_path=args.checkpoint,
        annotations_dir=args.annotations_dir,
        images_root=args.images_root,
        test_split=args.split,
        batch_size=args.batch_size,
        max_test_samples=args.max_samples,
        output_predictions_path=args.output_preds,
        output_metrics_path=args.output_metrics
    )
