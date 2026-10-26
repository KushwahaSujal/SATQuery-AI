"""Ship detector (single class) on MASATI-v2 (Bing Maps RGB, ~512 px tiles), with YOLO.

Splits: MASATI's own output/{train,val,test} (3617 / 452 / 453 images). About half the images are
negatives (open sea, coast, land with no vessel) and keep their empty label files, so the detector
learns to return nothing on them. Image lists go to datasets/processed/ships/ and the checkpoint to
checkpoints/ships_yolo/. The test split is scored once, after training, with the best-on-val weights.

Log lines follow train_seg.py's format for scripts/watch_training.py: epoch "val" holds
iou = mAP50 and f1 = mAP50-95 (named in "labels").

    .venv/bin/python -m training.detection.train_ships --epochs 80
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASATI = ROOT / "datasets/raw/masati_v2_ships/MASATI/output"
OUT = ROOT / "datasets/processed/ships"
LABELS = ["mAP50", "mAP50-95"]


def write_lists() -> dict[str, int]:
    OUT.mkdir(parents=True, exist_ok=True)
    counts = {}
    for split in ("train", "val", "test"):
        paths = sorted((MASATI / split / "images").glob("*.png"))
        (OUT / f"{split}.txt").write_text("".join(f"{p}\n" for p in paths))
        counts[split] = len(paths)
    (OUT / "data.yaml").write_text(
        f"path: {OUT}\ntrain: {OUT / 'train.txt'}\nval: {OUT / 'val.txt'}\ntest: {OUT / 'test.txt'}\n"
        "nc: 1\nnames: ['ship']\n")
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(ROOT / "checkpoints/pretrained/yolo11s.pt"))
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--project", default=str(ROOT / "checkpoints"), help="run directory parent")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    from ultralytics import YOLO

    counts = write_lists()
    print("tiles:", json.dumps({"masati": counts}), flush=True)
    project, name = Path(args.project), "ships_yolo"
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
        tl = trainer.tloss
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
                batch=args.batch, workers=args.workers, project=str(project), name=name,
                exist_ok=True, cache=False, fraction=0.05 if args.smoke else 1.0, verbose=False, plots=False,
                seed=0, deterministic=False)

    run = project / name
    print("phase=test", flush=True)
    best = YOLO(str(run / "weights/best.pt"))
    r = best.val(data=str(OUT / "data.yaml"), imgsz=args.imgsz, batch=args.batch, split="test",
                 plots=False, verbose=False, project=str(project), name=f"{name}_test", exist_ok=True)
    test = {"tiles": counts["test"], "iou": round(float(r.box.map50), 4), "f1": round(float(r.box.map), 4),
            "precision": round(float(r.box.mp), 4), "recall": round(float(r.box.mr), 4), "labels": LABELS}
    report = {"task": "ships_yolo", "args": vars(args), "tiles": {"masati": counts}, "labels": LABELS,
              "test_per_source": {"masati": test}, "weights": str(run / "weights/best.pt")}
    (run / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(test, indent=2), flush=True)


if __name__ == "__main__":
    main()
