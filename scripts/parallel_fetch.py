"""Resume one large Hugging Face file over N parallel HTTP range requests, then verify its SHA-256.

For when a single stream is slow (hf download without Xet fetches each file over one connection).
The existing partial file is kept: only the missing tail is fetched, split into N parts that are
appended in order. Memory use stays at about N × 1 MB.

    .venv/bin/python scripts/parallel_fetch.py --repo jaychempan/LAE-1M --path LAE-FOD/FAIR1M/images.zip \
        --partial <existing .incomplete> --dest datasets/raw/lae_1m/LAE-FOD/FAIR1M/images.zip --workers 8
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from huggingface_hub import HfApi, get_token

CHUNK = 1 << 20


def fetch_range(url: str, headers: dict, start: int, end: int, part: Path, progress: list, idx: int) -> None:
    """Download bytes [start, end] into part, resuming from part's current size."""
    for attempt in range(20):
        have = part.stat().st_size if part.exists() else 0
        if start + have > end:
            return
        h = dict(headers, Range=f"bytes={start + have}-{end}")
        try:
            with requests.get(url, headers=h, stream=True, timeout=60) as r:
                r.raise_for_status()
                if r.status_code != 206:
                    raise RuntimeError(f"server ignored Range (status {r.status_code})")
                with part.open("ab") as f:
                    for chunk in r.iter_content(CHUNK):
                        f.write(chunk)
                        progress[idx] += len(chunk)
            if part.stat().st_size >= end - start + 1:
                return
        except Exception as exc:  # retry with backoff; network hiccups are expected over hours
            print(f"part {idx}: {exc!r}; retry {attempt + 1}", flush=True)
            time.sleep(min(60, 2 ** attempt))
    raise RuntimeError(f"part {idx} failed after retries")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--path", required=True)
    ap.add_argument("--partial", required=True, type=Path)
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    meta = next(s for s in HfApi().dataset_info(args.repo, files_metadata=True).siblings if s.rfilename == args.path)
    size, sha = meta.size, meta.lfs.sha256
    url = f"https://huggingface.co/datasets/{args.repo}/resolve/main/{args.path}"
    headers = {"Authorization": f"Bearer {get_token()}"} if get_token() else {}

    base = args.partial.stat().st_size
    print(f"size {size}  have {base}  missing {size - base}  workers {args.workers}", flush=True)
    step = -(-(size - base) // args.workers)
    ranges = [(base + i * step, min(base + (i + 1) * step, size) - 1) for i in range(args.workers)]
    ranges = [r for r in ranges if r[0] <= r[1]]
    parts = [args.partial.with_name(args.partial.name + f".part{i}") for i in range(len(ranges))]
    progress = [p.stat().st_size if p.exists() else 0 for p in parts]
    start_total, t0 = sum(progress), time.time()

    stop = threading.Event()

    def report():
        while not stop.wait(30):
            done = sum(progress)
            rate = (done - start_total) / max(time.time() - t0, 1)
            left = (size - base - done) / rate if rate else float("inf")
            print(f"{(base + done) / 1e9:.2f}/{size / 1e9:.2f} GB  {rate / 1e6:.2f} MB/s  eta {left / 60:.0f} min",
                  flush=True)

    threading.Thread(target=report, daemon=True).start()
    with ThreadPoolExecutor(len(ranges)) as ex:
        for f in [ex.submit(fetch_range, url, headers, s, e, p, progress, i)
                  for i, ((s, e), p) in enumerate(zip(ranges, parts))]:
            f.result()
    stop.set()

    print("assembling", flush=True)
    with args.partial.open("ab") as out:
        for p in parts:
            with p.open("rb") as src:
                shutil.copyfileobj(src, out, 16 * CHUNK)
    for p in parts:
        p.unlink()
    if args.partial.stat().st_size != size:
        sys.exit(f"size mismatch: {args.partial.stat().st_size} != {size}")
    print("verifying sha256", flush=True)
    h = hashlib.sha256()
    with args.partial.open("rb") as f:
        while b := f.read(16 * CHUNK):
            h.update(b)
    if h.hexdigest() != sha:
        sys.exit(f"sha256 mismatch: {h.hexdigest()} != {sha}")
    args.dest.parent.mkdir(parents=True, exist_ok=True)
    args.partial.rename(args.dest)
    print(f"ok: {args.dest}", flush=True)


if __name__ == "__main__":
    main()
