"""Fine-tune Grounding DINO (IDEA-Research/grounding-dino-base) on DIOR-RSVG referring expressions.

DIOR-RSVG: 38,320 (image, box, expression) records over 17,402 DIOR images; the split files hold
0-based record indices in sorted-annotation order. Two leaks rule out the official split as-is:
- the official train/val/test share images (6,020 images carry records from more than one split);
- 3,250 of the 4,686 DIOR images in VRSBench val (the prescribed benchmark and our adoption gate)
  are in DIOR-RSVG train.
So training uses only records whose image is in neither VRSBench val nor any official test record.
"test_clean" is the official test records, image-disjoint from training by construction; "val" is a
5 % hash of the remaining images. Both are scored with the base model first (zero-shot baseline).

Image and text encoders are frozen (Swin-B 88M, BERT 110M); the fusion transformer, decoder and
heads train in fp16 autocast, which fits the 8 GB RTX 3070. Metric: Acc@0.5 of the top-1 box
(the DIOR-RSVG convention) and mean IoU. Best-on-val weights go to checkpoints/grounding_dino_rsvg/.

    .venv/bin/python -m training.grounding.finetune_grounding_dino --epochs 2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[2]
RSVG = ROOT / "datasets/raw/dior_rsvg"
VRS_VAL = ROOT / "datasets/raw/vrsbench/images/Images_val"
BASE = "IDEA-Research/grounding-dino-base"
OUT = ROOT / "checkpoints/grounding_dino_rsvg"


def records() -> dict[str, list[dict]]:
    splits = {s: {int(x) for x in (RSVG / f"{s}.txt").read_text().split()} for s in ("train", "val", "test")}
    recs, i = [], 0
    for xml in sorted((RSVG / "Annotations").glob("*.xml")):
        for obj in ET.parse(xml).getroot().findall("object"):
            b = obj.find("bndbox")
            recs.append({"idx": i, "image": xml.stem, "path": str(RSVG / "JPEGImages" / f"{xml.stem}.jpg"),
                         "expr": obj.findtext("description").strip(),
                         "box": [float(b.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax")],
                         "official": next(s for s, v in splits.items() if i in v)})
            i += 1
    vrs = {f.split("_")[0] for f in os.listdir(VRS_VAL) if f[0].isdigit()}
    test_imgs = {r["image"] for r in recs if r["official"] == "test"}
    out: dict[str, list[dict]] = {"train": [], "val": [], "test_clean": []}
    for r in recs:
        if r["official"] == "test":
            out["test_clean"].append(r)
        elif r["image"] not in vrs and r["image"] not in test_imgs:
            h = int(hashlib.sha1(r["image"].encode()).hexdigest(), 16) % 100
            out["val" if h < 5 else "train"].append(r)
    return out


def vrsbench_referring() -> list[dict]:
    """All 16,159 VRSBench val referring queries (the prescribed benchmark), as top-1 grounding records."""
    out = []
    for q in json.loads((VRS_VAL.parent.parent / "VRSBench_EVAL_referring.json").read_text()):
        pct = [float(v) for v in q["ground_truth"].strip("{}<>").split("><")]
        out.append({"image": q["image_id"], "path": str(VRS_VAL / q["image_id"]), "expr": q["question"],
                    "box_pct": pct, "unique": q["unique"]})
    return out


class Records(Dataset):
    def __init__(self, recs: list[dict]):
        self.recs = recs

    def __len__(self) -> int:
        return len(self.recs)

    def __getitem__(self, i: int):
        r = self.recs[i]
        img = Image.open(r["path"]).convert("RGB")
        if "box_pct" in r:  # VRSBench: {<x1><y1><x2><y2>} in percent of the image size
            w, h = img.size
            r = r | {"box": [r["box_pct"][0] * w / 100, r["box_pct"][1] * h / 100,
                             r["box_pct"][2] * w / 100, r["box_pct"][3] * h / 100]}
        return img, r


def text_of(expr: str) -> str:
    return expr.lower().rstrip(".") + "."


def collate(processor):
    def fn(batch):
        images, recs = zip(*batch)
        enc = processor(images=list(images), text=[text_of(r["expr"]) for r in recs], return_tensors="pt",
                        padding=True)
        labels = []
        for img, r in zip(images, recs):
            w, h = img.size
            x0, y0, x1, y1 = r["box"]
            labels.append({"class_labels": torch.tensor([0]),
                           "boxes": torch.tensor([[(x0 + x1) / 2 / w, (y0 + y1) / 2 / h, (x1 - x0) / w, (y1 - y0) / h]])})
        return enc, labels, list(recs), [img.size for img in images]
    return fn


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@torch.no_grad()
def evaluate(model, loader, device, tag: str = "eval", limit: int | None = None) -> dict:
    """Top-1 box per expression. Prints "eval tag=... step=i/N elapsed=..s rate=..it/s" lines so
    scripts/watch_training.py can show an ETA for the long evaluation passes (VRSBench is 16,159)."""
    model.eval()
    ious, n, t0 = [], len(loader.dataset), time.time()
    for enc, _, recs, sizes in loader:
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            out = model(**enc)
        # Logits past the text length are -inf, so sigmoid zeroes them; rank queries by their best token.
        best = out.logits.sigmoid().float().max(-1).values.argmax(-1)
        for b, (r, (w, h)) in enumerate(zip(recs, sizes)):
            cx, cy, bw, bh = out.pred_boxes[b, best[b]].float().tolist()
            pred = [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h]
            ious.append(iou(pred, r["box"]))
        if len(ious) % 200 < len(recs) or len(ious) == n:
            el = time.time() - t0
            print(f"eval tag={tag} step={len(ious)}/{n} elapsed={el:.1f}s rate={len(ious) / el:.2f}it/s", flush=True)
        if limit and len(ious) >= limit:
            break
    a = np.array(ious)
    return {"n": len(a), "acc@0.5": round(float((a >= 0.5).mean()), 4), "acc@0.25": round(float((a >= 0.25).mean()), 4),
            "mean_iou": round(float(a.mean()), 4)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=1, help="2 runs out of the 8 GB RTX 3070")
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = records()
    if args.smoke:
        data = {k: v[:40] for k, v in data.items()}
        args.epochs = 1
    counts = {k: {"records": len(v), "images": len({r["image"] for r in v})} for k, v in data.items()}
    print("tiles:", json.dumps({"dior_rsvg": counts}), flush=True)

    processor = AutoProcessor.from_pretrained(BASE)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(BASE).to(device)
    for p in model.model.backbone.parameters():
        p.requires_grad = False
    for p in model.model.text_backbone.parameters():
        p.requires_grad = False
    trainable = [p for p in model.parameters() if p.requires_grad]
    print(f"trainable params: {sum(p.numel() for p in trainable) / 1e6:.1f} M", flush=True)

    col = collate(processor)
    mk = lambda split, shuffle: DataLoader(Records(data[split]), batch_size=args.batch, shuffle=shuffle,  # noqa: E731
                                          num_workers=args.workers, collate_fn=col, drop_last=shuffle)
    data["vrsbench"] = vrsbench_referring()[:40] if args.smoke else vrsbench_referring()
    train_loader, val_loader, test_loader = mk("train", True), mk("val", False), mk("test_clean", False)
    vrs_loader = mk("vrsbench", False)
    evals = {"val": len(data["val"]), "test_clean": len(data["test_clean"]), "vrsbench": len(data["vrsbench"])}
    print("plan:", json.dumps({"epochs": args.epochs, "train_steps": len(train_loader), "eval": evals,
                               "baseline": list(evals), "per_epoch": ["val"], "final": list(evals)}), flush=True)

    print("phase=baseline", flush=True)
    baseline = {"val": evaluate(model, val_loader, device, "val"),
                "test_clean": evaluate(model, test_loader, device, "test_clean"),
                "vrsbench_referring": evaluate(model, vrs_loader, device, "vrsbench")}
    print(json.dumps({"baseline": baseline}), flush=True)

    opt = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=1e-4)
    steps = args.epochs * len(train_loader) // args.accum
    warm = max(1, min(300, steps // 10))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, steps - warm))))
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")
    history, best = [], -1.0
    for epoch in range(args.epochs):
        model.train()
        t0, running = time.time(), 0.0
        for step, (enc, labels, _, _) in enumerate(train_loader, 1):
            enc = {k: v.to(device) for k, v in enc.items()}
            labels = [{k: v.to(device) for k, v in lab.items()} for lab in labels]
            with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                ld = model(**enc, labels=labels).loss_dict
            # Decoder Hungarian loss only, with the config's own coefficients. The two-stage encoder term
            # (loss_ce_enc) comes out ~5e4 on a single sample (decoder loss_ce ~4), which would swamp every
            # gradient, so it is left out (project/qna.md Q-075).
            cfg = model.config
            loss = (ld["loss_ce"] + cfg.bbox_loss_coefficient * ld["loss_bbox"]
                    + cfg.giou_loss_coefficient * ld["loss_giou"]) / args.accum
            scaler.scale(loss).backward()
            running += float(loss) * args.accum
            if step % args.accum == 0:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(trainable, 0.1)
                scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True); sched.step()
            if step % 50 == 0 or step == len(train_loader):
                el = time.time() - t0
                print(f"progress epoch={epoch + 1}/{args.epochs} step={step}/{len(train_loader)} "
                      f"elapsed={el:.1f}s rate={step / el:.2f}it/s loss={running / step:.4f}", flush=True)
        val = evaluate(model, val_loader, device, "val")
        row = {"epoch": epoch + 1, "loss": round(running / len(train_loader), 4), "val": val,
               "sec": round(time.time() - t0, 1)}
        history.append(row)
        print(json.dumps(row), flush=True)
        if val["acc@0.5"] > best:
            best = val["acc@0.5"]
            model.save_pretrained(out); processor.save_pretrained(out)

    print("phase=test", flush=True)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(out).to(device)
    report = {"task": "grounding_dino_rsvg", "base": BASE, "args": vars(args), "tiles": {"dior_rsvg": counts},
              "baseline_zero_shot": baseline,
              "finetuned": {"val": evaluate(model, val_loader, device, "val"),
                            "test_clean": evaluate(model, test_loader, device, "test_clean"),
                            "vrsbench_referring": evaluate(model, vrs_loader, device, "vrsbench")},
              "history": history,
              "peak_gpu_mem_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if device.type == "cuda" else None}
    (out / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("baseline_zero_shot", "finetuned")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
