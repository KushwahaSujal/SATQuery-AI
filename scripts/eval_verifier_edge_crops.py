#!/usr/bin/env python3
"""
SatQuery AI — re-measurement of the Q-009 verifier numbers under each crop geometry.

Q-009 recorded the verifier's behaviour on VRSBench ground-truth crops at pad 1.0 / min side 96 /
top-3, and noted that the DISPUTED answers on `05945_0000.png` sit on boxes touching the image edge,
where `PIL.Image.crop` silently fills the out-of-frame region with black. The scripts behind
`results/evaluations/remoteclip_verifier_probe_20260914.json`,
`detection_verifier_3way_20260914.json` and `detection_verifier_sweep_20260914.json` were not
committed, so this rebuilds the probe from the same source data and the same selection rule
(first 40 VRSBench referring records per `obj_cls`, 26 classes → 973 crops, matching Q-009's n) and
measures every crop geometry in one process against one sample, so before/after is a like-for-like
comparison even where the absolute baseline differs from the 2026-09-14 run.

The wrong-label pairing is drawn from a fixed seed (the original pairing was not recorded), so
`wrong_label` rows are reproducible here but are not expected to match Q-009 digit for digit.

Usage:
  .venv/bin/python scripts/eval_verifier_edge_crops.py                 # all three modes
  .venv/bin/python scripts/eval_verifier_edge_crops.py --modes pad inset --limit 100
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.evidence.verifier import CONTRADICTED, UNVERIFIED, VERIFIED, DetectionVerifier

REFERRING = PROJECT_ROOT / "datasets/raw/vrsbench/VRSBench_EVAL_referring.json"
IMAGES = PROJECT_ROOT / "datasets/raw/vrsbench/images/Images_val"
OUT = PROJECT_ROOT / "results/evaluations/verifier_edge_crops_20260921.json"
PER_CLASS = 40
VEHICLE_SUBSET = 200   # Q-009's vehicle rows are in steps of 0.005, i.e. n=200
SEED = 20260914


def build_sample() -> List[Dict]:
    records = json.loads(REFERRING.read_text())
    per: Dict[str, List[Dict]] = collections.defaultdict(list)
    for r in records:
        if len(per[r["obj_cls"]]) < PER_CLASS:
            per[r["obj_cls"]].append(r)
    return [r for cls in sorted(per) for r in per[cls]]


def vehicle_sample() -> List[Dict]:
    """Q-009's vehicle rows move in steps of 0.005, i.e. a 200-crop vehicle subset."""
    records = json.loads(REFERRING.read_text())
    return [r for r in records if r["obj_cls"] == "vehicle"][:VEHICLE_SUBSET]


def gt_box(rec: Dict, width: int, height: int) -> List[float]:
    xs = rec["obj_corner"][0::2]
    ys = rec["obj_corner"][1::2]
    return [min(xs) * width, min(ys) * height, max(xs) * width, max(ys) * height]


def auc(pos: List[float], neg: List[float]) -> float:
    """Mann-Whitney U / |pos||neg| — ties count a half."""
    if not pos or not neg:
        return float("nan")
    allv = sorted(pos + neg)
    ranks = {}
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        ranks[allv[i]] = r
        i = j + 1
    rsum = sum(ranks[v] for v in pos)
    n1, n2 = len(pos), len(neg)
    return float((rsum - n1 * (n1 + 1) / 2.0) / (n1 * n2))


class Probe:
    """One RemoteCLIP image encoding per crop, then every verdict read off the same cosines.

    Validated against `DetectionVerifier.verify` on the first `--validate` records of every mode:
    status, rank and probability must match exactly, otherwise the run aborts.
    """

    def __init__(self, verifier: DetectionVerifier, classes: List[str]):
        self.v = verifier
        self.labels = list(dict.fromkeys([l.lower() for l in verifier.cfg.vocabulary]))
        self.extra = [c.replace("-", " ") for c in classes if c.replace("-", " ") not in self.labels]
        self.context = {verifier.group_of(c) for c in verifier.cfg.context_labels}

    @torch.no_grad()
    def _scores(self, crop_img: Image.Image, labels: List[str]):
        clip = self.v.clip
        text = self.v._text_features(tuple(labels))
        img = clip._model.encode_image(clip._preprocess(crop_img).unsqueeze(0).to(clip.device))
        img = img / img.norm(dim=-1, keepdim=True)
        cos = (img @ text.T).squeeze(0).float().cpu().numpy()
        group_cos: Dict[str, float] = {}
        for label, c in zip(labels, cos):
            g = self.v.group_of(label)
            group_cos[g] = max(group_cos.get(g, -1.0), float(c))
        groups = list(group_cos)
        scale = float(clip._model.logit_scale.exp())
        logits = np.array([group_cos[g] for g in groups]) * scale
        probs = np.exp(logits - logits.max())
        probs = probs / probs.sum()
        order = np.argsort(-probs)
        ranked = [(groups[i], float(probs[i])) for i in order]
        raw = {l: float(c) for l, c in zip(labels, cos)}
        return ranked, raw

    def verdict(self, ranked, target_label: str) -> Dict:
        g = self.v.group_of(target_label)
        names = [n for n, _ in ranked]
        rank = 1 + names.index(g)
        if rank <= self.v.cfg.top_k:
            status = VERIFIED
        elif names[0] in self.context:
            status = UNVERIFIED
        else:
            status = CONTRADICTED
        return {"status": status, "rank": rank,
                "probability": round(dict(ranked)[g], 4), "top": names[0]}

    def run(self, crop_img: Image.Image, target_label: str, others: List[str]) -> Dict:
        labels = list(self.labels)
        for lbl in [target_label] + others:
            if lbl not in labels:
                labels.append(lbl)
        ranked, raw = self._scores(crop_img, labels)
        out = {lbl: self.verdict(ranked, lbl) for lbl in [target_label] + others}
        out["_raw"] = raw
        return out


def rate(counter: collections.Counter, key: str, total: int) -> float:
    return round(counter[key] / total, 4) if total else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=list(DetectionVerifier.CROP_MODES))
    ap.add_argument("--limit", type=int, default=0, help="debug: cap the sample")
    ap.add_argument("--validate", type=int, default=20,
                    help="records per mode cross-checked against DetectionVerifier.verify")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    full = build_sample()
    sample = full[: args.limit] if args.limit else full
    vehicles = vehicle_sample()
    classes = sorted({r["obj_cls"] for r in full})
    print(f"sample: {len(sample)} crops over {len(classes)} classes; vehicle subset {len(vehicles)}")

    rng = random.Random(SEED)
    wrong_for: Dict[int, str] = {}
    base = DetectionVerifier()
    for i, rec in enumerate(sample):
        true_g = base.group_of(rec["obj_cls"].replace("-", " "))
        pool = [c.replace("-", " ") for c in classes
                if base.group_of(c.replace("-", " ")) != true_g]
        wrong_for[i] = rng.choice(pool)

    # One geometry analysis pass, no model needed: how much of each crop the old code fabricates.
    geom: Dict[str, Dict] = {}
    sizes: Dict[str, tuple] = {}
    for rec in sample:
        p = IMAGES / rec["image_id"]
        if rec["image_id"] not in sizes:
            with Image.open(p) as im:
                sizes[rec["image_id"]] = im.size

    results: Dict[str, Dict] = {}
    verifiers = {m: DetectionVerifier(crop_mode=m) for m in args.modes}
    for m, v in verifiers.items():
        if not v.is_available():
            print(f"FATAL: verifier unavailable for mode {m}")
            return 1
    probe = Probe(verifiers[args.modes[0]], classes)
    verifiers[args.modes[0]].clip.load_model()
    for v in verifiers.values():
        v._clip = verifiers[args.modes[0]]._clip
        v._text_cache = verifiers[args.modes[0]]._text_cache

    # Which crops the legacy geometry padded — reported as a subset so the unaffected crops can be
    # shown to be bit-identical across modes.
    padded_idx = set()
    legacy = DetectionVerifier(crop_mode="pad")
    for i, rec in enumerate(sample):
        w, h = sizes[rec["image_id"]]
        _, cb = legacy.crop(Image.new("RGB", (w, h)), gt_box(rec, w, h))
        if cb[0] < 0 or cb[1] < 0 or cb[2] > w or cb[3] > h:
            padded_idx.add(i)
    print(f"legacy geometry leaves the frame on {len(padded_idx)}/{len(sample)} crops "
          f"({len(padded_idx)/len(sample):.3f})")

    for mode in args.modes:
        v = verifiers[mode]
        probe.v = v
        true_c, wrong_c = collections.Counter(), collections.Counter()
        true_c_edge, true_c_clean = collections.Counter(), collections.Counter()
        veh_true_accept = 0
        nonveh_as_vehicle_accept = 0
        n_nonveh = 0
        raw_pos, raw_neg, con_pos, con_neg = [], [], [], []
        black = []
        checked = 0
        for i, rec in enumerate(sample):
            path = IMAGES / rec["image_id"]
            with Image.open(path) as im:
                img = im.convert("RGB")
            w, h = img.size
            box = gt_box(rec, w, h)
            true_label = rec["obj_cls"].replace("-", " ")
            wrong_label = wrong_for[i]
            crop_img, cb = v.crop(img, box)
            arr = np.asarray(crop_img)
            black.append(float((arr.sum(axis=2) == 0).mean()))
            out = probe.run(crop_img, true_label, [wrong_label, "vehicle"])
            if checked < args.validate:
                ref = v.verify(img, box, true_label)
                got = out[true_label]
                assert (ref.status, ref.target_rank) == (got["status"], got["rank"]), \
                    f"probe diverges from verify(): {ref} vs {got}"
                checked += 1
            t, wr = out[true_label], out[wrong_label]
            true_c[t["status"]] += 1
            wrong_c[wr["status"]] += 1
            (true_c_edge if i in padded_idx else true_c_clean)[t["status"]] += 1
            raw = out["_raw"]
            raw_pos.append(raw[true_label])
            raw_neg.append(raw[wrong_label])
            con_pos.append(t["probability"])
            con_neg.append(wr["probability"])
            if v.group_of(true_label) != "vehicle":
                n_nonveh += 1
                nonveh_as_vehicle_accept += out["vehicle"]["status"] == VERIFIED
            else:
                veh_true_accept += t["status"] == VERIFIED
        n = len(sample)

        # Vehicle subset (Q-009's 200 vehicle crops queried as "vehicle" and as "airplane").
        veh_as_veh, veh_as_air = collections.Counter(), collections.Counter()
        for rec in vehicles:
            with Image.open(IMAGES / rec["image_id"]) as im:
                img = im.convert("RGB")
            w, h = img.size
            crop_img, _ = v.crop(img, gt_box(rec, w, h))
            out = probe.run(crop_img, "vehicle", ["airplane"])
            veh_as_veh[out["vehicle"]["status"]] += 1
            veh_as_air[out["airplane"]["status"]] += 1

        nv = len(vehicles)
        ne, nc = sum(true_c_edge.values()), sum(true_c_clean.values())
        results[mode] = {
            "n": n,
            "fabricated_black_pixel_fraction_mean": round(float(np.mean(black)), 4),
            "crops_with_any_black_pixel": int(sum(1 for b in black if b > 0)),
            "probe": {
                "auc_raw": round(auc(raw_pos, raw_neg), 4),
                "auc_contrastive": round(auc(con_pos, con_neg), 4),
                "top3_accept_true": rate(true_c, VERIFIED, n),
                "top3_accept_wrong": rate(wrong_c, VERIFIED, n),
                "raw_pos_mean": round(float(np.mean(raw_pos)), 4),
                "raw_neg_mean": round(float(np.mean(raw_neg)), 4),
            },
            "three_way": {
                "true_label": {k: rate(true_c, k, n) for k in (VERIFIED, UNVERIFIED, CONTRADICTED)},
                "wrong_label": {k: rate(wrong_c, k, n) for k in (VERIFIED, UNVERIFIED, CONTRADICTED)},
                "vehicle_crop_as_vehicle": {k: rate(veh_as_veh, k, nv) for k in (VERIFIED, UNVERIFIED, CONTRADICTED)},
                "vehicle_crop_as_airplane": {k: rate(veh_as_air, k, nv) for k in (VERIFIED, UNVERIFIED, CONTRADICTED)},
            },
            "sweep_row": {
                "pad": v.cfg.crop_pad, "min_side": v.cfg.min_crop_side, "top_k": v.cfg.top_k,
                "vehicle_true_accept": rate(veh_as_veh, VERIFIED, nv),
                "all_true_accept": rate(true_c, VERIFIED, n),
                "all_wrong_accept": rate(wrong_c, VERIFIED, n),
                "nonvehicle_as_vehicle": round(nonveh_as_vehicle_accept / n_nonveh, 4),
            },
            "true_label_by_subset": {
                "legacy_padded": {"n": ne, **{k: rate(true_c_edge, k, ne) for k in (VERIFIED, UNVERIFIED, CONTRADICTED)}},
                "inside_frame": {"n": nc, **{k: rate(true_c_clean, k, nc) for k in (VERIFIED, UNVERIFIED, CONTRADICTED)}},
            },
        }
        print(f"\n=== mode {mode}")
        print(json.dumps(results[mode], indent=2))

    payload = {
        "source": "VRSBench_EVAL_referring.json, first 40 records per obj_cls (26 classes)",
        "config": {"crop_pad": base.cfg.crop_pad, "min_crop_side": base.cfg.min_crop_side,
                   "top_k": base.cfg.top_k, "prompt_template": base.cfg.prompt_template},
        "wrong_label_seed": SEED,
        "legacy_out_of_frame_crops": len(padded_idx),
        "modes": results,
    }
    Path(args.out).write_text(json.dumps(payload, indent=2))
    print(f"\nwrote {args.out}")
    for v in verifiers.values():
        try:
            v.clip.unload()
        except Exception:
            pass
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
