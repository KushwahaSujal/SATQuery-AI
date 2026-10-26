"""Does the SpaceNet 7 built-up model track built-up *change* over time? (read-only)

Pixel IoU (report.json) answers "where are the buildings"; the deliverable question is "has the
built-up area increased, decreased or stayed the same?" (prd.md, representative queries). So per
held-out AOI and month this measures the built-up fraction of the usable (non-cloud) pixels, predicted
vs ground truth, and per AOI the first-to-last-month change:
  - sign agreement of the change (increase / decrease / unchanged within +-0.5 percentage points);
  - absolute error of the predicted change, in percentage points of the AOI;
  - Pearson r of predicted vs true fraction over every AOI-month.
Test AOIs are the honest numbers; val AOIs (used to freeze the threshold) are reported separately.

    .venv/bin/python scripts/eval_builtup_trend.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.segmentation.datasets import SOURCES, SegTiles  # noqa: E402
from training.segmentation.train_seg import build_model, infer_prob  # noqa: E402

CKPT = ROOT / "checkpoints/builtup_sn7_seg/best.pt"
TARGET_GSD = 2.4  # the run's --target-gsd (report.json args)
UNCHANGED_PP = 0.5


def direction(delta_pp: float) -> str:
    return "unchanged" if abs(delta_pp) <= UNCHANGED_PP else ("increase" if delta_pp > 0 else "decrease")


@torch.no_grad()
def score(split: str, model, thr: float, device) -> dict:
    items = SOURCES["spacenet7"](split)
    ds = SegTiles(items, crop=None, train=False, target_gsd=TARGET_GSD)
    series: dict[str, list[tuple[str, float, float]]] = defaultdict(list)
    for i, item in enumerate(items):
        x, mask, valid = ds[i]
        prob = infer_prob(model, x[None].to(device))[0, 0].cpu().numpy()
        v = valid[0].numpy() > 0
        if v.mean() < 0.5:  # mostly cloud: the month says nothing about built-up area
            continue
        aoi, month = Path(item[0]).stem.split("__")
        series[aoi].append((month, float((prob[v] >= thr).mean() * 100), float((mask[0].numpy()[v] > 0.5).mean() * 100)))
    per_aoi, pred_all, true_all = {}, [], []
    for aoi, s in series.items():
        s.sort()
        pred_all += [p for _, p, _ in s]; true_all += [t for _, _, t in s]
        dp, dt = s[-1][1] - s[0][1], s[-1][2] - s[0][2]
        per_aoi[aoi] = {"months": len(s), "first": s[0][0], "last": s[-1][0],
                        "true_change_pp": round(dt, 2), "pred_change_pp": round(dp, 2),
                        "true_direction": direction(dt), "pred_direction": direction(dp),
                        "true_fraction_first_last_pp": [round(s[0][2], 2), round(s[-1][2], 2)],
                        "pred_fraction_first_last_pp": [round(s[0][1], 2), round(s[-1][1], 2)]}
    agree = [a["true_direction"] == a["pred_direction"] for a in per_aoi.values()]
    err = [abs(a["pred_change_pp"] - a["true_change_pp"]) for a in per_aoi.values()]
    return {"aois": len(per_aoi), "aoi_months_scored": len(pred_all),
            "direction_agreement": f"{sum(agree)}/{len(agree)}",
            "mean_abs_change_error_pp": round(float(np.mean(err)), 2) if err else None,
            "pearson_r_fraction": round(float(np.corrcoef(pred_all, true_all)[0, 1]), 4) if len(pred_all) > 2 else None,
            "per_aoi": per_aoi}


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(CKPT, map_location=device, weights_only=False)
    model = build_model(ckpt["arch"], ckpt["encoder"]).to(device).eval()
    model.load_state_dict(ckpt["model"])
    report = {"ckpt": str(CKPT), "threshold": ckpt["threshold"], "unchanged_band_pp": UNCHANGED_PP,
              "test": score("test", model, ckpt["threshold"], device),
              "val_used_for_threshold": score("val", model, ckpt["threshold"], device)}
    out = ROOT / "results/eval/builtup_sn7_trend.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "per_aoi"} if isinstance(v, dict) else v
                      for k, v in report.items()}, indent=2))


if __name__ == "__main__":
    main()
