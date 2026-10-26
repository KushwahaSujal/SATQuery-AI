#!/usr/bin/env python3
"""Score the ISPRS Potsdam / Vaihingen models against the *eroded* ("noBoundary") labels.

The training reports (project/qna.md Q-036) score our held-out test tiles against the full labels.
The ISPRS benchmark protocol instead ignores a 3 px band around every class boundary (black in the
eroded label sets) and quotes overall accuracy plus per-class F1, with the headline mean F1 over
the five classes excluding clutter. This scores the same test tiles under that protocol.

It is still NOT a leaderboard number: our test tiles come from isprs_split, not the official
withheld test set (Q-036 §"Not comparable").

    .venv/bin/python scripts/eval_isprs_eroded.py --out results/eval/isprs_eroded.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.segmentation.datasets import (  # noqa: E402
    IGNORE, ISPRS_CLASSES, ISPRS_RAW, ISPRS_SOURCES, IsprsTiles,
)
from training.segmentation.train_landcover import infer_logits  # noqa: E402
from training.segmentation.train_seg import build_model  # noqa: E402

ERODED = {
    "isprs_potsdam": lambda label: ISPRS_RAW / "Potsdam/Potsdam/5_Labels_all_noBoundary"
                                   / label.name.replace("_label.tif", "_label_noBoundary.tif"),
    "isprs_vaihingen": lambda label: ISPRS_RAW / "Vaihingen/Vaihingen"
                                     / "ISPRS_semantic_labeling_Vaihingen_ground_truth_eroded_COMPLETE"
                                     / label.name.replace(".tif", "_noBoundary.tif"),
}


@torch.no_grad()
def score(source: str, ckpt_path: Path, device: torch.device) -> dict:
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = build_model(ckpt["arch"], ckpt["encoder"])
    head = model.segmentation_head[0]  # same K-class head swap as train_landcover.py
    model.segmentation_head[0] = torch.nn.Conv2d(head.in_channels, len(ckpt["classes"]), head.kernel_size,
                                                 padding=head.padding)
    model.load_state_dict(ckpt["model"])
    model.to(device).eval()
    items = [(img, ERODED[source](label), gsd, bands) for img, label, gsd, bands in ISPRS_SOURCES[source]("test")]
    missing = [str(i[1]) for i in items if not i[1].exists()]
    assert not missing, f"eroded labels missing: {missing}"
    K = len(ISPRS_CLASSES)
    conf = torch.zeros((K, K), dtype=torch.int64, device=device)
    for img, mask in DataLoader(IsprsTiles(items, crop=None, train=False, target_gsd=ckpt["target_gsd"]), batch_size=1):
        img, mask = img.to(device), mask.to(device)
        pred = infer_logits(model, img).argmax(1)
        v = mask != IGNORE
        conf += torch.bincount(mask[v] * K + pred[v], minlength=K * K).view(K, K)
    conf = conf.double().cpu().numpy()
    tp, gt, pr = np.diag(conf), conf.sum(1), conf.sum(0)
    f1 = 2 * tp / np.maximum(gt + pr, 1)
    iou = tp / np.maximum(gt + pr - tp, 1)
    five = [ISPRS_CLASSES.index(c) for c in ISPRS_CLASSES if c != "clutter"]
    return {
        "test_tiles": [Path(i[0]).name for i in items],
        "overall_accuracy": round(float(tp.sum() / conf.sum()), 4),
        "mean_f1_5class": round(float(f1[five].mean()), 4),
        "mean_iou_5class": round(float(iou[five].mean()), 4),
        "per_class_f1": {c: round(float(f1[i]), 4) for i, c in enumerate(ISPRS_CLASSES)},
        "per_class_iou": {c: round(float(iou[i]), 4) for i, c in enumerate(ISPRS_CLASSES)},
        "scored_pixels": int(conf.sum()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results/eval/isprs_eroded.json"))
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    report = {city: score(f"isprs_{city}", ROOT / f"checkpoints/isprs_{city}_seg/best.pt", device)
              for city in ("potsdam", "vaihingen")}
    report["protocol"] = ("eroded (noBoundary) labels, 3 px boundary band ignored; held-out isprs_split test "
                          "tiles, not the official ISPRS test set")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
