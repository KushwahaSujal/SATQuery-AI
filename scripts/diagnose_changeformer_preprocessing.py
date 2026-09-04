#!/usr/bin/env python3
"""
SatQuery AI — ChangeFormer Preprocessing Discriminator
=======================================================

WHY THIS EXISTS
---------------
Reported symptom: "when changes are highlighted between two images, the difference
does not show properly."

Two SatQuery documents give contradictory preprocessing contracts:

  docs/SATQUERY_AI_MASTER_DOCUMENTATION.md  §26
      "Root cause: production code normalised with ImageNet mean/std, whereas native
       training used [-1, 1] rescaling. Solution: re-aligned preprocess_changeformer_input()."
      -> implies ImageNet is WRONG.

  docs/models/CHANGEFORMER_V6.md            §10
      "Upstream preprocessing: ImageNet mean [0.485,0.456,0.406] std [0.229,0.224,0.225]."
      -> implies ImageNet is RIGHT.

The code (backend/app/models/changeformer.py:464-467) currently uses ImageNet.
There is no ChangeFormer training script in this repository, so the contract that
satquery_changeformer_best.pt was actually trained under is undocumented.

This script does NOT guess. It runs the SAME image pair under every candidate
configuration and scores each against the real LEVIR-CD ground-truth label, so the
correct contract is decided by measurement.

USAGE
-----
    python scripts/diagnose_changeformer_preprocessing.py

Requires checkpoints/changeformer/satquery_changeformer_best.pt to be present.

INTERPRETING THE OUTPUT
-----------------------
The winning row is the true preprocessing contract. If ImageNet@512 (the current
production setting) is NOT the winner, that is the root cause of the reported bug
and backend/app/models/changeformer.py must be aligned to the winner.

If every row scores poorly (IoU < 0.2), the problem is not preprocessing — suspect
the checkpoint itself, and re-open the investigation.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.changeformer import ChangeFormerAdapter  # noqa: E402

PAIR_DIR = PROJECT_ROOT / "datasets" / "samples" / "real_pair"
IMG_A = PAIR_DIR / "real_image_a.png"
IMG_B = PAIR_DIR / "real_image_b.png"
GT = PAIR_DIR / "ground_truth_label.png"

# Candidate normalisation contracts.
NORMALISATIONS: Dict[str, Tuple[List[float], List[float]]] = {
    # What the code does today.
    "imagenet": ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    # What the master doc says training used; also what wgcban/ChangeFormer's
    # reference dataloader applies -> maps [0,1] to [-1,1].
    "neg1to1": ([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    # Control: no normalisation at all, plain [0,1].
    "zero_one": ([0.0, 0.0, 0.0], [1.0, 1.0, 1.0]),
}

# The pair is natively 256x256; production forces 512x512. Test both.
INPUT_SIZES = [(256, 256), (512, 512)]


def to_tensor(path: Path, mean: List[float], std: List[float], size: Tuple[int, int]) -> torch.Tensor:
    """Preprocess one image under an explicit contract (no heuristics)."""
    arr = np.array(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    arr = (arr - np.array(mean, dtype=np.float32)) / np.array(std, dtype=np.float32)
    t = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).float()
    if t.shape[2:] != size:
        t = F.interpolate(t, size=size, mode="bilinear", align_corners=False)
    return t


def score(pred: np.ndarray, gt: np.ndarray) -> Dict[str, float]:
    """Binary segmentation metrics for the change class."""
    p = pred.astype(bool)
    g = gt.astype(bool)
    tp = int(np.logical_and(p, g).sum())
    fp = int(np.logical_and(p, ~g).sum())
    fn = int(np.logical_and(~p, g).sum())
    tn = int(np.logical_and(~p, ~g).sum())
    union = tp + fp + fn
    return {
        "iou": tp / union if union else 0.0,
        "f1": (2 * tp) / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0,
        "precision": tp / (tp + fp) if (tp + fp) else 0.0,
        "recall": tp / (tp + fn) if (tp + fn) else 0.0,
        "accuracy": (tp + tn) / (tp + tn + fp + fn),
        "pred_pct": 100.0 * p.sum() / p.size,
    }


def main() -> int:
    for f in (IMG_A, IMG_B, GT):
        if not f.is_file():
            print(f"[ERROR] missing fixture: {f}", file=sys.stderr)
            return 1

    adapter = ChangeFormerAdapter()
    if not adapter.is_available():
        print(
            "[BLOCKED] ChangeFormer checkpoint not found.\n"
            "          Expected: checkpoints/changeformer/satquery_changeformer_best.pt\n"
            "          This diagnostic cannot run without it — ask Ayushman for the file.",
            file=sys.stderr,
        )
        return 2

    adapter.load_model()
    model = adapter._model
    device = adapter.device

    gt_arr = np.array(Image.open(GT))
    if gt_arr.ndim == 3:
        gt_arr = gt_arr[..., 0]
    gt_bin = (gt_arr > 128).astype(np.uint8)
    h, w = gt_bin.shape
    print(f"Ground truth: {gt_bin.sum():,} changed px = {100 * gt_bin.mean():.2f}% of scene\n")

    rows = []
    for norm_name, (mean, std) in NORMALISATIONS.items():
        for size in INPUT_SIZES:
            ta = to_tensor(IMG_A, mean, std, size).to(device)
            tb = to_tensor(IMG_B, mean, std, size).to(device)
            with torch.no_grad():
                logits = model(ta, tb)
                if logits.shape[2:] != (h, w):
                    logits = F.interpolate(logits, size=(h, w), mode="bilinear", align_corners=False)
                prob = torch.softmax(logits, dim=1)[0, 1].cpu().numpy()

            # Sweep threshold too — a wrong contract often also shifts the optimum.
            best = None
            for thr in (0.3, 0.4, 0.5, 0.6, 0.7):
                m = score((prob >= thr).astype(np.uint8), gt_bin)
                m["threshold"] = thr
                if best is None or m["iou"] > best["iou"]:
                    best = m
            best["config"] = f"{norm_name}@{size[0]}"
            rows.append(best)

    rows.sort(key=lambda r: r["iou"], reverse=True)

    print(f"{'config':<20} {'thr':>4} {'IoU':>7} {'F1':>7} {'prec':>7} {'rec':>7} {'pred%':>7}")
    print("-" * 64)
    for r in rows:
        print(
            f"{r['config']:<20} {r['threshold']:>4.1f} {r['iou']:>7.4f} {r['f1']:>7.4f} "
            f"{r['precision']:>7.4f} {r['recall']:>7.4f} {r['pred_pct']:>7.2f}"
        )

    win = rows[0]
    current = next(r for r in rows if r["config"] == "imagenet@512")
    print("\n" + "=" * 64)
    print(f"WINNER            : {win['config']} @ thr={win['threshold']} -> IoU {win['iou']:.4f}")
    print(f"PRODUCTION TODAY  : imagenet@512 @ thr={current['threshold']} -> IoU {current['iou']:.4f}")

    if win["iou"] < 0.20:
        print(
            "\nVERDICT: every configuration scores poorly. Preprocessing is NOT the root cause.\n"
            "         Suspect the checkpoint itself (wrong weights, or trained on a different task).\n"
            "         Re-open the investigation — do not 'fix' preprocessing."
        )
    elif win["config"] == "imagenet@512":
        print(
            "\nVERDICT: current production preprocessing is already optimal.\n"
            "         The reported bug lies elsewhere — check the overlay renderer,\n"
            "         min_component_area filtering, or the input bit-depth path."
        )
    else:
        gain = win["iou"] - current["iou"]
        print(
            f"\nVERDICT: ROOT CAUSE CONFIRMED — preprocessing mismatch.\n"
            f"         Switching to '{win['config']}' raises IoU by {gain:+.4f}.\n"
            f"         Align backend/app/models/changeformer.py:464-467 to the winning contract."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
