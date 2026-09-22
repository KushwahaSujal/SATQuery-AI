#!/usr/bin/env python3
"""Probe: does the delivered burn-scar checkpoint instantiate from its delivered config?

This script answers a *dependency-safety and architectural-truth* question only.
It does NOT and CANNOT verify the delivered metrics (burn-scar IoU 0.6567): the HLS
Burn Scars imagery is not present on this machine (nothing matching *burn*/*hls*
under datasets/raw/, no entry in datasets/manifests/training_sources.yaml).

It must be run from a SEPARATE venv that has terratorch installed. It must never be
run from the project's .venv, which deliberately does not have terratorch:

    /home/natsu/.venvs/terratorch-probe/bin/python scripts/verify_burnscars_terratorch.py

CPU only. The 3.6 GB checkpoint is opened with mmap=True + weights_only=True and loaded
with assign=True, so the tensors are never copied into resident memory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CKPT = REPO / "checkpoints/burnscars_seg/PrithviEO2_300M_BurnScars_from_scratch_epoch08.ckpt"
DEFAULT_CFG = REPO / "docs/models/burnscars/model_config.yaml"


def _dist_version(name: str) -> str:
    import importlib.metadata as md

    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return "not installed"


def rss_mb() -> float:
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=DEFAULT_CKPT)
    ap.add_argument("--config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    import torch
    import yaml

    torch.set_grad_enabled(False)
    torch.set_num_threads(4)

    import terratorch
    import lightning

    report: dict = {
        "versions": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "terratorch": _dist_version("terratorch"),
            "lightning": lightning.__version__,
        }
    }
    print("== versions ==")
    for k, v in report["versions"].items():
        print(f"  {k}: {v}")

    # ---- 1. the delivered config -------------------------------------------------
    cfg = yaml.safe_load(args.config.read_text())
    init_args = dict(cfg["model"]["init_args"])
    model_args = dict(init_args["model_args"])
    print("\n== delivered model_args ==")
    print(json.dumps(model_args, indent=2))

    # ---- 2. build the model from that config, via terratorch ---------------------
    from terratorch.tasks import SemanticSegmentationTask

    task_kwargs = {k: v for k, v in init_args.items() if k != "model_args"}
    print("\n== building SemanticSegmentationTask ==")
    task = SemanticSegmentationTask(model_args=model_args, **task_kwargs)
    task.eval()
    n_params = sum(p.numel() for p in task.model.parameters())
    print(f"  built. task.model params: {n_params:,}")
    report["built_param_count"] = n_params
    report["built_model_class"] = type(task.model).__name__

    # ---- 3. load the checkpoint's state_dict, strict=True ------------------------
    print(f"\n== loading {args.ckpt.name} (mmap, weights_only) ==")
    ckpt = torch.load(args.ckpt, map_location="cpu", mmap=True, weights_only=True)
    sd = ckpt["state_dict"]
    print(f"  state_dict tensors: {len(sd)}")
    print(f"  ckpt tensor params: {sum(t.numel() for t in sd.values()):,}")
    report["ckpt_tensor_count"] = len(sd)
    report["ckpt_param_count"] = int(sum(t.numel() for t in sd.values()))

    strict_ok = True
    missing: list[str] = []
    unexpected: list[str] = []
    try:
        task.load_state_dict(sd, strict=True, assign=True)
        print("  load_state_dict(strict=True): OK")
    except RuntimeError as exc:
        strict_ok = False
        print("  load_state_dict(strict=True): FAILED")
        print(f"  {exc}")
        res = task.load_state_dict(sd, strict=False, assign=True)
        missing = list(res.missing_keys)
        unexpected = list(res.unexpected_keys)
        print(f"  strict=False -> missing {len(missing)}, unexpected {len(unexpected)}")
        for k in missing:
            print(f"    MISSING    {k}")
        for k in unexpected:
            print(f"    UNEXPECTED {k}")

    report["strict_load_ok"] = strict_ok
    report["missing_keys"] = missing
    report["unexpected_keys"] = unexpected

    # shape agreement on every shared key
    model_sd = task.state_dict()
    shape_mismatch = {
        k: [list(sd[k].shape), list(model_sd[k].shape)]
        for k in sd
        if k in model_sd and tuple(sd[k].shape) != tuple(model_sd[k].shape)
    }
    report["shape_mismatches"] = shape_mismatch
    print(f"  shape mismatches on shared keys: {len(shape_mismatch)}")
    for k, (a, b) in shape_mismatch.items():
        print(f"    {k}: ckpt {a} vs built {b}")

    # ---- 3b. BatchNorm audit -----------------------------------------------------
    # The decoder/neck BatchNorms carry running statistics. If they are still at
    # initialisation (running_mean 0, running_var 1, num_batches_tracked 0) then in
    # eval() mode every BN degenerates to y = weight * x / sqrt(1 + eps) + bias, and
    # eval-mode inference is NOT equivalent to training-time behaviour if training
    # used batch statistics. Compare docs/models/flood.md / qna.md Q-044.
    bn = {"at_init": [], "trained": [], "num_batches_tracked": {}}
    for k in sorted(sd):
        if k.endswith("running_var"):
            base = k[: -len("running_var")]
            rv, rm = sd[k], sd[base + "running_mean"]
            at_init = bool(
                torch.all(rv == 1.0).item() and torch.all(rm == 0.0).item()
            )
            (bn["at_init"] if at_init else bn["trained"]).append(base)
        if k.endswith("num_batches_tracked"):
            bn["num_batches_tracked"][k] = int(sd[k])
    n_init, n_tr = len(bn["at_init"]), len(bn["trained"])
    print("\n== BatchNorm running-statistics audit ==")
    print(f"  BN layers with running stats: {n_init + n_tr}")
    print(f"    at initialisation (mean 0 / var 1): {n_init}")
    print(f"    carrying trained statistics:        {n_tr}")
    nbt = set(bn["num_batches_tracked"].values())
    print(f"  num_batches_tracked distinct values: {sorted(nbt)}")
    if n_init and not n_tr:
        print("  *** ALL BN running stats are at init while affine weights ARE trained.")
        print("  *** eval() BN is then a pure affine map; train/eval behaviour may differ.")
    # show the affine weights drifted from init 1.0, i.e. the model really did train
    for base in (bn["at_init"] + bn["trained"])[:3]:
        w = sd[base + "weight"]
        print(
            f"    {base}weight: mean={w.mean().item():.4f} std={w.std().item():.4f} "
            f"(init would be exactly 1.0 / 0.0)"
        )
    report["batchnorm"] = {
        "n_at_init": n_init,
        "n_trained": n_tr,
        "num_batches_tracked_values": sorted(nbt),
        "at_init_layers": bn["at_init"],
    }

    del ckpt, sd

    # ---- 4. one CPU forward pass on a synthetic 6-band 224x224 tile --------------
    print("\n== forward pass: 1 x 6 x 224 x 224 ==")
    g = torch.Generator().manual_seed(0)
    means = torch.tensor(cfg["data"]["init_args"]["means"]).view(1, 6, 1, 1)
    stds = torch.tensor(cfg["data"]["init_args"]["stds"]).view(1, 6, 1, 1)
    refl = torch.rand(1, 6, 224, 224, generator=g)  # synthetic reflectance in [0, 1]
    x = (refl - means) / stds
    out = task.model(x)
    logits = out.output if hasattr(out, "output") else out
    print(f"  output type: {type(out).__name__}")
    print(f"  logits shape: {tuple(logits.shape)}")
    print(f"  logits dtype: {logits.dtype}")
    print(f"  logits min/max: {logits.min().item():.6f} / {logits.max().item():.6f}")
    report["forward_output_type"] = type(out).__name__
    report["forward_logits_shape"] = list(logits.shape)
    report["forward_logits_minmax"] = [logits.min().item(), logits.max().item()]
    ok_shape = tuple(logits.shape) == (1, 2, 224, 224)
    report["forward_shape_as_expected"] = ok_shape
    print(f"  == (1, 2, 224, 224)? {ok_shape}")

    print(f"\n== peak-ish RSS: {rss_mb():.0f} MB ==")
    report["rss_mb"] = rss_mb()

    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2))
        print(f"wrote {args.json_out}")

    return 0 if (strict_ok and ok_shape) else 1


if __name__ == "__main__":
    raise SystemExit(main())
