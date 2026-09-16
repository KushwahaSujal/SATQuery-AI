#!/usr/bin/env python3
"""
SatQuery AI — LocateAnything-3B install, patch and verify.

Fetches nvidia/LocateAnything-3B at a pinned revision into
checkpoints/locate_anything_3b/, applies the transformers-5.x compatibility
patches from third_party/locate_anything/patches/, and verifies every file it
is responsible for by hash. Safe to re-run: files already in the right state
are left alone.

    python scripts/setup_locate_anything.py                 # full install
    python scripts/setup_locate_anything.py --check         # verify only
    python scripts/setup_locate_anything.py --skip-weights  # code + config only
    python scripts/setup_locate_anything.py --check --hash-weights  # also sha256 the 7.7 GB

Exit code 0 when the directory is complete and correctly patched, 1 otherwise.
See third_party/locate_anything/UPSTREAM.md for what the patches change and why.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = PROJECT_ROOT / "third_party" / "locate_anything" / "patches"
DEFAULT_DEST = PROJECT_ROOT / "checkpoints" / "locate_anything_3b"

REPO_ID = "nvidia/LocateAnything-3B"
REVISION = "c32291ca5e996f5a7a485845b4f57a233936bba0"

# git blob hashes: (upstream at REVISION, after our patch)
PATCHED_FILES = {
    "modeling_locateanything.py": (
        "8e61b1d898197e7ad844cb1bfbe56ffff251e4c2",
        "c035c3b21d8d58aa700a0e44a355f7c742fa5821",
    ),
    "modeling_qwen2.py": (
        "e42a31e8620d122ea15dc1c9fef314f77fe05bb0",
        "5a95084c322b9204c6558b5c27db459a49fc97d9",
    ),
}

# Files that must be byte-identical to upstream.
UNPATCHED_FILES = {
    "modeling_vit.py": "cc6b38328207b2232a97478914c72154336f5027",
    "processing_locateanything.py": "2be6905c41354f5363c8272654f268b91d61973f",
}

# (size in bytes, sha256 == Hub LFS etag)
WEIGHT_SHARDS = {
    "model-00001-of-00002.safetensors": (
        4_959_632_160,
        "923cfc10fed19808067da6df85a9a4220ddc1f9eb91ceee94c0fecd05d0f2d58",
    ),
    "model-00002-of-00002.safetensors": (
        2_701_795_216,
        "3459ba101f40594f3f62d3312014f1f8378b4ba3da3b1d562480045938fc7d47",
    ),
}

# Demo media in the Hub repo; not needed for inference.
IGNORE_PATTERNS = ["assets/*"]


def git_blob_hash(path: Path) -> str:
    """Same value as `git hash-object <path>`, without needing git."""
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(dest: Path, skip_weights: bool) -> None:
    from huggingface_hub import snapshot_download

    ignore = list(IGNORE_PATTERNS)
    if skip_weights:
        ignore.append("*.safetensors")
    print(f"[download] {REPO_ID}@{REVISION[:12]} -> {dest}")
    snapshot_download(
        repo_id=REPO_ID,
        revision=REVISION,
        local_dir=str(dest),
        ignore_patterns=ignore,
    )


def apply_patches(dest: Path) -> list[str]:
    """Patches each file that is still at its upstream hash. Returns problems."""
    problems = []
    for name, (upstream, patched) in PATCHED_FILES.items():
        path = dest / name
        if not path.exists():
            problems.append(f"{name}: missing")
            continue
        current = git_blob_hash(path)
        if current == patched:
            print(f"[patch]    {name}: already patched")
            continue
        if current != upstream:
            problems.append(
                f"{name}: unknown content {current[:12]} (neither upstream {upstream[:12]} "
                f"nor patched {patched[:12]}); refusing to patch over local edits"
            )
            continue
        patch = PATCH_DIR / f"{name}.patch"
        result = subprocess.run(
            ["git", "apply", "--unsafe-paths", str(patch)],
            cwd=dest,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            problems.append(f"{name}: git apply failed: {result.stderr.strip()}")
            continue
        print(f"[patch]    {name}: applied")
    return problems


def verify(dest: Path, skip_weights: bool, hash_weights: bool, quiet: bool = False) -> list[str]:
    problems = []
    log = (lambda *a: None) if quiet else print

    for name, (_, patched) in PATCHED_FILES.items():
        path = dest / name
        if not path.exists():
            problems.append(f"{name}: missing")
        elif git_blob_hash(path) != patched:
            problems.append(f"{name}: not patched (blob {git_blob_hash(path)[:12]})")
        else:
            log(f"[verify]   {name}: patched OK")

    for name, expected in UNPATCHED_FILES.items():
        path = dest / name
        if not path.exists():
            problems.append(f"{name}: missing")
        elif git_blob_hash(path) != expected:
            problems.append(f"{name}: differs from upstream (blob {git_blob_hash(path)[:12]})")
        else:
            log(f"[verify]   {name}: upstream OK")

    for name in ("config.json", "preprocessor_config.json", "processor_config.json",
                 "tokenizer_config.json", "model.safetensors.index.json"):
        if not (dest / name).exists():
            problems.append(f"{name}: missing")

    if not skip_weights:
        for name, (size, sha) in WEIGHT_SHARDS.items():
            path = dest / name
            if not path.exists():
                problems.append(f"{name}: missing")
                continue
            if path.stat().st_size != size:
                problems.append(f"{name}: {path.stat().st_size} bytes, expected {size}")
                continue
            if hash_weights:
                log(f"[verify]   {name}: hashing {size / 1e9:.1f} GB ...")
                if sha256_file(path) != sha:
                    problems.append(f"{name}: sha256 mismatch")
                    continue
                log(f"[verify]   {name}: sha256 OK")
            else:
                log(f"[verify]   {name}: size OK (use --hash-weights for sha256)")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--check", action="store_true", help="verify only; never download or modify")
    ap.add_argument("--skip-weights", action="store_true", help="ignore the two .safetensors shards")
    ap.add_argument("--hash-weights", action="store_true", help="sha256 the shards (~20 s)")
    args = ap.parse_args()
    dest = args.dest.resolve()

    if args.check and not dest.exists():
        print(f"{dest} does not exist. Run without --check to install.")
        return 1

    # A complete install is left untouched: snapshot_download restores upstream
    # content over locally patched files, so only fetch when something is wrong.
    problems: list[str] = []
    if not args.check and (not dest.exists() or verify(dest, args.skip_weights, hash_weights=False, quiet=True)):
        dest.mkdir(parents=True, exist_ok=True)
        download(dest, args.skip_weights)
        problems += apply_patches(dest)

    problems += verify(dest, args.skip_weights, args.hash_weights)

    print()
    if problems:
        print("PROBLEMS:")
        for p in dict.fromkeys(problems):
            print(f"  - {p}")
        return 1
    print(f"LocateAnything-3B ready at {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
