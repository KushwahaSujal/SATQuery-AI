"""Search preprocessing candidates on the Sen1Floods11 VALIDATION split, then score the winner
once on the test split.

Tuning on validation and reporting on test is the only defensible way to do this: picking a scheme
by its test IoU and then quoting that IoU would be selecting on the test set.
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


def read(sid):
    sc = {}
    for key, (sub, suf) in SUB.items():
        with rasterio.open(f"{BASE}/data/{sub}/{sid}_{suf}.tif") as ds:
            sc[key] = ds.read().astype(np.float32)
    return sc


def cat(s1, s2, dem):
    return np.concatenate([s1, s2, dem], axis=0)


# Each scheme: raw stored values -> network input.
SCHEMES = {
    "raw": lambda s: cat(s["s1"], s["s2"], s["dem"]),
    "s2/3000": lambda s: cat(s["s1"], s["s2"] / 3000.0, s["dem"]),
    "s2/4000": lambda s: cat(s["s1"], s["s2"] / 4000.0, s["dem"]),
    "s1clip30_s2/10k_dem0": lambda s: cat(
        (np.clip(s["s1"], -30, 0) + 30) / 30.0, s["s2"] / 10000.0, np.zeros_like(s["dem"])),
    "raw_dem0": lambda s: cat(s["s1"], s["s2"], np.zeros_like(s["dem"])),
    "raw_s1_0": lambda s: cat(np.zeros_like(s["s1"]), s["s2"], s["dem"]),
    "s2/10k_s1/10_dem/100": lambda s: cat(s["s1"] / 10.0, s["s2"] / 10000.0, s["dem"] / 100.0),
    "div255": lambda s: cat(s["s1"], s["s2"] / 255.0, s["dem"]),
    "s2_p2p98": None,  # filled below
    "raw_dem_centered": lambda s: cat(s["s1"], s["s2"], s["dem"] - s["dem"].mean()),
}


def _p2p98(s):
    s2 = s["s2"]
    lo = np.percentile(s2, 2, axis=(1, 2), keepdims=True)
    hi = np.percentile(s2, 98, axis=(1, 2), keepdims=True)
    return cat(s["s1"], np.clip((s2 - lo) / (hi - lo + 1e-6), 0, 1), s["dem"])


SCHEMES["s2_p2p98"] = _p2p98


def evaluate(model, dev, ids, schemes, thresholds=(0.5,)):
    acc = {(n, t): dict(tp=0, fp=0, fn=0, tn=0, per=[]) for n in schemes for t in thresholds}
    for i, sid in enumerate(ids, 1):
        sc = read(sid)
        lab = sc["label"][0]
        valid = lab >= 0
        gt = (lab == 1) & valid
        for name, fn in schemes.items():
            x = fn(sc)
            with torch.no_grad():
                prob = torch.softmax(
                    model(torch.from_numpy(x[None]).to(dev)).float(), 1)[0, 1].cpu().numpy()
            for t in thresholds:
                pred = (prob >= t) & valid
                tp = int((pred & gt).sum()); fp = int((pred & ~gt & valid).sum())
                fnn = int((~pred & gt).sum()); tn = int((~pred & ~gt & valid).sum())
                a = acc[(name, t)]
                a["tp"] += tp; a["fp"] += fp; a["fn"] += fnn; a["tn"] += tn
                d = tp + fp + fnn
                a["per"].append(tp / d if d else np.nan)
            del x
        del sc
        if i % 25 == 0:
            print(f"    {i}/{len(ids)}")
    return acc


def report(acc, title):
    print(f"\n=== {title} ===")
    print(f"{'scheme':24s} {'thr':>5s} {'IoU':>7s} {'perScn':>7s} {'prec':>7s} {'rec':>7s} {'F1':>7s} {'pixAcc':>7s}")
    print("-" * 78)
    rows = []
    for (name, t), a in sorted(acc.items()):
        tp, fp, fn, tn = a["tp"], a["fp"], a["fn"], a["tn"]
        iou = tp / (tp + fp + fn) if (tp + fp + fn) else 0
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
        pa = (tp + tn) / (tp + tn + fp + fn)
        per = float(np.nanmean(a["per"]))
        rows.append((iou, name, t, per, prec, rec, f1, pa))
    for iou, name, t, per, prec, rec, f1, pa in sorted(rows, reverse=True):
        print(f"{name:24s} {t:5.2f} {iou:7.4f} {per:7.4f} {prec:7.4f} {rec:7.4f} {f1:7.4f} {pa:7.4f}")
    return sorted(rows, reverse=True)


def main():
    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = build_flood_model(state_dict=ck["model_state_dict"])
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(dev).eval()
    print("checkpoint reports validation flood IoU", ck["metrics"]["validation_flood_iou"],
          "and validation pixel accuracy", ck["metrics"]["validation_pixel_accuracy"])

    val = [ln.strip() for ln in open(f"{BASE}/splits/flood_valid_data.txt") if ln.strip()]
    print(f"\nsearching {len(SCHEMES)} schemes on {len(val)} validation scenes")
    acc = evaluate(model, dev, val, SCHEMES)
    rows = report(acc, f"VALIDATION ({len(val)} scenes), argmax")
    print("\nCheckpoint's own recorded validation: flood IoU "
          f"{ck['metrics']['validation_flood_iou']:.4f}, pixel accuracy "
          f"{ck['metrics']['validation_pixel_accuracy']:.4f}")

    best = rows[0][1]
    print(f"\n--> best on validation: {best}. Scoring it once on the test split.")
    test = [ln.strip() for ln in open(f"{BASE}/splits/flood_test_data.txt") if ln.strip()]
    acc2 = evaluate(model, dev, test, {best: SCHEMES[best]}, thresholds=(0.3, 0.5))
    report(acc2, f"TEST ({len(test)} scenes) with '{best}'")
    print("\nDelivered (their 67-scene subset): argmax IoU 0.6292 prec 0.7873 rec 0.7580 "
          "pixAcc 0.9557 | thr0.30 IoU 0.6211 prec 0.7220 rec 0.8164")


if __name__ == "__main__":
    main()
