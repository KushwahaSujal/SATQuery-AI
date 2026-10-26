"""Score a trained binary segmenter checkpoint on another source's test split (read-only).

Same evaluate()/infer_prob code and the checkpoint's own val-frozen threshold that train_seg.py uses
for its report, so the numbers line up with report.json's test_per_source / test_per_source_tta.
Used for cross-source questions such as "how does the served buildings model do on Inria cities it
never saw?" (project/qna.md Q-071).

    .venv/bin/python scripts/eval_segmenter_on_source.py \
        --ckpt checkpoints/buildings_whu_ma_r50_seg/best.pt --source inria --target-gsd 0.5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.segmentation.datasets import SOURCES, SegTiles  # noqa: E402
from training.segmentation.train_seg import at, build_model, evaluate  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--source", required=True, choices=sorted(SOURCES))
    ap.add_argument("--target-gsd", type=float, default=0.5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.ckpt, map_location=device, weights_only=False)
    bands = int(ckpt.get("in_channels", 3))
    model = build_model(ckpt["arch"], ckpt["encoder"], bands).to(device)
    model.load_state_dict(ckpt["model"])
    items = SOURCES[args.source]("test")
    loader = DataLoader(SegTiles(items, crop=None, train=False, target_gsd=args.target_gsd, bands=bands),
                        batch_size=1, num_workers=2)
    report = {"ckpt": args.ckpt, "source": args.source, "test_tiles": len(items),
              "threshold": ckpt["threshold"],
              "test": at(evaluate(model, loader, device), ckpt["threshold"]),
              "test_tta": at(evaluate(model, loader, device, tta=True), ckpt["threshold"])}
    out = Path(args.out or ROOT / f"results/eval/{Path(args.ckpt).parent.name}_on_{args.source}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
