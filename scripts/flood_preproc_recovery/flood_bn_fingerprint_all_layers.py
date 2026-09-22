"""Pin the flood model's training-time normalisation using ALL its BatchNorm layers.

Round 1 (`flood_recover_from_bn_stats.py`) matched only `encoder1.block.1`, the first BatchNorm, and
that turned out to be necessary but not sufficient: scaling per-scene min-max by 1.2078 matched layer
one well and then collapsed to IoU 0.41, because a global input scale propagates and mismatches every
*later* layer differently.

So this script uses the whole network as the fingerprint. Every BatchNorm in the model stores
`running_mean` / `running_var` estimated, during training, from its own input. A forward hook captures
what each BatchNorm actually receives under a candidate normalisation, and the candidate is scored by
how far those statistics sit from the stored ones, aggregated over all 18 layers. Only the genuinely
correct preprocessing can match the whole stack, because errors compound with depth.

No labels are involved and the TRAIN split is used -- the split the running statistics were estimated
on -- so there is nothing to overfit and no test leakage.

Handling of non-finite input matters here: 6 of the 90 official test scenes (and some training
scenes) carry NaN in the Sentinel-1 bands, one of them entirely NaN. A per-scene percentile taken
with `np.percentile` returns NaN for such a channel and silently poisons the whole scene, which is a
bug that affected the earlier label-based sweep (project/qna.md Q-044). Percentiles here are
nan-aware and non-finite pixels are replaced after normalisation.
"""
import json
import sys

import numpy as np
import rasterio
import torch

sys.path.insert(0, "/home/natsu/dev/isro")
from backend.app.ml.adapters.flood_unet import build_flood_model  # noqa: E402

BASE = "/home/natsu/dev/isro/datasets/raw/sen1floods11/sen1floods11_v1.1"
CKPT = "/home/natsu/dev/isro/checkpoints/flood_seg/best.pt"
SUB = {"s1": ("S1GRDHand", "S1Hand"), "s2": ("S2L1CHand", "S2Hand"),
       "dem": ("CopernicusDEM", "DEM")}
N_SCENES = 24          # 24 x 512 x 512 is ample for per-channel statistics at every depth
PERCENTILES = [0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]


def read_raw(sid):
    parts = []
    for k in ("s1", "s2", "dem"):
        sub, suf = SUB[k]
        with rasterio.open(f"{BASE}/data/{sub}/{sid}_{suf}.tif") as ds:
            parts.append(ds.read().astype(np.float32))
    return np.concatenate(parts, axis=0)


def normalise_per_scene(x, p):
    """Scale each channel into [0, 1] using its own nan-aware p / (100-p) percentiles."""
    f = x.reshape(16, -1)
    if p == 0.0:
        lo = np.nanmin(f, axis=1)
        hi = np.nanmax(f, axis=1)
    else:
        lo = np.nanpercentile(f, p, axis=1)
        hi = np.nanpercentile(f, 100.0 - p, axis=1)
    lo = np.nan_to_num(lo).reshape(16, 1, 1)
    hi = np.nan_to_num(hi).reshape(16, 1, 1)
    y = (x - lo) / np.maximum(hi - lo, 1e-6)
    y = np.clip(y, 0.0, 1.0)
    return np.nan_to_num(y, nan=0.0, posinf=1.0, neginf=0.0)


def collect_bn_layers(model):
    """Every BatchNorm2d, with its stored statistics."""
    out = []
    for name, mod in model.named_modules():
        if isinstance(mod, torch.nn.BatchNorm2d):
            out.append((name, mod))
    return out


def main():
    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = build_flood_model(state_dict=ck["model_state_dict"])
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(dev).eval()

    layers = collect_bn_layers(model)
    print(f"{len(layers)} BatchNorm layers will be compared against their stored statistics")

    captured = {}

    def make_hook(name):
        def hook(_mod, inputs, _out):
            x = inputs[0].detach()
            acc = captured.setdefault(name, [0, None, None])
            flat = x.permute(1, 0, 2, 3).reshape(x.shape[1], -1).double()
            acc[0] += flat.shape[1]
            s1 = flat.sum(1)
            s2 = (flat ** 2).sum(1)
            acc[1] = s1 if acc[1] is None else acc[1] + s1
            acc[2] = s2 if acc[2] is None else acc[2] + s2
        return hook

    handles = [mod.register_forward_hook(make_hook(name)) for name, mod in layers]

    ids = [l.strip() for l in open(f"{BASE}/splits/flood_train_data.txt") if l.strip()][:N_SCENES]
    print(f"{len(ids)} scenes from the official TRAIN split\n")
    raws = [read_raw(s) for s in ids]

    results = {}
    for p in PERCENTILES:
        captured.clear()
        for x in raws:
            xn = normalise_per_scene(x, p).astype(np.float32)
            with torch.no_grad():
                model(torch.from_numpy(xn[None]).to(dev))
            del xn
        per_layer = []
        for name, mod in layers:
            n, s1, s2 = captured[name]
            m = (s1 / n).cpu().numpy()
            v = np.maximum((s2 / n).cpu().numpy() - m ** 2, 1e-12)
            bm = mod.running_mean.detach().cpu().numpy().astype(np.float64)
            bv = mod.running_var.detach().cpu().numpy().astype(np.float64)
            log_std = np.abs(np.log2(np.sqrt(v) / np.sqrt(bv)))
            mean_off = np.abs(m - bm) / np.sqrt(bv)
            per_layer.append((name, float(np.median(log_std)), float(np.median(mean_off))))
        med_std = float(np.median([r[1] for r in per_layer]))
        med_mean = float(np.median([r[2] for r in per_layer]))
        worst = max(per_layer, key=lambda r: r[1])
        results[p] = dict(median_log2_std=med_std, median_mean_off=med_mean,
                         worst_layer=worst[0], worst_log2_std=worst[1],
                         per_layer=per_layer)
        print(f"p={p:<5} median|log2(std/std*)|={med_std:.4f}  "
              f"median|dmean|/std*={med_mean:.4f}  worst={worst[0]} ({worst[1]:.3f})")

    for h in handles:
        h.remove()

    best = min(results, key=lambda k: results[k]["median_log2_std"] + results[k]["median_mean_off"])
    print(f"\n--> best over all {len(layers)} layers: per-scene percentile clip at "
          f"p={best} / {100 - best}")
    print(f"\nper-layer detail for p={best}:")
    print(f"{'layer':28s} {'med|log2 std|':>14s} {'med|dmean|/std*':>17s}")
    for name, ls, mo in results[best]["per_layer"]:
        print(f"{name:28s} {ls:14.4f} {mo:17.4f}")

    dest = ("/home/natsu/dev/isro/results/evaluations/"
            "flood_preproc_recovery_20260920/bn_fingerprint_all_layers.json")
    with open(dest, "w") as fh:
        json.dump({str(k): {kk: vv for kk, vv in v.items() if kk != "per_layer"}
                   for k, v in results.items()} | {"_meta": {
                       "n_scenes": len(ids), "split": "flood_train_data",
                       "n_bn_layers": len(layers), "best_percentile": best}}, fh, indent=1)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
