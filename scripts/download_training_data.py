"""Fetch the training datasets listed in datasets/manifests/training_sources.yaml.

Resumable: a dataset whose datasets/raw/<name>/.complete marker exists is skipped, and
`hf download` itself resumes partial files. Archives are extracted in place and then deleted.

    .venv/bin/python scripts/download_training_data.py            # everything
    .venv/bin/python scripts/download_training_data.py --only loveda whu_building
    .venv/bin/python scripts/download_training_data.py --list
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "datasets/manifests/training_sources.yaml"
RAW = ROOT / "datasets/raw"
BIN = Path(sys.executable).parent


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def extract_archives(dest: Path) -> None:
    # Repeat until no archive is left: some archives contain archives.
    while True:
        archives = [p for p in dest.rglob("*") if p.is_file() and (
            p.suffix == ".zip" or p.name.endswith((".tar.gz", ".tgz", ".tar")))]
        if not archives:
            return
        for arc in archives:
            log(f"  extracting {arc.relative_to(RAW)}")
            if arc.suffix == ".zip":
                with zipfile.ZipFile(arc) as zf:
                    zf.extractall(arc.parent)
            else:
                with tarfile.open(arc) as tf:
                    tf.extractall(arc.parent, filter="data")
            arc.unlink()


def fetch(entry: dict) -> None:
    dest = RAW / entry["name"]
    marker = dest / ".complete"
    if marker.exists():
        log(f"skip {entry['name']} (complete)")
        return
    if entry["source"] == "manual":
        log(f"skip {entry['name']} (manual: place the files in {dest} and create .complete)")
        return
    if entry.get("hold"):
        log(f"skip {entry['name']} (on hold in the manifest)")
        return
    dest.mkdir(parents=True, exist_ok=True)
    log(f"fetch {entry['name']} ← {entry['source']}:{entry['ref']} (~{entry['approx_gb']} GB)")
    if entry["source"] == "hf":
        cmd = [str(BIN / "hf"), "download", entry["ref"], "--repo-type", "dataset",
               "--local-dir", str(dest), "--max-workers", "8"]
    elif entry["source"] == "kaggle":
        cmd = [str(BIN / "kaggle"), "datasets", "download", "-d", entry["ref"], "-p", str(dest)]
    elif entry["source"] == "s3":
        for prefix in entry["sync"]:
            subprocess.run([str(BIN / "aws"), "s3", "sync", "--no-sign-request", "--only-show-errors",
                            entry["ref"] + prefix, str(dest / prefix)], check=True)
        cmd = None
    elif entry["source"] == "url":
        for f in entry["files"]:
            out = dest / f["name"]
            subprocess.run(["curl", "-L", "--fail", "--retry", "10", "-C", "-", "-sS", "-o", str(out), f["url"]],
                           check=True)
            algo, want = f["checksum"].split(":")
            h = hashlib.new(algo)
            with out.open("rb") as fh:
                while b := fh.read(1 << 24):
                    h.update(b)
            if h.hexdigest() != want:
                out.unlink()
                raise RuntimeError(f"{f['name']}: {algo} mismatch ({h.hexdigest()} != {want}); deleted, re-run")
            log(f"  {f['name']} {algo} ok")
        cmd = None
    else:
        raise ValueError(f"unknown source {entry['source']}")
    if cmd:
        subprocess.run(cmd, check=True)
    extract_archives(dest)
    shutil.rmtree(dest / ".cache", ignore_errors=True)
    want = entry.get("expect_files")
    if want:  # guards against a half-finished mirror being marked complete
        have = sum(1 for p in dest.rglob("*") if p.is_file() and not p.name.startswith("."))
        if have < want:
            raise RuntimeError(f"{entry['name']}: {have} files on disk, expected {want}; not marking complete")
        log(f"  file count ok: {have} >= {want}")
    marker.write_text(
        f"source: {entry['source']}:{entry['ref']}\nfetched: {dt.datetime.now().isoformat()}\n")
    size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file()) / 1e9
    log(f"done  {entry['name']} — {size:.2f} GB on disk")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="dataset names to fetch")
    ap.add_argument("--source", nargs="*", choices=["hf", "kaggle", "s3", "url"],
                    help="only these sources (run one process per source to download in parallel)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    entries = yaml.safe_load(MANIFEST.read_text())["datasets"]
    if args.list:
        for e in entries:
            done = (RAW / e["name"] / ".complete").exists()
            flag = "manual" if e["source"] == "manual" else ("hold" if e.get("hold") else "")
            print(f"{'✓' if done else ' '} {e['name']:24s} {e['approx_gb']:6.1f} GB  {e['task']:24s} {flag}")
        return 0
    if args.only:
        unknown = set(args.only) - {e["name"] for e in entries}
        if unknown:
            sys.exit(f"unknown dataset(s): {sorted(unknown)}")
        entries = [e for e in entries if e["name"] in args.only]
    if args.source:
        entries = [e for e in entries if e["source"] in args.source]

    failed = []
    for e in entries:
        try:
            fetch(e)
        except Exception as exc:  # keep going; report at the end
            log(f"FAIL  {e['name']}: {exc}")
            failed.append(e["name"])
    log(f"finished; failed: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
