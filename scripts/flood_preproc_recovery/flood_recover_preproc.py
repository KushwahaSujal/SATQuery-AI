"""Recover the flood model's training-time preprocessing empirically.

The delivery (docs/models/flood/) fixes the 16-channel order but never states the normalisation.
Wrong normalisation on a BatchNorm network does not crash, it just predicts badly -- so we sweep
candidate schemes over the official Sen1Floods11 test split and compare against the delivered
report (global flood IoU 0.629 at argmax, 0.621 at threshold 0.30, per-scene mean 0.407).

Ground truth LabelHand uses -1 nodata / 0 no-flood / 1 flood; -1 pixels are excluded.
"""
import sys
import numpy as np
import rasterio
import torch

sys.path.insert(0, "/home/natsu/dev/isro")
from backend.app.ml.adapters.flood_unet import build_flood_model  # noqa: E402

BASE = "/home/natsu/dev/isro/datasets/raw/sen1floods11/sen1floods11_v1.1"
CKPT = "/home/natsu/dev/isro/checkpoints/flood_seg/best.pt"
SUB = {"s1": ("S1GRDHand", "S1Hand"), "s2": ("S2L1CHand", "S2Hand"),
       "dem": ("CopernicusDEM", "DEM"), "label": ("LabelHand", "LabelHand")}


def scene_ids(split="flood_test_data"):
    with open(f"{BASE}/splits/{split}.txt") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def read_scene(sid):
    out = {}
    for key, (sub, suf) in SUB.items():
        with rasterio.open(f"{BASE}/data/{sub}/{sid}_{suf}.tif") as ds:
            out[key] = ds.read().astype(np.float32)
    return out


# ---- candidate preprocessing schemes -------------------------------------------------------
def stack(s1, s2, dem):
    return np.concatenate([s1, s2, dem], axis=0)


def p_raw(sc):
    """Everything as stored: S1 in dB, S2 as int16 DN, DEM in metres."""
    return stack(sc["s1"], sc["s2"], sc["dem"])


def p_s2_10k(sc):
    """S2 divided by 10000 into reflectance; S1 and DEM untouched."""
    return stack(sc["s1"], sc["s2"] / 10000.0, sc["dem"])


def p_s2_10k_dem_1k(sc):
    """S2 reflectance, DEM in kilometres, S1 untouched."""
    return stack(sc["s1"], sc["s2"] / 10000.0, sc["dem"] / 1000.0)


def p_s1_shift(sc):
    """S1 mapped from roughly [-50, 0] dB into [0, 1]; S2 reflectance; DEM in km."""
    return stack((sc["s1"] + 50.0) / 50.0, sc["s2"] / 10000.0, sc["dem"] / 1000.0)


def p_per_scene_z(sc):
    """Per-channel z-score computed on the scene itself."""
    x = stack(sc["s1"], sc["s2"], sc["dem"])
    m = x.reshape(x.shape[0], -1).mean(1)[:, None, None]
    s = x.reshape(x.shape[0], -1).std(1)[:, None, None] + 1e-6
    return (x - m) / s


def p_per_scene_minmax(sc):
    """Per-channel min-max to [0, 1] on the scene itself."""
    x = stack(sc["s1"], sc["s2"], sc["dem"])
    lo = x.reshape(x.shape[0], -1).min(1)[:, None, None]
    hi = x.reshape(x.shape[0], -1).max(1)[:, None, None]
    return (x - lo) / (hi - lo + 1e-6)


def p_s2_10k_z_s1(sc):
    """S2 reflectance, S1 z-scored per scene, DEM z-scored per scene."""
    s1 = sc["s1"]
    s1 = (s1 - s1.mean()) / (s1.std() + 1e-6)
    dem = sc["dem"]
    dem = (dem - dem.mean()) / (dem.std() + 1e-6)
    return stack(s1, sc["s2"] / 10000.0, dem)


SCHEMES = {
    "raw": p_raw,
    "s2/10k": p_s2_10k,
    "s2/10k+dem/1k": p_s2_10k_dem_1k,
    "s1shift+s2/10k+dem/1k": p_s1_shift,
    "per_scene_z": p_per_scene_z,
    "per_scene_minmax": p_per_scene_minmax,
    "s2/10k+z(s1,dem)": p_s2_10k_z_s1,
}


def main():
    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = build_flood_model(state_dict=ck["model_state_dict"])
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(dev).eval()
    print(f"loaded {CKPT} (epoch {ck['epoch']}), strict=True OK, device={dev}")

    ids = scene_ids()
    print(f"official Sen1Floods11 test split: {len(ids)} scenes\n")

    # accumulate a global confusion matrix per scheme, plus per-scene IoU
    acc = {k: dict(tp=0, fp=0, fn=0, tn=0, per=[]) for k in SCHEMES}

    for n, sid in enumerate(ids, 1):
        sc = read_scene(sid)
        lab = sc["label"][0]
        valid = lab >= 0
        gt = (lab == 1) & valid
        for name, fn in SCHEMES.items():
            x = fn(sc)
            with torch.no_grad():
                t = torch.from_numpy(x[None]).to(dev)
                logit = model(t)
                pred = logit.argmax(1)[0].cpu().numpy().astype(bool)
            pred &= valid
            tp = int((pred & gt).sum()); fp = int((pred & ~gt & valid).sum())
            fn_ = int((~pred & gt).sum()); tn = int((~pred & ~gt & valid).sum())
            a = acc[name]
            a["tp"] += tp; a["fp"] += fp; a["fn"] += fn_; a["tn"] += tn
            den = tp + fp + fn_
            a["per"].append(tp / den if den else float("nan"))
            del x, t, logit
        del sc
        if n % 15 == 0:
            print(f"  {n}/{len(ids)} scenes")

    print(f"\n{'scheme':24s} {'globalIoU':>10s} {'perSceneIoU':>12s} {'prec':>7s} {'rec':>7s} {'F1':>7s} {'pixAcc':>8s}")
    print("-" * 80)
    rows = []
    for name, a in acc.items():
        tp, fp, fn_, tn = a["tp"], a["fp"], a["fn"], a["tn"]
        iou = tp / (tp + fp + fn_) if (tp + fp + fn_) else 0.0
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn_) if (tp + fn_) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        pa = (tp + tn) / (tp + tn + fp + fn_)
        per = float(np.nanmean(a["per"]))
        rows.append((iou, name))
        print(f"{name:24s} {iou:10.4f} {per:12.4f} {prec:7.4f} {rec:7.4f} {f1:7.4f} {pa:8.4f}")

    print("\nDelivered report (their 67-scene subset): global flood IoU 0.6292 argmax, "
          "per-scene mean 0.4075, precision 0.7873, recall 0.7580, F1 0.7724, pixAcc 0.9557")
    rows.sort(reverse=True)
    print(f"\nbest scheme: {rows[0][1]}  (global IoU {rows[0][0]:.4f})")


if __name__ == "__main__":
    main()
