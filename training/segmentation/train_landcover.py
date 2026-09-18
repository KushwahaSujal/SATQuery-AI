"""Multi-class semantic segmentation trainer (255 = ignore) for an 8 GB GPU.

Same shape as train_seg.py: random crops at the task GSD, whole tiles for validation and test,
best checkpoint by validation mIoU, test scored once. Loss is cross-entropy + soft Dice. Epoch
lines use train_seg's JSON layout (val.iou = mIoU, f1 = mean F1, precision/recall = class means,
threshold 0) so scripts/watch_training.py can show them; per-class IoU is in "per_class".

--taxonomy picks the class list, source registry, Dataset and default GSD from
datasets.SEG_TASKS; it defaults to "landcover", which is exactly the old behaviour.

    .venv/bin/python -m training.segmentation.train_landcover --task landcover \
        --sources deepglobe_landcover loveda openearthmap

    .venv/bin/python -m training.segmentation.train_landcover --task isprs_urban \
        --taxonomy isprs_urban --sources isprs_potsdam    # see docs/models/isprs_urban.md
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import ConcatDataset, DataLoader

from training.segmentation.datasets import IGNORE, SEG_TASKS
from training.segmentation.train_seg import build_model

ROOT = Path(__file__).resolve().parents[2]


def soft_dice(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    K = logits.shape[1]  # class count comes from the head, so any taxonomy works unchanged
    valid = (target != IGNORE).unsqueeze(1)
    prob = torch.softmax(logits, 1) * valid
    onehot = F.one_hot(target.clamp(max=K - 1), K).permute(0, 3, 1, 2) * valid
    inter = (prob * onehot).sum((0, 2, 3))
    denom = prob.sum((0, 2, 3)) + onehot.sum((0, 2, 3))
    present = onehot.sum((0, 2, 3)) > 0
    return (1 - (2 * inter + 1) / (denom + 1))[present].mean()


@torch.no_grad()
def infer_logits(model, img: torch.Tensor, window: int = 1024, overlap: int = 128) -> torch.Tensor:
    h, w = img.shape[-2:]
    K = model.segmentation_head[0].out_channels

    def run(x):
        xh, xw = x.shape[-2:]
        x = F.pad(x, (0, (32 - xw % 32) % 32, 0, (32 - xh % 32) % 32), mode="reflect")
        with torch.autocast("cuda", dtype=torch.float16, enabled=x.is_cuda):
            return torch.softmax(model(x)[..., :xh, :xw].float(), 1)

    if max(h, w) <= window + overlap:
        return run(img)
    out = torch.zeros((1, K, h, w), device=img.device)
    weight = torch.zeros((1, 1, h, w), device=img.device)
    step = window - overlap
    for y in sorted({*range(0, max(h - window, 0) + 1, step), max(h - window, 0)}):
        for x in sorted({*range(0, max(w - window, 0) + 1, step), max(w - window, 0)}):
            out[..., y:y + window, x:x + window] += run(img[..., y:y + window, x:x + window])
            weight[..., y:y + window, x:x + window] += 1
    return out / weight


@torch.no_grad()
def evaluate(model, loader, device, classes: list[str]) -> dict:
    model.eval()
    K = len(classes)
    conf = torch.zeros((K, K), dtype=torch.int64, device=device)
    for img, mask in loader:
        img, mask = img.to(device), mask.to(device)
        pred = infer_logits(model, img).argmax(1)
        v = mask != IGNORE
        conf += torch.bincount(mask[v] * K + pred[v], minlength=K * K).view(K, K)
    conf = conf.double().cpu().numpy()
    tp = np.diag(conf)
    gt, pr = conf.sum(1), conf.sum(0)
    present = gt > 0
    iou = tp / np.maximum(gt + pr - tp, 1)
    f1 = 2 * tp / np.maximum(gt + pr, 1)
    prec, rec = tp / np.maximum(pr, 1), tp / np.maximum(gt, 1)
    return {
        "iou": round(float(iou[present].mean()), 4), "f1": round(float(f1[present].mean()), 4),
        "precision": round(float(prec[present].mean()), 4), "recall": round(float(rec[present].mean()), 4),
        "pixel_acc": round(float(tp.sum() / max(conf.sum(), 1)), 4), "threshold": 0.0,
        "per_class": {c: (round(float(iou[i]), 4) if present[i] else None) for i, c in enumerate(classes)},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="checkpoint/report name under checkpoints/")
    ap.add_argument("--taxonomy", default="landcover", choices=sorted(SEG_TASKS),
                    help="class list + source registry + default GSD (datasets.SEG_TASKS)")
    ap.add_argument("--sources", nargs="+", required=True,
                    choices=sorted({s for _, srcs, _, _ in SEG_TASKS.values() for s in srcs}))
    ap.add_argument("--target-gsd", type=float, default=None,
                    help="metres per pixel; default is the taxonomy's (0.5 land cover, 0.1 ISPRS)")
    ap.add_argument("--arch", default="unet")
    ap.add_argument("--encoder", default="resnet34")
    ap.add_argument("--crop", type=int, default=512)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--samples-per-epoch", type=int, default=4000)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-val-tiles", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--resume", action="store_true", help="continue from <out>/last.pt (saved every epoch)")
    args = ap.parse_args()

    CLASSES, SOURCES, default_gsd, Tiles = SEG_TASKS[args.taxonomy]
    K = len(CLASSES)
    target_gsd = default_gsd if args.target_gsd is None else args.target_gsd
    bad = [s for s in args.sources if s not in SOURCES]
    if bad:
        ap.error(f"sources {bad} are not in taxonomy {args.taxonomy!r}; it has {sorted(SOURCES)}")

    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out = ROOT / f"checkpoints/{args.task}_seg"
    out.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.epochs, args.samples_per_epoch, args.max_val_tiles = 2, 64, 4

    counts = {s: {k: len(SOURCES[s](k)) for k in ("train", "val", "test")} for s in args.sources}
    print("tiles:", json.dumps(counts), flush=True)
    train_sets = [Tiles(SOURCES[s]("train"), args.crop, True, target_gsd) for s in args.sources]
    val_items = [x for s in args.sources for x in SOURCES[s]("val")]
    if len(val_items) > args.max_val_tiles:
        val_items = random.Random(args.seed).sample(val_items, args.max_val_tiles)
    weights = torch.cat([torch.full((len(d),), 1.0 / len(d)) for d in train_sets])
    train_loader = DataLoader(ConcatDataset(train_sets), batch_size=args.batch,
                              sampler=torch.utils.data.WeightedRandomSampler(weights, args.samples_per_epoch),
                              num_workers=args.workers, pin_memory=True, drop_last=True,
                              persistent_workers=args.workers > 0)
    val_loader = DataLoader(Tiles(val_items, None, False, target_gsd), batch_size=1,
                            num_workers=args.workers)

    model = build_model(args.arch, args.encoder)
    head = model.segmentation_head[0]
    model.segmentation_head[0] = torch.nn.Conv2d(head.in_channels, K, head.kernel_size, padding=head.padding)
    model = model.to(device).to(memory_format=torch.channels_last)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    steps = args.epochs * len(train_loader)
    warm = min(500, steps // 10)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, steps - warm))))
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")

    history, best, start_epoch = [], -1.0, 0
    last_path = out / "last.pt"
    if args.resume and last_path.exists():
        st = torch.load(last_path, map_location=device, weights_only=False)
        model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"])
        sched.load_state_dict(st["sched"]); scaler.load_state_dict(st["scaler"])
        history, best, start_epoch = st["history"], st["best"], st["epoch"]
        print(f"resumed from {last_path} after epoch {start_epoch}", flush=True)
    for epoch in range(start_epoch + 1, args.epochs + 1):
        model.train()
        t0, total, n_steps = time.time(), 0.0, len(train_loader)
        for step, (img, mask) in enumerate(train_loader, 1):
            img = img.to(device, non_blocking=True).to(memory_format=torch.channels_last)
            mask = mask.to(device, non_blocking=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                logits = model(img)
            logits = logits.float()
            loss = F.cross_entropy(logits, mask, ignore_index=IGNORE) + soft_dice(logits, mask)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            total += loss.item()
            if step % 25 == 0 or step == n_steps:
                el = time.time() - t0
                print(f"progress epoch={epoch}/{args.epochs} step={step}/{n_steps} "
                      f"elapsed={el:.1f}s rate={step / el:.2f}it/s", flush=True)
        print(f"phase=validate epoch={epoch}/{args.epochs}", flush=True)
        m = evaluate(model, val_loader, device, CLASSES)
        row = {"epoch": epoch, "loss": round(total / n_steps, 4), "val": m, "sec": round(time.time() - t0, 1)}
        history.append(row)
        print(json.dumps(row), flush=True)
        if m["iou"] > best:
            best = m["iou"]
            torch.save({"model": model.state_dict(), "arch": args.arch, "encoder": args.encoder,
                        "classes": CLASSES, "taxonomy": args.taxonomy, "target_gsd": target_gsd,
                        "epoch": epoch, "val": m}, out / "best.tmp")
            (out / "best.tmp").replace(out / "best.pt")
        tmp = last_path.with_suffix(".tmp")  # write-then-rename: a power cut cannot leave a torn file
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                    "scaler": scaler.state_dict(), "history": history, "best": best, "epoch": epoch}, tmp)
        tmp.replace(last_path)

    print("phase=test", flush=True)
    ckpt = torch.load(out / "best.pt", map_location=device)
    model.load_state_dict(ckpt["model"])
    per_source = {}
    for s in args.sources:
        items = SOURCES[s]("test")[: 4 if args.smoke else None]
        per_source[s] = evaluate(model, DataLoader(Tiles(items, None, False, target_gsd), batch_size=1,
                                                   num_workers=args.workers), device, CLASSES)
    report = {"task": args.task, "args": vars(args), "tiles": counts, "classes": CLASSES,
              "best_epoch": ckpt["epoch"], "val_at_best": ckpt["val"], "threshold_frozen_on_val": None,
              "test_all": None, "test_per_source": per_source, "history": history,
              "gpu": torch.cuda.get_device_name() if device.type == "cuda" else "cpu",
              "peak_gpu_mem_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2) if device.type == "cuda" else None}
    (out / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("best_epoch", "test_per_source", "peak_gpu_mem_gb")}, indent=2))


if __name__ == "__main__":
    main()
