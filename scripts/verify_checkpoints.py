#!/usr/bin/env python3
"""
SatQuery AI — Checkpoint verification.

Unlike scripts/setup_checkpoints.py (which writes 1.5 KB placeholder dicts that
make is_available() report True while load_model() fails), this script never
creates anything. It reports what is actually on disk and whether each file is a
real set of weights or a placeholder.

    python scripts/verify_checkpoints.py

Exit code 0 if every enabled model has genuine weights, 1 otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Approximate sizes from docs/SATQUERY_AI_MODEL_DATA_SETUP.md, used only to flag
# something obviously wrong (e.g. a placeholder). Not an equality check.
EXPECTED_MB = {
    "changeformer": 164,
    "cdvqa": 46,
    "satquery_optical_sar_fusion": 18,
    "dofa": 552,
    "remoteclip": 605,
    "bigearthnet": 94,
    "general_rs_vlm": 1540,
    "grounding_dino": 694,
    "sam2": 184,
}

# These load from HuggingFace by model_id and need no local file.
HUGGINGFACE_BACKED = {"grounding_dino", "sam2"}


def describe(path: Path) -> tuple[str, float]:
    """Returns (verdict, size_mb) for a checkpoint file or directory."""
    if path.is_dir():
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return ("directory", size / 1e6)
    size_mb = path.stat().st_size / 1e6
    if size_mb < 0.05:
        return ("PLACEHOLDER", size_mb)
    return ("file", size_mb)


def is_placeholder(path: Path) -> bool:
    """A setup_checkpoints.py placeholder is a tiny dict with no tensors."""
    if path.is_dir() or path.stat().st_size > 100_000:
        return False
    try:
        import torch

        obj = torch.load(str(path), map_location="cpu", weights_only=False)
    except Exception:
        return False
    if isinstance(obj, dict):
        keys = set(obj)
        return keys <= {"model_name", "version", "initialized"} or len(keys) < 5
    return False


def main() -> int:
    from backend.app.config import settings

    print(f"{'model':<30} {'status':<14} {'size':>10}   path")
    print("-" * 100)

    problems = []
    for key, spec in sorted(settings.models.items()):
        if not spec.checkpoint_path:
            continue
        p = PROJECT_ROOT / spec.checkpoint_path
        exp = EXPECTED_MB.get(key)

        if not p.exists():
            status = "HF-backed" if key in HUGGINGFACE_BACKED else "MISSING"
            if key not in HUGGINGFACE_BACKED:
                problems.append(f"{key}: no file at {spec.checkpoint_path}")
            print(f"{key:<30} {status:<14} {'-':>10}   {spec.checkpoint_path}")
            continue

        verdict, size_mb = describe(p)
        if is_placeholder(p):
            verdict = "PLACEHOLDER"
            problems.append(
                f"{key}: {spec.checkpoint_path} is a {size_mb*1000:.0f} KB placeholder, "
                f"not weights (expected ~{exp} MB)"
            )
        elif exp and size_mb < exp * 0.5:
            verdict = "TOO SMALL"
            problems.append(f"{key}: {size_mb:.1f} MB but expected ~{exp} MB")
        else:
            verdict = "OK"

        print(f"{key:<30} {verdict:<14} {size_mb:>8.1f}MB   {spec.checkpoint_path}")

    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        print(
            "\nNote: grounding_dino and sam2 load from HuggingFace by model_id and need\n"
            "no local file — 'HF-backed' is expected and fine."
        )
        return 1

    print("All configured checkpoints present and plausible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
