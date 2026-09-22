"""Binary aerial segmentation trainer (roads, buildings, water) for an 8 GB GPU.

U-Net / D-LinkNet-style encoder-decoder from segmentation_models_pytorch, BCE + Dice loss,
mixed precision, random crops for training, whole tiles (padded to /32) for validation.
Validation IoU picks the best checkpoint; the test split is scored once, at the end, with
the threshold frozen on validation.

    .venv/bin/python -m training.segmentation.train_seg --task roads \
        --sources deepglobe_roads massachusetts_roads --epochs 40
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import segmentation_models_pytorch as smp
import torch
import torch.nn.functional as F
from torch.utils.data import ConcatDataset, DataLoader

from training.segmentation.datasets import SOURCES, TARGET_GSD_M, SegTiles

ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS = np.round(np.arange(0.2, 0.8, 0.05), 2)


def build_model(arch: str, encoder: str) -> torch.nn.Module:
    cls = {"unet": smp.Unet, "unetpp": smp.UnetPlusPlus, "linknet": smp.Linknet,
           "deeplabv3p": smp.DeepLabV3Plus, "segformer": smp.Segformer}[arch]
    return cls(encoder_name=encoder, encoder_weights="imagenet", in_channels=3, classes=1)


def dice_loss(logits: torch.Tensor, target: torch.Tensor, eps: float = 1.0) -> torch.Tensor:
    p = torch.sigmoid(logits).flatten(1)
    t = target.flatten(1)
    return (1 - (2 * (p * t).sum(1) + eps) / (p.sum(1) + t.sum(1) + eps)).mean()


@torch.no_grad()
def infer_prob(model, img: torch.Tensor, window: int = 1024, overlap: int = 128, tta: bool = False) -> torch.Tensor:
    """Sigmoid map for a (1,3,H,W) tile of any size: whole-tile if small, else overlapping windows.
    tta averages the identity, horizontal, vertical and double flips."""
    h, w = img.shape[-2:]

    def run_once(x):
        xh, xw = x.shape[-2:]
        x = F.pad(x, (0, (32 - xw % 32) % 32, 0, (32 - xh % 32) % 32), mode="reflect")
        with torch.autocast("cuda", dtype=torch.float16, enabled=x.is_cuda):
            return torch.sigmoid(model(x)[..., :xh, :xw].float())

    def run(x):
        if not tta:
            return run_once(x)
        flips = [(), (-1,), (-2,), (-2, -1)]
        return sum(run_once(x.flip(d) if d else x).flip(d) if d else run_once(x) for d in flips) / len(flips)

    if max(h, w) <= window + overlap:
        return run(img)
    prob = torch.zeros((1, 1, h, w), device=img.device)
    weight = torch.zeros_like(prob)
    step = window - overlap
    ys = sorted({*range(0, max(h - window, 0) + 1, step), max(h - window, 0)})
    xs = sorted({*range(0, max(w - window, 0) + 1, step), max(w - window, 0)})
    for y in ys:
        for x in xs:
            prob[..., y:y + window, x:x + window] += run(img[..., y:y + window, x:x + window])
            weight[..., y:y + window, x:x + window] += 1
    return prob / weight


@torch.no_grad()
def evaluate(model, loader, device, tta: bool = False) -> dict:
    """Pixel TP/FP/FN summed over the split, for every candidate threshold."""
    model.eval()
    tp = np.zeros(len(THRESHOLDS)); fp = np.zeros_like(tp); fn = np.zeros_like(tp)
    for img, mask, valid in loader:
        img, mask, valid = img.to(device), mask.to(device), valid.to(device)
        prob = infer_prob(model, img, tta=tta)
        m, valid = mask > 0.5, valid > 0.5
        for i, t in enumerate(THRESHOLDS):
            pred = (prob > t) & valid
            tp[i] += (pred & m).sum().item()
            fp[i] += (pred & ~m).sum().item()
            fn[i] += (~pred & m & valid).sum().item()
    iou = tp / np.maximum(tp + fp + fn, 1)
    f1 = 2 * tp / np.maximum(2 * tp + fp + fn, 1)
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / np.maximum(tp + fn, 1)
    return {"thresholds": THRESHOLDS.tolist(), "iou": iou.tolist(), "f1": f1.tolist(),
            "precision": precision.tolist(), "recall": recall.tolist()}


def at(metrics: dict, thr: float) -> dict:
    i = metrics["thresholds"].index(thr)
    return {k: round(metrics[k][i], 4) for k in ("iou", "f1", "precision", "recall")} | {"threshold": thr}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="output name, e.g. roads")
    ap.add_argument("--sources", nargs="+", required=True, choices=sorted(SOURCES))
    ap.add_argument("--arch", default="unet")
    ap.add_argument("--encoder", default="resnet34")
    ap.add_argument("--crop", type=int, default=512)
    ap.add_argument("--target-gsd", type=float, default=TARGET_GSD_M,
                    help="metres per pixel every source is resampled to. The 0.5 m default suits the "
                         "sub-metre road/building sources; pass the source's own GSD for coarse "
                         "imagery (10 for water_bodies, 30 for cloud95) so it is not upsampled")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--samples-per-epoch", type=int, default=4000,
                    help="random crops per epoch (tiles differ in size across sources)")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-val-tiles", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true", help="2 tiny epochs to check the pipeline")
    ap.add_argument("--resume", action="store_true",
                    help="continue from <out>/last.pt (saved after every epoch) if it exists")
    ap.add_argument("--warm-start", default=None,
                    help="best.pt of an interrupted run that predates last.pt: load its weights and resume the "
                         "LR schedule after its epoch (optimizer moments restart; not identical to no interruption)")
    args = ap.parse_args()

    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out = Path(args.out or ROOT / f"checkpoints/{args.task}_seg")
    out.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.epochs, args.samples_per_epoch, args.max_val_tiles = args.epochs if args.resume else 2, 64, 8

    def split(name):
        return [SOURCES[s](name) for s in args.sources]

    train_sets = [SegTiles(items, crop=args.crop, train=True, target_gsd=args.target_gsd)
                  for items in split("train")]
    val_items = [x for items in split("val") for x in items]
    test_items = [x for items in split("test") for x in items]
    rng = random.Random(args.seed)
    if len(val_items) > args.max_val_tiles:
        val_items = rng.sample(val_items, args.max_val_tiles)
    counts = {s: {k: len(SOURCES[s](k)) for k in ("train", "val", "test")} for s in args.sources}
    print("tiles:", json.dumps(counts))

    # Each source contributes equally per epoch, whatever its tile count.
    train = ConcatDataset(train_sets)
    weights = torch.cat([torch.full((len(d),), 1.0 / len(d)) for d in train_sets])
    sampler = torch.utils.data.WeightedRandomSampler(weights, args.samples_per_epoch)
    train_loader = DataLoader(train, batch_size=args.batch, sampler=sampler,
                              num_workers=args.workers, pin_memory=True, drop_last=True,
                              persistent_workers=args.workers > 0)
    val_loader = DataLoader(SegTiles(val_items, crop=None, train=False, target_gsd=args.target_gsd), batch_size=1,
                            num_workers=args.workers)

    model = build_model(args.arch, args.encoder).to(device).to(memory_format=torch.channels_last)
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
    elif args.warm_start:
        st = torch.load(args.warm_start, map_location=device, weights_only=False)
        model.load_state_dict(st["model"])
        start_epoch, best = st["epoch"], st["val"]["iou"]
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for _ in range(start_epoch * len(train_loader)):
                sched.step()
        print(f"warm-started from {args.warm_start} (epoch {start_epoch}, val IoU {best}); "
              f"LR now {sched.get_last_lr()[0]:.2e}; optimizer state reset", flush=True)
    for epoch in range(start_epoch + 1, args.epochs + 1):
        model.train()
        t0, total = time.time(), 0.0
        n_steps = len(train_loader)
        for step, (img, mask, valid) in enumerate(train_loader, 1):
            img = img.to(device, non_blocking=True).to(memory_format=torch.channels_last)
            mask, valid = mask.to(device, non_blocking=True), valid.to(device, non_blocking=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                logits = model(img)
            logits = logits.float()
            bce = (F.binary_cross_entropy_with_logits(logits, mask, reduction="none") * valid).sum() / valid.sum().clamp(min=1)
            loss = bce + dice_loss(logits.masked_fill(valid == 0, -1e4), mask * valid)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            total += loss.item()
            if step % 25 == 0 or step == n_steps:  # read by scripts/watch_training.py
                el = time.time() - t0
                print(f"progress epoch={epoch}/{args.epochs} step={step}/{n_steps} "
                      f"elapsed={el:.1f}s rate={step / el:.2f}it/s", flush=True)
        print(f"phase=validate epoch={epoch}/{args.epochs}", flush=True)
        m = evaluate(model, val_loader, device)
        bi = int(np.argmax(m["iou"]))
        row = {"epoch": epoch, "loss": round(total / len(train_loader), 4),
               "val": at(m, m["thresholds"][bi]), "sec": round(time.time() - t0, 1)}
        history.append(row)
        print(json.dumps(row), flush=True)
        if m["iou"][bi] > best:
            best = m["iou"][bi]
            torch.save({"model": model.state_dict(), "arch": args.arch, "encoder": args.encoder,
                        "threshold": m["thresholds"][bi], "epoch": epoch, "val": row["val"]},
                       out / "best.tmp")
            (out / "best.tmp").replace(out / "best.pt")
        tmp = last_path.with_suffix(".tmp")  # write-then-rename, so a power cut never leaves a torn last.pt
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                    "scaler": scaler.state_dict(), "history": history, "best": best, "epoch": epoch}, tmp)
        tmp.replace(last_path)

    print("phase=test", flush=True)
    ckpt = torch.load(out / "best.pt", map_location=device)
    model.load_state_dict(ckpt["model"])
    test_loader = DataLoader(SegTiles(test_items, crop=None, train=False, target_gsd=args.target_gsd), batch_size=1,
                             num_workers=args.workers)
    per_source, per_source_tta = {}, {}
    for s in args.sources:
        items = SOURCES[s]("test")
        if args.smoke:
            items = items[:4]
        loader = DataLoader(SegTiles(items, crop=None, train=False, target_gsd=args.target_gsd),
                            batch_size=1, num_workers=args.workers)
        per_source[s] = at(evaluate(model, loader, device), ckpt["threshold"])
        per_source_tta[s] = at(evaluate(model, loader, device, tta=True), ckpt["threshold"])
    report = {
        "task": args.task, "args": vars(args), "tiles": counts,
        "best_epoch": ckpt["epoch"], "val_at_best": ckpt["val"],
        "threshold_frozen_on_val": ckpt["threshold"],
        "test_all": at(evaluate(model, test_loader, device), ckpt["threshold"]) if not args.smoke else None,
        "test_per_source": per_source,
        "test_per_source_tta": per_source_tta,  # same threshold, 4-flip averaging; not used for selection
        "history": history,
        "gpu": torch.cuda.get_device_name() if device.type == "cuda" else "cpu",
        "peak_gpu_mem_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2) if device.type == "cuda" else None,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("best_epoch", "threshold_frozen_on_val", "test_all", "test_per_source",
                                             "test_per_source_tta", "peak_gpu_mem_gb")}, indent=2))


if __name__ == "__main__":
    main()
