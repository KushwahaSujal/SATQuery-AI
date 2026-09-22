"""Recover the flood model's training-time normalisation from its own BatchNorm statistics.

The delivery never documented the preprocessing, and scoring candidate schemes against labels was
inconclusive (project/qna.md Q-041 §5: nothing reproduced the reported IoU 0.6292, and the
best-scoring scheme needed the DEM channel zeroed, which cannot be what a DEM-trained model did).

This script uses a different, label-free signal. `encoder1.block.1` is a BatchNorm2d whose
`running_mean` / `running_var` were estimated, during training, from the output of
`encoder1.block.0` — i.e. from whatever the *normalised* inputs actually were. So the stored
statistics are a fingerprint of the training-time input distribution:

    conv is linear, so  stats(conv(x_norm))  is determined by  stats(x_norm).

For a candidate normalisation P we push real training-split scenes through the first convolution and
compare the resulting per-channel activation statistics with the stored ones. The correct P should
match; a wrong scale shows up immediately, because the stored means are O(0.1-1) while raw
Sentinel-2 digital numbers are O(1000).

Two properties make this stronger than the label-based sweep:
  * it needs no labels at all, so there is nothing to overfit;
  * it reads the TRAIN split, which is what the running statistics were estimated on, so there is no
    test leakage even in principle.

Caveat recorded up front: BN running statistics are an exponential moving average (momentum 0.1), so
they reflect the last few dozen batches rather than the exact dataset mean, and any training-time
augmentation also shaped them. Treat a close match as strong evidence and an order-of-magnitude
mismatch as decisive refutation -- not the reverse.
"""
import json
import sys

import numpy as np
import rasterio
import torch

sys.path.insert(0, "/home/natsu/dev/isro")

BASE = "/home/natsu/dev/isro/datasets/raw/sen1floods11/sen1floods11_v1.1"
CKPT = "/home/natsu/dev/isro/checkpoints/flood_seg/best.pt"
SUB = {"s1": ("S1GRDHand", "S1Hand"), "s2": ("S2L1CHand", "S2Hand"),
       "dem": ("CopernicusDEM", "DEM")}
CHANNELS = ["S1_VV", "S1_VH", "B1", "B2", "B3", "B4", "B5", "B6",
            "B7", "B8", "B8A", "B9", "B10", "B11", "B12", "DEM"]
#: Enough scenes for stable per-channel statistics without loading the whole split.
N_SCENES = 48


def scene_ids(split):
    with open(f"{BASE}/splits/{split}.txt") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def read_raw(sid):
    """The 16-channel stack exactly as stored on disk, no scaling of any kind."""
    parts = []
    for key in ("s1", "s2", "dem"):
        sub, suf = SUB[key]
        with rasterio.open(f"{BASE}/data/{sub}/{sid}_{suf}.tif") as ds:
            parts.append(ds.read().astype(np.float32))
    return np.concatenate(parts, axis=0)


def dataset_stats(ids):
    """Per-channel mean/std/min/max/percentiles over the sampled scenes, computed streaming."""
    n = 0
    s1 = np.zeros(16, np.float64)
    s2 = np.zeros(16, np.float64)
    lo = np.full(16, np.inf)
    hi = np.full(16, -np.inf)
    samples = []
    for sid in ids:
        x = read_raw(sid)
        flat = x.reshape(16, -1)
        finite = np.isfinite(flat)
        flat = np.where(finite, flat, 0.0)
        n += flat.shape[1]
        s1 += flat.sum(1)
        s2 += (flat.astype(np.float64) ** 2).sum(1)
        lo = np.minimum(lo, flat.min(1))
        hi = np.maximum(hi, flat.max(1))
        # a thin spatial subsample, for percentiles
        samples.append(flat[:, ::997])
        del x, flat
    mean = s1 / n
    var = np.maximum(s2 / n - mean ** 2, 1e-12)
    cat = np.concatenate(samples, axis=1)
    p2 = np.percentile(cat, 2, axis=1)
    p98 = np.percentile(cat, 98, axis=1)
    return dict(mean=mean.astype(np.float32), std=np.sqrt(var).astype(np.float32),
                min=lo.astype(np.float32), max=hi.astype(np.float32),
                p2=p2.astype(np.float32), p98=p98.astype(np.float32))


def build_schemes(st):
    """Candidate normalisations, each a function (16,H,W) raw -> (16,H,W) normalised."""
    ch = lambda v: v.reshape(16, 1, 1)

    def zscore_dataset(x):
        return (x - ch(st["mean"])) / ch(st["std"])

    def minmax_dataset(x):
        return (x - ch(st["min"])) / ch(st["max"] - st["min"] + 1e-6)

    def p2p98_dataset(x):
        return np.clip((x - ch(st["p2"])) / ch(st["p98"] - st["p2"] + 1e-6), 0, 1)

    def zscore_per_scene(x):
        m = x.reshape(16, -1).mean(1).reshape(16, 1, 1)
        s = x.reshape(16, -1).std(1).reshape(16, 1, 1) + 1e-6
        return (x - m) / s

    def minmax_per_scene(x):
        f = x.reshape(16, -1)
        m = f.min(1).reshape(16, 1, 1)
        M = f.max(1).reshape(16, 1, 1)
        return (x - m) / (M - m + 1e-6)

    def raw(x):
        return x

    def phys(x):
        """The 'obvious physical' scaling: S2 to reflectance, S1 dB as-is, DEM in km."""
        y = x.copy()
        y[2:15] /= 10000.0
        y[15] /= 1000.0
        return y

    def phys_s1shift(x):
        y = x.copy()
        y[0:2] = (np.clip(y[0:2], -30, 0) + 30) / 30.0
        y[2:15] /= 10000.0
        y[15] /= 1000.0
        return y

    return {
        "zscore_dataset": zscore_dataset,
        "minmax_dataset": minmax_dataset,
        "p2p98_dataset": p2p98_dataset,
        "zscore_per_scene": zscore_per_scene,
        "minmax_per_scene": minmax_per_scene,
        "phys(S2/1e4,DEM/1e3)": phys,
        "phys+S1clip": phys_s1shift,
        "raw": raw,
    }


def main():
    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    sd = ck["model_state_dict"]
    W = sd["encoder1.block.0.weight"]                       # (16,16,3,3), bias-free
    bn_mean = sd["encoder1.block.1.running_mean"].numpy()
    bn_var = sd["encoder1.block.1.running_var"].numpy()
    nbt = int(sd["encoder1.block.1.num_batches_tracked"])
    print(f"stored encoder1 BN stats: num_batches_tracked={nbt}")
    print(f"  |running_mean| in [{np.abs(bn_mean).min():.4f}, {np.abs(bn_mean).max():.4f}]  "
          f"running_std in [{np.sqrt(bn_var).min():.4f}, {np.sqrt(bn_var).max():.4f}]")

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    W = W.to(dev)

    ids = scene_ids("flood_train_data")[:N_SCENES]
    print(f"\nsampling {len(ids)} scenes from the official TRAIN split "
          f"(the split the running statistics were estimated on)")
    st = dataset_stats(ids)
    np.set_printoptions(precision=3, suppress=True, linewidth=200)
    print("\nper-channel raw dataset statistics:")
    for i, name in enumerate(CHANNELS):
        print(f"  {name:6s} mean {st['mean'][i]:12.3f}  std {st['std'][i]:10.3f}  "
              f"min {st['min'][i]:10.2f}  max {st['max'][i]:10.2f}")

    schemes = build_schemes(st)
    results = {}
    for name, fn in schemes.items():
        acc_n = 0
        acc_s1 = np.zeros(16, np.float64)
        acc_s2 = np.zeros(16, np.float64)
        for sid in ids:
            x = read_raw(sid)
            xn = fn(x).astype(np.float32)
            xn = np.nan_to_num(xn, nan=0.0, posinf=0.0, neginf=0.0)
            with torch.no_grad():
                out = torch.nn.functional.conv2d(
                    torch.from_numpy(xn[None]).to(dev), W, padding=1)[0]
            o = out.reshape(16, -1).double()
            acc_n += o.shape[1]
            acc_s1 += o.sum(1).cpu().numpy()
            acc_s2 += (o ** 2).sum(1).cpu().numpy()
            del x, xn, out, o
        m = acc_s1 / acc_n
        v = np.maximum(acc_s2 / acc_n - m ** 2, 1e-12)
        # Scale-free discrepancy: how far the activation std is from the stored std, in octaves,
        # plus the mean offset expressed in units of the stored std.
        log_std_err = np.abs(np.log2(np.sqrt(v) / np.sqrt(bn_var)))
        mean_err = np.abs(m - bn_mean) / np.sqrt(bn_var)
        results[name] = dict(
            mean=m, var=v,
            median_log2_std_err=float(np.median(log_std_err)),
            max_log2_std_err=float(np.max(log_std_err)),
            median_mean_err=float(np.median(mean_err)),
        )

    print(f"\n{'scheme':24s} {'med |log2(std/std*)|':>21s} {'max':>8s} {'med |dmean|/std*':>18s}")
    print("-" * 78)
    for name, r in sorted(results.items(), key=lambda kv: kv[1]["median_log2_std_err"]):
        print(f"{name:24s} {r['median_log2_std_err']:21.3f} {r['max_log2_std_err']:8.3f} "
              f"{r['median_mean_err']:18.3f}")
    print("\nA value of 0 in column 1 means the activation spread matches training exactly;")
    print("1.0 means it is off by a factor of two, 10 means a factor of ~1000.")

    best = min(results, key=lambda k: results[k]["median_log2_std_err"])
    print(f"\n--> closest to the stored statistics: {best}")
    r = results[best]
    print(f"\nper-channel comparison for '{best}':")
    print(f"{'ch':>3s} {'act mean':>10s} {'BN mean':>10s} {'act std':>10s} {'BN std':>10s}")
    for i in range(16):
        print(f"{i:3d} {r['mean'][i]:10.4f} {bn_mean[i]:10.4f} "
              f"{np.sqrt(r['var'][i]):10.4f} {np.sqrt(bn_var[i]):10.4f}")

    out = {k: dict(median_log2_std_err=v["median_log2_std_err"],
                   max_log2_std_err=v["max_log2_std_err"],
                   median_mean_err=v["median_mean_err"]) for k, v in results.items()}
    out["_meta"] = dict(n_scenes=len(ids), split="flood_train_data",
                        num_batches_tracked=nbt, best=best)
    dest = ("/home/natsu/dev/isro/results/evaluations/"
            "flood_preproc_recovery_20260920/bn_fingerprint.json")
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
