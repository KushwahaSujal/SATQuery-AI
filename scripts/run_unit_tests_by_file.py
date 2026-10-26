#!/usr/bin/env python3
"""CPU unit suite, one test file per process, with progress the dashboard can show (scripts/watch_training.py).

Why not one `pytest tests/unit`: that process peaked at 4.7 GB and was killed (2026-10-26, project/qna.md Q-084);
memory builds up across files. Here each file is its own pytest process, run one after another, and the next
file waits while MemAvailable is below MIN_FREE_MB. Per file: return code, pass/fail counts and peak RSS (from
wait4), written to results/eval/unit_tests_<date>.json. Files in AB_FILES are also re-run with the referring-
grounding path switched off, to measure whether that path changes their memory.

    .venv/bin/python scripts/run_unit_tests_by_file.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"test_geotiff_georeferencing.py"}  # 3 pre-existing GDAL failures, recorded since Q-0xx (memory.md §0)
AB_FILES = {"test_aoi_http.py"}
MIN_FREE_MB = 4096


def mem_available_mb() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return 0


def run_file(path: Path, extra_env: dict | None = None) -> dict:
    while mem_available_mb() < MIN_FREE_MB:
        print(f"waiting: MemAvailable {mem_available_mb()} MB < {MIN_FREE_MB} MB", flush=True)
        time.sleep(15)
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": str(ROOT), **(extra_env or {})}
    t0 = time.time()
    proc = subprocess.Popen([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "not models",
                             str(path)], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = proc.stdout.read()
    _, status, usage = os.wait4(proc.pid, 0)  # reap it ourselves: wait4 returns this child's own peak RSS
    proc.returncode = rc = os.waitstatus_to_exitcode(status)
    peak_mb = round(usage.ru_maxrss / 1024)  # kB -> MB
    summary = next((l for l in reversed(out.splitlines()) if re.search(r"\d+ (passed|failed|error)", l)), "")
    counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|errors?|skipped|deselected)", summary)}
    failed = [l for l in out.splitlines() if l.startswith(("FAILED", "ERROR"))]
    return {"file": path.name, "rc": rc, "counts": counts, "summary": summary.strip("= "), "failed": failed[:20],
            "seconds": round(time.time() - t0, 1), "peak_rss_mb": peak_mb,
            "killed": rc is not None and rc < 0}


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / f"results/eval/unit_tests_{time.strftime('%Y-%m-%d')}.json"
    files = sorted(p for p in (ROOT / "tests/unit").glob("test_*.py") if p.name not in SKIP)
    n = len(files) + len(AB_FILES)
    print("tiles:", json.dumps({"unit_tests": {"train": 0, "val": 0, "test": len(files)}}), flush=True)
    print("plan:", json.dumps({"epochs": 0, "train_steps": 0, "eval": {"unit_tests": n}, "baseline": ["unit_tests"],
                               "per_epoch": [], "final": []}), flush=True)
    results, t0 = [], time.time()
    jobs = [(f, None) for f in files] + [(ROOT / "tests/unit" / f, {"SATQUERY_REFERRING_GROUNDING_ENABLED": "false"})
                                        for f in sorted(AB_FILES)]
    for i, (f, env) in enumerate(jobs, 1):
        r = run_file(f, env)
        r["variant"] = "referring_off" if env else "default"
        results.append(r)
        print(f"file {i}/{n}: {f.name}{' [referring off]' if env else ''} rc={r['rc']} {r['summary']} "
              f"({r['seconds']}s, peak {r['peak_rss_mb']} MB)", flush=True)
        el = time.time() - t0
        print(f"eval tag=unit_tests step={i}/{n} elapsed={el:.1f}s rate={i / el:.3f}it/s", flush=True)
    bad = [r for r in results if r["rc"] not in (0, 5)]  # 5 = no tests collected
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"files": len(files), "passed": sum(r["counts"].get("passed", 0) for r in results),
                               "failed_files": [r["file"] for r in bad], "results": results}, indent=1))
    print(f"done: {len(jobs)} runs, {len(bad)} with failures: {[r['file'] for r in bad]}", flush=True)


if __name__ == "__main__":
    main()
