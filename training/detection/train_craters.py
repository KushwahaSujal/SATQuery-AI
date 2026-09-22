"""Crater detector (single class) on LU3M6TGT (Moon) + the Kaggle Mars/Lunar crater set, with YOLO.

Splits: LU3M6TGT ships only train/valid, so its valid set is hash-split 50/50 into our val and
test. The Mars/Lunar set keeps its own train/valid/test. Image lists are written to
datasets/processed/craters/ and the checkpoint to checkpoints/craters_yolo/.

Craters are tiny (LU3M6TGT median box ≈ 9 px at 416 px, up to 506 per tile), so training runs at
832 px with max_det 1000. The test split is scored once, after training, with the best-on-val weights.

Log lines follow train_seg.py's format for scripts/watch_training.py: epoch "val" holds
iou = mAP50 and f1 = mAP50-95 (named in "labels").

    .venv/bin/python -m training.detection.train_craters --epochs 60
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "datasets/raw"
LU = RAW / "craters_lu3m6tgt/LU3M6TGT_yolo_format"
MM = RAW / "craters_mars_moon/craters"
OUT = ROOT / "datasets/processed/craters"
LABELS = ["mAP50", "mAP50-95"]


def _half(stem: str) -> str:
    return "test" if int(hashlib.sha1(stem.encode()).hexdigest(), 16) % 2 else "val"


def write_lists() -> dict[str, int]:
    splits: dict[str, list[Path]] = {"train": [], "val": [], "test": []}
    splits["train"] += sorted((LU / "train/images").glob("*"))
    for p in sorted((LU / "valid/images").glob("*")):
        splits[_half(p.stem)].append(p)
    splits["train"] += sorted((MM / "train/images").glob("*"))
    splits["val"] += sorted((MM / "valid/images").glob("*"))
    splits["test"] += sorted((MM / "test/images").glob("*"))
    OUT.mkdir(parents=True, exist_ok=True)
    for k, paths in splits.items():
        (OUT / f"{k}.txt").write_text("".join(f"{p}\n" for p in paths))
    (OUT / "data.yaml").write_text(
        f"path: {OUT}\ntrain: {OUT / 'train.txt'}\nval: {OUT / 'val.txt'}\ntest: {OUT / 'test.txt'}\n"
        "nc: 1\nnames: ['crater']\n")
    return {k: len(v) for k, v in splits.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(ROOT / "checkpoints/pretrained/yolo11s.pt"))
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--imgsz", type=int, default=832)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    from ultralytics import YOLO

    counts = write_lists()
    print("tiles:", json.dumps({"craters": {"train": counts["train"], "val": counts["val"], "test": counts["test"]}}),
          flush=True)
    project, name = ROOT / "checkpoints", "craters_yolo"
    model = YOLO(args.model)
    state = {"t0": time.time(), "step": 0}

    def on_epoch_start(trainer):
        state["t0"], state["step"] = time.time(), 0

    def on_batch_end(trainer):
        state["step"] += 1
        n = len(trainer.train_loader)
        if state["step"] % 25 == 0 or state["step"] == n:
            el = time.time() - state["t0"]
            print(f"progress epoch={trainer.epoch + 1}/{trainer.epochs} step={state['step']}/{n} "
                  f"elapsed={el:.1f}s rate={state['step'] / el:.2f}it/s", flush=True)

    def on_fit_epoch_end(trainer):
        if trainer.epoch + 1 > trainer.epochs:  # final re-validation after training, not a new epoch
            return
        m = trainer.metrics
        tl = trainer.tloss  # dict of running-mean loss components in ultralytics 8.4
        loss = sum(float(v) for v in tl.values()) if isinstance(tl, dict) else float(tl.sum())
        row = {"epoch": trainer.epoch + 1, "loss": round(loss, 4), "labels": LABELS,
               "val": {"iou": round(m.get("metrics/mAP50(B)", 0), 4), "f1": round(m.get("metrics/mAP50-95(B)", 0), 4),
                       "precision": round(m.get("metrics/precision(B)", 0), 4),
                       "recall": round(m.get("metrics/recall(B)", 0), 4), "threshold": 0.0},
               "sec": round(time.time() - state["t0"], 1)}
        print(json.dumps(row), flush=True)

    model.add_callback("on_train_epoch_start", on_epoch_start)
    model.add_callback("on_train_batch_end", on_batch_end)
    model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

    model.train(data=str(OUT / "data.yaml"), epochs=2 if args.smoke else args.epochs, imgsz=args.imgsz,
                batch=args.batch, workers=args.workers, max_det=1000, project=str(project), name=name,
                exist_ok=True, cache=False, fraction=0.02 if args.smoke else 1.0, verbose=False, plots=False,
                seed=0, deterministic=False)

    run = project / name
    print("phase=test", flush=True)
    best = YOLO(str(run / "weights/best.pt"))
    per_source = {}
    for tag, lst in (("lu3m6tgt", [p for p in (OUT / "test.txt").read_text().split() if str(LU) in p]),
                     ("mars_moon", [p for p in (OUT / "test.txt").read_text().split() if str(MM) in p])):
        sub = OUT / f"test_{tag}.txt"
        sub.write_text("".join(f"{p}\n" for p in lst))
        yaml_path = OUT / f"test_{tag}.yaml"
        yaml_path.write_text(f"path: {OUT}\ntrain: {OUT / 'train.txt'}\nval: {sub}\nnc: 1\nnames: ['crater']\n")
        r = best.val(data=str(yaml_path), imgsz=args.imgsz, batch=args.batch, max_det=1000, split="val",
                     plots=False, verbose=False, project=str(project), name=f"{name}_test_{tag}", exist_ok=True)
        per_source[tag] = {"tiles": len(lst), "iou": round(float(r.box.map50), 4), "f1": round(float(r.box.map), 4),
                           "precision": round(float(r.box.mp), 4), "recall": round(float(r.box.mr), 4),
                           "labels": LABELS}
        shutil.rmtree(project / f"{name}_test_{tag}", ignore_errors=True)
    report = {"task": "craters_yolo", "args": vars(args), "tiles": {"craters": counts}, "labels": LABELS,
              "best_epoch": None, "threshold_frozen_on_val": None, "test_all": None,
              "test_per_source": per_source, "weights": str(run / "weights/best.pt")}
    (ROOT / "checkpoints/craters_yolo_seg").mkdir(parents=True, exist_ok=True)
    (ROOT / "checkpoints/craters_yolo_seg/report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(per_source, indent=2), flush=True)


if __name__ == "__main__":
    main()
