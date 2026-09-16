"""Scene VLM on VRSBench val: VQA accuracy and caption ROUGE-L on a fixed random subset (Q-021)."""
import argparse
import json
import random
import re
import string
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("datasets/raw/vrsbench")
IMAGES = ROOT / "images" / "Images_val"
ARTICLES = {"a", "an", "the"}


def norm(s: str) -> str:
    s = (s or "").lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(w for w in s.split() if w not in ARTICLES)


def vqa_correct(pred: str, gt: str) -> bool:
    p, g = norm(pred), norm(gt)
    return bool(g) and (p == g or re.search(rf"\b{re.escape(g)}\b", p) is not None)


def rouge_l(pred: str, ref: str) -> float:
    a, b = norm(pred).split(), norm(ref).split()
    if not a or not b:
        return 0.0
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a)):
        for j in range(len(b)):
            dp[i + 1][j + 1] = dp[i][j] + 1 if a[i] == b[j] else max(dp[i][j + 1], dp[i + 1][j])
    lcs = dp[-1][-1]
    if lcs == 0:
        return 0.0
    p, r = lcs / len(a), lcs / len(b)
    return 2 * p * r / (p + r)


def sample(path: Path, n: int, seed: int):
    rows = [r for r in json.load(open(path)) if (IMAGES / r["image_id"]).exists()]
    return random.Random(seed).sample(rows, min(n, len(rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", choices=["general_rs_vlm", "scene_vlm"], required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    from PIL import Image
    from backend.app.ml.registry import model_registry

    adapter = model_registry.get_adapter(args.adapter)
    t0 = time.time()
    vqa, caps = [], []
    vqa_errors, caption_errors = 0, 0
    for r in sample(ROOT / "VRSBench_EVAL_vqa.json", args.n, args.seed):
        try:
            img = Image.open(IMAGES / r["image_id"]).convert("RGB")
            pred = adapter.predict({"image_pil": img, "query": r["question"]}).answer or ""
            vqa.append({"image": r["image_id"], "type": r["type"], "question": r["question"], "gt": r["ground_truth"],
                        "pred": pred, "correct": vqa_correct(pred, r["ground_truth"])})
        except Exception as e:
            vqa_errors += 1
            print(f"Warning: VQA sample {r['image_id']} failed: {type(e).__name__}: {e}")
            vqa.append({"image": r["image_id"], "type": r["type"], "question": r["question"], "gt": r["ground_truth"],
                        "pred": "", "error": f"{type(e).__name__}: {e}", "correct": False})
    for r in sample(ROOT / "VRSBench_EVAL_Cap.json", args.n, args.seed):
        try:
            img = Image.open(IMAGES / r["image_id"]).convert("RGB")
            pred = adapter.predict({"image_pil": img, "query": "Describe the image in detail."}).answer or ""
            caps.append({"image": r["image_id"], "gt": r["ground_truth"], "pred": pred, "rouge_l": rouge_l(pred, r["ground_truth"])})
        except Exception as e:
            caption_errors += 1
            print(f"Warning: Caption sample {r['image_id']} failed: {type(e).__name__}: {e}")
            caps.append({"image": r["image_id"], "gt": r["ground_truth"], "pred": "", "error": f"{type(e).__name__}: {e}", "rouge_l": 0.0})
    secs = time.time() - t0
    out = {
        "adapter": args.adapter, "n": args.n, "seed": args.seed, "measured_at": datetime.now(timezone.utc).isoformat(),
        "vqa_accuracy": sum(v["correct"] for v in vqa) / max(len(vqa), 1),
        "caption_rouge_l": sum(c["rouge_l"] for c in caps) / max(len(caps), 1),
        "caption_mean_words": sum(len(c["pred"].split()) for c in caps) / max(len(caps), 1),
        "secs_per_sample": secs / max(len(vqa) + len(caps), 1),
        "vqa_errors": vqa_errors, "caption_errors": caption_errors,
        "vqa": vqa, "captions": caps,
    }
    dest = Path("results/evaluations") / f"scene_vlm_vrsbench_{args.adapter}_{datetime.now():%Y%m%d}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("vqa", "captions")}, indent=1), "->", dest)


if __name__ == "__main__":
    main()
