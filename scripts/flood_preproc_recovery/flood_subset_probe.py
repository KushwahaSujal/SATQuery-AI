"""With raw preprocessing fixed, find which 67-scene subset of the 90 official test scenes
reproduces the delivered numbers -- and record per-scene stats so any subset can be scored
without re-running the model.
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
OUT = "/tmp/claude-1000/-home-natsu-dev-isro/562f4605-c65e-440f-8528-d05fa5ffd5b5/scratchpad/flood_per_scene.json"
SUB = {"s1": ("S1GRDHand", "S1Hand"), "s2": ("S2L1CHand", "S2Hand"),
       "dem": ("CopernicusDEM", "DEM"), "label": ("LabelHand", "LabelHand")}


def main():
    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = build_flood_model(state_dict=ck["model_state_dict"])
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(dev).eval()

    ids = [ln.strip() for ln in open(f"{BASE}/splits/flood_test_data.txt") if ln.strip()]
    recs = []
    for n, sid in enumerate(ids, 1):
        sc = {}
        for key, (sub, suf) in SUB.items():
            with rasterio.open(f"{BASE}/data/{sub}/{sid}_{suf}.tif") as ds:
                sc[key] = ds.read().astype(np.float32)
        lab = sc["label"][0]
        valid = lab >= 0
        gt = (lab == 1) & valid
        x = np.concatenate([sc["s1"], sc["s2"], sc["dem"]], axis=0)
        with torch.no_grad():
            logit = model(torch.from_numpy(x[None]).to(dev))
            prob = torch.softmax(logit.float(), 1)[0, 1].cpu().numpy()
        pred = (prob >= 0.5) & valid
        tp = int((pred & gt).sum()); fp = int((pred & ~gt & valid).sum())
        fn = int((~pred & gt).sum()); tn = int((~pred & ~gt & valid).sum())
        # threshold 0.30, the delivery's calibrated value
        p30 = (prob >= 0.30) & valid
        tp30 = int((p30 & gt).sum()); fp30 = int((p30 & ~gt & valid).sum())
        fn30 = int((~p30 & gt).sum()); tn30 = int((~p30 & ~gt & valid).sum())
        recs.append(dict(
            sid=sid, tp=tp, fp=fp, fn=fn, tn=tn,
            tp30=tp30, fp30=fp30, fn30=fn30, tn30=tn30,
            valid=int(valid.sum()), nodata=int((~valid).sum()),
            gt_flood=int(gt.sum()),
            s2_zeros=int((sc["s2"] == 0).all(axis=0).sum()),
            s2_min=float(sc["s2"].min()), s1_nan=int(np.isnan(sc["s1"]).sum()),
            dem_min=float(sc["dem"].min()),
        ))
        del sc, x, logit
        if n % 20 == 0:
            print(f"  {n}/{len(ids)}")

    json.dump(recs, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")

    def score(rs, suffix=""):
        tp = sum(r["tp" + suffix] for r in rs); fp = sum(r["fp" + suffix] for r in rs)
        fn = sum(r["fn" + suffix] for r in rs); tn = sum(r["tn" + suffix] for r in rs)
        iou = tp / (tp + fp + fn) if (tp + fp + fn) else 0
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
        pa = (tp + tn) / (tp + tn + fp + fn)
        per = np.nanmean([r["tp" + suffix] / d if (d := r["tp" + suffix] + r["fp" + suffix] + r["fn" + suffix]) else np.nan for r in rs])
        return iou, per, prec, rec, f1, pa, tp, fp, fn, tn

    print(f"\n{'subset':34s} {'n':>3s} {'IoU':>7s} {'perScn':>7s} {'prec':>7s} {'rec':>7s} {'F1':>7s} {'pixAcc':>7s}")
    print("-" * 84)
    cands = {
        "all 90 (argmax)": recs,
        "all 90 (thr 0.30)": recs,
        "no label nodata": [r for r in recs if r["nodata"] == 0],
        "has some flood gt": [r for r in recs if r["gt_flood"] > 0],
        "no all-zero S2 px": [r for r in recs if r["s2_zeros"] == 0],
        "s2_min > 0": [r for r in recs if r["s2_min"] > 0],
        "no nodata AND flood gt": [r for r in recs if r["nodata"] == 0 and r["gt_flood"] > 0],
    }
    for name, rs in cands.items():
        suf = "30" if "0.30" in name else ""
        if not rs:
            continue
        iou, per, prec, rec, f1, pa, *_ = score(rs, suf)
        print(f"{name:34s} {len(rs):3d} {iou:7.4f} {per:7.4f} {prec:7.4f} {rec:7.4f} {f1:7.4f} {pa:7.4f}")

    print("\nDelivered (67 scenes, argmax): IoU 0.6292 perScene 0.4075 prec 0.7873 rec 0.7580 "
          "F1 0.7724 pixAcc 0.9557")
    print("Delivered (67 scenes, thr 0.30): IoU 0.6211 prec 0.7220 rec 0.8164 F1 0.7663 pixAcc 0.9507")
    print("\nDelivered pixel total: 15152361 valid px. Ours (90):",
          sum(r["valid"] for r in recs))


if __name__ == "__main__":
    main()
