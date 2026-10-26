"""Live terminal dashboard for SatQuery training runs and dataset downloads (read-only).

Everything shown is derived from files on disk, so the window can be closed and reopened at any
time without losing track:
  - training: the newest results/training/*.log written by training/segmentation/train_seg.py
    (per-step "progress ..." lines; runs started before those existed fall back to estimating the
    current epoch from the previous epoch's duration), plus the run's report.json when it ends;
  - downloads: datasets/manifests/training_sources.yaml, the .complete markers, and the last
    progress bar in each datasets/raw/_download_*.log;
  - system: /proc/meminfo, /proc/net/dev, nvidia-smi, disk usage, mem_guard.log.

    .venv/bin/python scripts/watch_training.py              # newest training log
    .venv/bin/python scripts/watch_training.py --log results/training/roads_dg_ma.log
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets/raw"
TRAIN_LOGS = ROOT / "results/training"
W = 92  # inner width; reduced per frame to fit the terminal
STALL_S = 120  # seconds without a new log line before the clocks stop interpolating
_SHOWN: dict[str, tuple[float, float]] = {}  # clock key -> (value shown, wall time shown)


def steady_eta(key: str, target: float | None) -> float | None:
    """ETA as a countdown that never ticks upward on estimate noise.

    Each progress line re-estimates the ETA from the measured rate, which wobbles by seconds; shown raw,
    the clock would tick 2:06:10 -> 2:06:09 -> 2:06:12. Instead the shown value counts down 1 s per second.
    A lower estimate pulls it down faster; a slightly higher one slows the countdown to half speed until
    they agree; only a real slowdown (more than max(30 s, 1 %) above the countdown) moves it up.
    """
    now = time.time()
    if target is None:
        _SHOWN.pop(key, None)
        return None
    prev = _SHOWN.get(key)
    if prev is None:
        shown = target
    else:
        dt = now - prev[1]
        countdown = max(prev[0] - dt, 0.0)
        if target > countdown + max(30.0, 0.01 * target):
            shown = target
        elif target >= countdown:
            shown = countdown + min(0.05 * (target - countdown), 0.5 * dt)
        else:
            shown = countdown + 0.2 * (target - countdown)
    _SHOWN[key] = (shown, now)
    return shown


def steady_elapsed(key: str, value: float) -> float:
    """Elapsed clocks never step backwards when a log line replaces the interpolated value."""
    prev = _SHOWN.get(key)
    shown = max(value, prev[0]) if prev and value >= prev[0] - 60 else value  # a restart may reset it
    _SHOWN[key] = (shown, time.time())
    return shown
HISTORY_N = 12  # epoch rows shown; reduced per frame to fit the terminal height
COMPACT_DONE = False  # collapse finished downloads into one line when the terminal is short

C = {"cyan": "36", "dcyan": "2;36", "green": "32", "dgreen": "2;32", "blue": "34", "yellow": "33",
     "magenta": "35", "red": "31", "grey": "2;37", "white": "37", "bold": "1"}

EPOCH_RE = re.compile(r'^\{"epoch": (\d+)')
PROGRESS_RE = re.compile(r"progress epoch=(\d+)/(\d+) step=(\d+)/(\d+) elapsed=([\d.]+)s rate=([\d.]+)it/s")
EVAL_RE = re.compile(r"eval tag=(\w+) step=(\d+)/(\d+) elapsed=([\d.]+)s rate=([\d.]+)it/s")
TQDM_RE = re.compile(r"(\d+)%\|[^|]*\|\s*([^\[]+?)\s*\[([^<\]]+)<([^,\]]+),\s*([^\]]+)\]")


def paint(text: str, color: str) -> str:
    return f"\033[{C[color]}m{text}\033[0m"


def row(text: str, color: str = "white") -> str:
    text = text[:W].ljust(W)
    return paint("║", "dcyan") + paint(text, color) + paint("║", "dcyan")


def rule(kind: str = "mid") -> str:
    left, right = {"top": ("╔", "╗"), "mid": ("╠", "╣"), "bot": ("╚", "╝")}[kind]
    return paint(left + "═" * W + right, "dcyan")


def bar(frac: float, width: int) -> str:
    frac = min(max(frac, 0.0), 1.0)
    n = int(frac * width)
    return "█" * n + "░" * (width - n)


def dur(sec: float | None) -> str:
    if sec is None or sec < 0 or sec != sec:
        return "--"
    sec = int(sec)
    return f"{sec // 3600}h {sec // 60 % 60:02d}m {sec % 60:02d}s"


def human(nbytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024 or unit == "TB":
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return ""


# ---------------------------------------------------------------- training
def newest_train_log() -> Path | None:
    logs = [p for p in TRAIN_LOGS.glob("*.log")
            if p.name not in ("sysmon.log", "mem_guard.log") and "tiles:" in p.read_text(errors="ignore")[:4000]]
    return max(logs, key=lambda p: p.stat().st_mtime) if logs else None


def _stages(plan: dict) -> list[dict]:
    """A run's whole workload in order, from its "plan:" line: baseline evals, then per epoch the
    training steps and its evals, then the final evals."""
    ev = plan["eval"]
    first = "before training: " if plan["epochs"] else ""  # evaluation-only runs have no "baseline"
    out = [{"kind": "eval", "tag": t, "label": first + t.replace("_", " "), "n": ev[t]} for t in plan.get("baseline", [])]
    for e in range(1, plan["epochs"] + 1):
        out.append({"kind": "train", "tag": f"epoch {e}", "label": f"train epoch {e}/{plan['epochs']}",
                    "n": plan["train_steps"]})
        out += [{"kind": "eval", "tag": t, "label": f"epoch {e} {t}", "n": ev[t]} for t in plan.get("per_epoch", [])]
    out += [{"kind": "eval", "tag": t, "label": f"final {t}", "n": ev[t]} for t in plan.get("final", [])]
    for s in out:
        s.update(done=0, elapsed=0.0)
    return out


def _advance(st: dict, key: tuple[str, str], step: int, n: int, elapsed: float, rate: float) -> None:
    """Attribute a progress line to the first unfinished stage of that kind/tag at or after the pointer."""
    stages, i = st["plan"], st["stage"]
    while i < len(stages) and (stages[i]["kind"], stages[i]["tag"]) != key:
        i += 1
    if i == len(stages):
        return
    stages[i].update(done=step, n=n, elapsed=elapsed)
    st["rate"][key[0]] = rate
    st["rate"][_family(key)] = rate
    st["stage"] = i + 1 if step >= n else i


def _known_rates() -> dict[str, float]:
    """family -> the latest rate logged by any run in results/training (oldest log first, so newest wins)."""
    out: dict[str, float] = {}
    for log in sorted(TRAIN_LOGS.glob("*.log"), key=lambda p: p.stat().st_mtime):
        text = log.read_text(errors="ignore")
        for m in EVAL_RE.finditer(text):
            out[_family(("eval", m[1]))] = float(m[5])
    return out


def _family(key: tuple[str, str]) -> str:
    """Rate bucket: evaluation tags like det_ft_present / pipe_base_absent share a speed per prefix."""
    return f"{key[0]}:{key[1].split('_')[0]}"


def plan_eta(st: dict) -> tuple[dict | None, float | None, float, float | None]:
    """(current stage, its ETA, total elapsed, total ETA) from the plan and the measured rates."""
    stages, rate = st["plan"], st["rate"]
    cur = stages[st["stage"]] if st["stage"] < len(stages) else None
    left = 0.0
    for s in stages[st["stage"]:]:
        r = (rate.get(_family((s["kind"], s["tag"]))) or rate.get(s["kind"])
             or rate.get("eval" if s["kind"] == "train" else "train"))
        if not r:
            return cur, None, sum(x["elapsed"] for x in stages), None
        left += (s["n"] - s["done"]) / r
    r_cur = (rate.get(_family((cur["kind"], cur["tag"]))) or rate.get(cur["kind"])) if cur else None
    cur_eta = (cur["n"] - cur["done"]) / r_cur if cur and r_cur else None
    return cur, cur_eta, sum(x["elapsed"] for x in stages), left


def parse_train(log: Path) -> dict:
    text = log.read_text(errors="ignore").replace("\x00", "")
    st = {"log": log, "epochs": [], "progress": None, "phase": "train", "tiles": None,
          "total_epochs": None, "report": None, "failed": None, "plan": None, "stage": 0, "rate": {}}
    for line in text.splitlines():
        if line.startswith("tiles:"):
            st["tiles"] = json.loads(line[len("tiles:"):])
        elif line.startswith("plan:"):  # a (re)started run that declares its whole workload
            st["plan"] = _stages(json.loads(line[len("plan:"):]))
            st["stage"], st["epochs"] = 0, []
        elif st.get("plan") and (m := EVAL_RE.search(line)):
            _advance(st, ("eval", m[1]), int(m[2]), int(m[3]), float(m[4]), float(m[5]))
        elif EPOCH_RE.match(line):
            st["epochs"].append(json.loads(line))
            st["progress"], st["phase"] = None, "train"
        elif m := PROGRESS_RE.search(line):  # YOLO's tqdm bar can precede it on the same line
            if st.get("plan"):
                _advance(st, ("train", f"epoch {m[1]}"), int(m[3]), int(m[4]), float(m[5]), float(m[6]))
            st["progress"] = dict(epoch=int(m[1]), total=int(m[2]), step=int(m[3]), steps=int(m[4]),
                                  elapsed=float(m[5]), rate=float(m[6]))
            st["total_epochs"] = int(m[2])
        elif m := re.search(r"phase=(\w+)", line):
            st["phase"] = m[1]
        elif "Error" in line and "Traceback" not in line:
            st["failed"] = line.strip()
    # --task / --epochs come from the matching checkpoint report, or the command line of the process.
    task = log.stem
    report = _report_path(task)
    if report and report.stat().st_mtime >= log.stat().st_mtime - 5:
        st["report"] = json.loads(report.read_text())
        st["total_epochs"] = st["report"]["args"]["epochs"]
    if st["total_epochs"] is None:
        st["total_epochs"] = _epochs_from_cmdline(task) or 40
    st["running"] = _is_running(task) or _log_is_open(log)
    smoke = TRAIN_LOGS / f"{task}_smoke.log"
    if st.get("plan") and smoke.exists():  # speeds not measured yet in this run: use the smoke run's
        text = smoke.read_text(errors="ignore")
        rates = PROGRESS_RE.findall(text)
        if rates and "train" not in st["rate"]:
            st["rate"]["train"] = float(rates[-1][5])
        for m in EVAL_RE.finditer(text):
            st["rate"].setdefault(_family(("eval", m[1])), float(m[5]))
    if st.get("plan"):  # still unmeasured: the last speed any earlier run logged for the same kind of stage
        for fam, r in (cached("known_rates", 60, _known_rates) or {}).items():
            st["rate"].setdefault(fam, r)
    st["log_mtime"] = log.stat().st_mtime
    return st


def _procs() -> list[tuple[int, str]]:
    out = []
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                out.append((int(pid), Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")))
            except OSError:
                pass
    return out


def _cmdlines() -> list[str]:
    return [c for _, c in _procs()]


def _frozen(pid: int) -> bool:
    """True if the process sits in a frozen cgroup (systemctl --user freeze)."""
    try:
        cg = Path(f"/proc/{pid}/cgroup").read_text().strip().split("::", 1)[-1]
        return "frozen 1" in Path(f"/sys/fs/cgroup{cg}/cgroup.events").read_text()
    except OSError:
        return False


# Trainers that take no --task: log stem -> the module on their command line. A "_smoke" log matches
# only a --smoke process and the plain log only a non-smoke one, since both run the same module.
NO_TASK_JOBS = {"craters_yolo": "train_craters", "ships_yolo": "train_ships",
                "grounding_dino_rsvg": "finetune_grounding_dino",
                "grounding_dino_rsvg_smoke": "finetune_grounding_dino",
                "grounding_options": "eval_grounding_options", "grounding_options_smoke": "eval_grounding_options",
                "grounding_options_confirm": "eval_grounding_options"}


def _job_matches(task: str, cmdline: str) -> bool:
    if "training." not in cmdline and "scripts/" not in cmdline:
        return False
    if f"--task {task} " in cmdline + " ":
        return True
    module = NO_TASK_JOBS.get(task)
    return bool(module) and module in cmdline and (("--smoke" in cmdline) == task.endswith("_smoke"))


def _log_is_open(log: Path) -> bool:
    """True if any live process has the log as its stdout - covers every queued job (systemd StandardOutput=append)
    without needing a --task flag or a NO_TASK_JOBS entry."""
    target = str(log.resolve())
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                if os.readlink(f"/proc/{pid}/fd/1") == target:
                    return True
            except OSError:
                continue
    return False


def _is_running(task: str) -> bool:
    return any(_job_matches(task, c) for c in _cmdlines())


def _epochs_from_cmdline(task: str) -> int | None:
    for c in _cmdlines():
        if _job_matches(task, c) and (m := re.search(r"--epochs (\d+)", c)):
            return int(m[1])
    return None


def _report_path(task: str) -> Path | None:
    """train_seg/train_landcover write checkpoints/<task>_seg/; the YOLO and grounding trainers write
    checkpoints/<task>/."""
    for p in (ROOT / f"checkpoints/{task}_seg/report.json", ROOT / f"checkpoints/{task}/report.json"):
        if p.exists():
            return p
    return None


def _primary(v: dict, labels: list | None = None) -> tuple[str, float]:
    """Headline validation metric: segmentation/YOLO rows carry "iou" (named by "labels"); the
    grounding trainer reports top-1 "acc@0.5"."""
    if "iou" in v:
        return (labels or ["Val IoU"])[0], v["iou"]
    return "Acc@0.5", v.get("acc@0.5", 0.0)


def _secondary(v: dict, labels: list | None = None) -> tuple[str, float]:
    if "f1" in v:
        return (labels or ["Val IoU", "F1"])[1], v["f1"]
    return "mIoU", v.get("mean_iou", 0.0)


def render_train(st: dict, tick: bool) -> list[str]:
    lines = []
    total_ep = st["total_epochs"]
    done = len(st["epochs"])
    ep_secs = [e.get("sec", 0) for e in st["epochs"]]
    avg_ep = sum(ep_secs[-5:]) / max(len(ep_secs[-5:]), 1) if ep_secs else None
    prog = st["progress"]
    # Progress lines land every 50 train steps / 200 eval items (~15 s), so between them the clocks advance by
    # wall time since the log was last written. Capped, so a stalled job shows as stalled, not as finishing.
    quiet = time.time() - st["log_mtime"] if st["running"] else 0.0
    since = min(quiet, STALL_S)
    if avg_ep is None and prog and prog["rate"]:
        # No epoch has finished yet (still epoch 1): estimate seconds/epoch from the current step
        # rate instead of waiting for a completed epoch, so Total ETA isn't "--" the whole first epoch.
        avg_ep = prog["steps"] / prog["rate"]
    blink = "◉" if tick else "○"

    if prog:
        frac_ep, ep_elapsed = prog["step"] / prog["steps"], prog["elapsed"] + since
        ep_eta = max((prog["steps"] - prog["step"]) / prog["rate"] - since, 0) if prog["rate"] else None
        status = f"Step {prog['step']}/{prog['steps']}  {prog['rate']:.2f} it/s"
        cur = prog["epoch"]
    else:  # older log format: estimate from the time since the last epoch line
        ep_elapsed = time.time() - st["log_mtime"] if st["running"] else 0
        frac_ep = min(ep_elapsed / avg_ep, 0.99) if (avg_ep and st["running"]) else 0.0
        ep_eta = max(avg_ep - ep_elapsed, 0) if (avg_ep and st["running"]) else None
        status = "estimated from previous epoch time (run predates per-step logging)"
        cur = done + 1
    if st["phase"] in ("validate", "test", "baseline"):
        status = f"{st['phase']}…"
    if st["report"]:
        frac_total, status = 1.0, "complete"
    else:
        frac_total = (done + frac_ep) / total_ep
    total_elapsed = sum(ep_secs) + (ep_elapsed if st["running"] else 0)
    total_eta = (ep_eta or 0) + (total_ep - cur) * avg_ep if (avg_ep and st["running"]) else None
    stage = None
    if st["plan"] and not st["report"]:  # runs with a declared workload: ETA over every stage, evals included
        stage, stage_eta, total_elapsed, total_eta = plan_eta(st)
        if not st["running"]:
            stage_eta = total_eta = None
        else:
            total_elapsed += since
            stage_eta = max(stage_eta - since, 0) if stage_eta is not None else None
            total_eta = max(total_eta - since, 0) if total_eta is not None else None
        if total_eta is not None:
            frac_total = total_elapsed / max(total_elapsed + total_eta, 1e-9)
        else:
            frac_total = st["stage"] / len(st["plan"])

    name = st["log"].stem
    k = str(st["log"])
    total_eta = steady_eta(f"{k}:total", total_eta)
    total_elapsed = steady_elapsed(f"{k}:total_elapsed", total_elapsed)
    if stage:
        stage_eta = steady_eta(f"{k}:stage:{stage['label']}", stage_eta)
    else:
        ep_eta = steady_eta(f"{k}:epoch:{cur}", ep_eta)
    plan_done = bool(st["plan"]) and st["stage"] >= len(st["plan"])
    finished = bool(st["report"]) or plan_done
    state = "RUNNING" if st["running"] else ("FINISHED" if finished else "STOPPED part-way")
    kind = "EVALUATION" if st["plan"] and not any(s["kind"] == "train" for s in st["plan"]) else "TRAINING"
    took = (sum(x["elapsed"] for x in st["plan"]) if st["plan"] else sum(ep_secs)) if finished else total_elapsed
    st["summary"] = {"title": title_for(name), "running": st["running"], "finished": finished,
                     "frac": 1.0 if finished else frac_total, "eta": total_eta, "elapsed": total_elapsed,
                     "took": took, "ended": st["log_mtime"],
                     "now": (stage["label"] if stage else f"epoch {cur} of {total_ep}") if st["running"] else None}
    lines.append(row(f"  {'L A S T   R U N' if not st['running'] else 'C U R R E N T   R U N'}  ::  "
                     f"{title_for(name)}   [{kind} {state}]", "cyan"))
    lines.append(rule())
    if finished and not st["running"]:
        lines.append(row(f"  ✓ finished {time.strftime('%a %H:%M', time.localtime(st['log_mtime']))} · took {dur(took)}"
                         + (f" · all {len(st['plan'])} stages done" if st["plan"] else f" · {done} epochs"), "green"))
        stage = None
    elif not st["running"]:
        lines.append(row(f"  ■ stopped part-way at {time.strftime('%a %H:%M', time.localtime(st['log_mtime']))} "
                         f"({frac_total * 100:.0f}% done) — it is not running now", "red"))
        stage = None
    else:
        lines.append(row(f"  TOTAL [{bar(frac_total, 44)}] {frac_total * 100:6.2f}%", "green"))
        lines.append(row(f"  Total elapsed: {dur(total_elapsed)}     Total ETA: {dur(total_eta)}", "green"))
    if stage:
        f = stage["done"] / max(stage["n"], 1)
        lines.append(row(f"  {stage['label'].upper()}  {stage['done']}/{stage['n']} [{bar(f, 30)}] {f * 100:6.2f}%", "blue"))
        stage_elapsed = steady_elapsed(f"{k}:stage_elapsed:{stage['label']}", stage["elapsed"] + since)
        lines.append(row(f"  Stage elapsed: {dur(stage_elapsed)}     Stage ETA: {dur(stage_eta)}", "blue"))
        nxt = st["plan"][st["stage"] + 1:st["stage"] + 3]
        lines.append(row(f"  {blink if st['running'] else '■'} stage {st['stage'] + 1}/{len(st['plan'])}"
                         + (f"  · next: {', '.join(x['label'] for x in nxt)}" if nxt else ""), "yellow"))
    elif st["running"] and not st["report"]:
        lines.append(row(f"  EPOCH {cur}/{total_ep} [{bar(frac_ep, 36)}] {frac_ep * 100:6.2f}%", "blue"))
        lines.append(row(f"  Epoch elapsed: {dur(ep_elapsed)}     Epoch ETA: {dur(ep_eta)}", "blue"))
        lines.append(row(f"  {blink if st['running'] else '■'} {status}", "yellow"))
    if quiet > STALL_S:
        lines.append(row(f"  ! no new log line for {dur(quiet)} - clocks paused; the job may be stalled", "red"))
    if st["tiles"]:
        def n(x):  # a count, or {"records": n, "images": m} from the grounding trainer
            return x["records"] if isinstance(x, dict) else x
        t = " · ".join(f"{k} {n(v['train'])}/{n(v['val'])}/{n(v.get('test', v.get('test_clean', '?')))}"
                       for k, v in st["tiles"].items())
        lines.append(row(f"  tiles (train/val/test): {t}", "magenta"))
    if st["failed"] and not st["running"]:
        lines.append(row(f"  ✗ {st['failed']}", "red"))
    eval_only = bool(st["plan"]) and not any(s["kind"] == "train" for s in st["plan"])
    if st["epochs"] or st["report"] or not eval_only:  # an evaluation-only run has no epoch history to rule off
        lines.append(rule())

    best = max((_primary(e["val"])[1] for e in st["epochs"]), default=None)
    shown = st["epochs"][-HISTORY_N:] if HISTORY_N else []
    if len(st["epochs"]) > len(shown):
        lines.append(row(f"  … {len(st['epochs']) - len(shown)} earlier epochs", "grey"))
    for e in shown:
        v = e["val"]
        (a, va), (b, vb) = _primary(v, e.get("labels")), _secondary(v, e.get("labels"))
        is_best = va == best
        mark = "  [BEST]" if is_best else ""
        thr = f"  thr={v['threshold']:.2f}" if v.get("threshold") else ""
        pr = f"  P={v['precision']:.3f}  R={v['recall']:.3f}" if "precision" in v else ""
        lines.append(row(f"  [OK] Epoch {e['epoch']:>2}/{total_ep}  Loss={e['loss']:.3f}  {a}={va:.3f}  "
                         f"{b}={vb:.3f}{pr}{thr}  "
                         f"{e.get('sec', 0):.0f}s{mark}", "green" if is_best else "dgreen"))
    if st["running"] and not st["report"] and not (st["plan"] and not any(s["kind"] == "train" for s in st["plan"])):
        lines.append(row(f"  [{blink}] Epoch {cur}/{total_ep} in progress...", "yellow"))
    if r := st["report"]:
        lines.append(rule())
        bits = [f"best epoch {r['best_epoch']}" if r.get("best_epoch") is not None else "",
                f"threshold (frozen on val) {r['threshold_frozen_on_val']}" if r.get("threshold_frozen_on_val") is not None else "",
                f"peak GPU {r['peak_gpu_mem_gb']} GB" if r.get("peak_gpu_mem_gb") is not None else ""]
        if any(bits):
            lines.append(row("  " + "  ".join(b for b in bits if b), "cyan"))
        for k, v in (("baseline", r.get("baseline_zero_shot")), ("fine-tuned", r.get("finetuned"))):
            if isinstance(v, dict):  # grounding report: per-set Acc@0.5, base vs fine-tuned
                lines.append(row(f"  {k:<10} " + "  ".join(f"{s} {m['acc@0.5']:.3f}" for s, m in v.items()
                                                          if isinstance(m, dict) and "acc@0.5" in m), "cyan"))
        if r.get("test_all"):
            t = r["test_all"]
            lines.append(row(f"  TEST (all)  IoU={t['iou']:.3f}  F1={t['f1']:.3f}  P={t['precision']:.3f}  R={t['recall']:.3f}", "cyan"))
        for src, t in (r.get("test_per_source") or {}).items():
            a, b = t.get("labels", ["IoU", "F1"])
            lines.append(row(f"  TEST {src:<22} {a}={t['iou']:.3f}  {b}={t['f1']:.3f}  P={t['precision']:.3f}  R={t['recall']:.3f}", "cyan"))
    return lines


# ---------------------------------------------------------------- downloads
_size_cache: dict[str, tuple[float, int]] = {}


def dir_size(path: Path) -> int:
    key = str(path)
    now = time.time()
    if key in _size_cache and now - _size_cache[key][0] < 20:
        return _size_cache[key][1]
    try:
        out = subprocess.run(["du", "-sb", key], capture_output=True, text=True, timeout=10).stdout
        size = int(out.split()[0]) if out else 0
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        size = _size_cache.get(key, (0, 0))[1]
    _size_cache[key] = (now, size)
    return size


def active_downloads(manifest: list[dict]) -> dict[str, tuple[str, bool]]:
    """dataset name -> (progress text, paused) for datasets a download process is working on.

    Activity comes from process command lines (hf/kaggle/aws/curl/parallel_fetch carry the manifest ref);
    progress text is the last tqdm bar in the newest lane log for that source, when the tool prints one."""
    procs = [(pid, c) for pid, c in _procs()
             if not re.match(r"(/usr)?/bin/(ba)?sh |bash ", c)  # shell wrappers only mention refs in their text
             and re.search(r"bin/(hf|kaggle|aws) |parallel_fetch\.py|^curl |download_training_data\.py", c)]
    bars = {}
    for log in sorted(RAW.glob("_download_*.log"), key=lambda p: p.stat().st_mtime):
        if time.time() - log.stat().st_mtime > 120:
            continue
        with log.open("rb") as f:
            f.seek(max(0, log.stat().st_size - 4000))
            tail = f.read().decode(errors="ignore")
        m = None
        for m in TQDM_RE.finditer(tail):
            pass
        if m:
            bars[log.name] = f"{m[1]:>3}% {m[2]}  eta {m[4]}"
    active = {}
    for e in manifest:
        refs = [e["ref"].rstrip("/")] + [f["url"] for f in e.get("files", []) if isinstance(f, dict)]
        hits = [(pid, c) for pid, c in procs
                if any(r in c for r in refs) or f"--only {e['name']}" in c + " " and "download_training_data" in c
                and len(c.split("--only")[1].split()) == 1]
        if hits:
            paused = all(_frozen(pid) for pid, _ in hits)
            text = [t for n, t in bars.items() if refs[0] in _lane_fetching(RAW / n)]
            active[e["name"]] = (text[-1] if text else "", paused)
    return active


def _lane_fetching(log: Path) -> str:
    """The ref of the dataset this lane log most recently started fetching."""
    text = log.read_text(errors="ignore")
    refs = re.findall(r"fetch \S+ ← \w+:(\S+)", text)
    return refs[-1] if refs else ""


_our_rate = 0.0
_rate_prev: dict[str, tuple[float, int]] = {}
_rate_last: dict[str, float] = {}


def dir_rate(name: str, size: int) -> float:
    """Bytes/s from successive (cached, ~20 s apart) directory sizes."""
    now = time.time()
    prev = _rate_prev.get(name)
    if prev is None:
        _rate_prev[name] = (now, size)
    elif size != prev[1]:
        _rate_last[name] = max(0.0, (size - prev[1]) / (now - prev[0]))
        _rate_prev[name] = (now, size)
    elif now - prev[0] > 60:
        _rate_last[name] = 0.0
    return _rate_last.get(name, 0.0)


def render_downloads(manifest: list[dict], tick: bool) -> list[str]:
    global _our_rate
    _our_rate = 0.0
    lines = [row("  D O W N L O A D S", "cyan"), rule()]
    active = active_downloads(manifest)
    done_gb = total_gb = 0.0  # automatic queue only (not on hold, not manual)
    done_names: list[str] = []
    extra = {"hold": 0.0, "manual": 0.0}
    for e in manifest:
        name, gb = e["name"], float(e["approx_gb"])
        bucket = "manual" if e["source"] == "manual" else ("hold" if e.get("hold") else None)
        if bucket and not (RAW / name / ".complete").exists() and name not in active:
            extra[bucket] += gb
        else:
            total_gb += gb
        dest = RAW / name
        if (dest / ".complete").exists():
            done_gb += gb
            done_names.append(name)
            if COMPACT_DONE:
                continue
            lines.append(row(f"  ✓ {name:<24} {e['source']:<7} {human(dir_size(dest)):>17}   done", "dgreen"))
        elif name in active:
            have = dir_size(dest)
            frac = min(have / (gb * 1e9), 1.0)
            done_gb += frac * gb
            text, paused = active[name]
            rate = dir_rate(name, have)
            if not paused:
                _our_rate += rate
            status = "PAUSED" if paused else f"{human(rate)}/s  {text}".strip()
            lines.append(row(f"  {'■' if paused else ('◉' if tick else '○')} {name:<24} {e['source']:<7} "
                             f"{have / 1e9:>6.1f}/{gb:<5.1f} GB   {status}", "grey" if paused else "yellow"))
        else:
            state = "manual (you)" if e["source"] == "manual" else ("on hold" if e.get("hold") else "queued")
            lines.append(row(f"  · {name:<24} {e['source']:<7} {gb:>14.1f} GB   {state}", "grey"))
    lines.append(rule())
    if COMPACT_DONE and done_names:
        lines.insert(2, row(f"  ✓ {len(done_names)} done: {', '.join(done_names)}", "dgreen"))
    lines.append(row(f"  QUEUE [{bar(done_gb / total_gb, 44)}] {done_gb:6.1f} / {total_gb:.1f} GB", "green"))
    lines.append(row(f"  download sizes, not disk use · excluded: on hold {extra['hold']:.1f} GB, "
                     f"your ISPRS {extra['manual']:.1f} GB", "grey"))
    return lines


# ---------------------------------------------------------------- browser (user's Chrome downloads)
DOWNLOADS = Path.home() / "Downloads"
INGEST_LOG = RAW / "_ingest_isprs.log"
ISPRS_EXPECTED = {"Potsdam.zip": 12.4, "Vaihingen.zip": 14.9, "Toronto.zip": 3.2}  # GB, from Chrome's list
_browser_prev: dict[str, tuple[float, int]] = {}


def _chrome_names() -> dict[str, tuple[str, int]]:
    """crdownload path -> (target file name, total bytes), when Chrome has written it to its History DB.
    Chrome often commits in-progress rows late, so this is best-effort; an empty result is normal."""
    out = {}
    for db in (Path.home() / ".config/google-chrome").glob("*/History"):
        try:
            con = sqlite3.connect(f"file:{db}?immutable=1", uri=True, timeout=1)
            for target, current, total in con.execute(
                    "select target_path, current_path, total_bytes from downloads where state = 0"):
                if current:
                    out[Path(current).name] = (Path(target).name, int(total or 0))
            con.close()
        except sqlite3.Error:
            pass
    return out


def render_browser(tick: bool) -> list[str]:
    lines = [row("  B R O W S E R   D O W N L O A D S   (you, Chrome → ~/Downloads)", "cyan"), rule()]
    now = time.time()
    names = _chrome_names()
    partials = sorted(DOWNLOADS.glob("*.crdownload"))
    for p in partials:
        try:
            st = p.stat()
        except OSError:
            continue
        prev = _browser_prev.get(p.name)
        rate = (st.st_size - prev[1]) / (now - prev[0]) if prev and now > prev[0] else 0.0
        _browser_prev[p.name] = (now, st.st_size)
        stalled = now - st.st_mtime > 180
        target, total = names.get(p.name, (p.stem, 0))
        pct = f"{st.st_size / total * 100:5.1f}%" if total else "     "
        eta = dur((total - st.st_size) / rate) if total and rate > 0 else "--"
        lines.append(row(f"  {'◉' if tick else '○'} {target[:28]:<28} {human(st.st_size):>10} {pct}  "
                         f"{'stalled' if stalled else human(rate) + '/s':>12}  eta {eta}",
                         "grey" if stalled else "yellow"))
    dest = RAW / "isprs_potsdam_vaihingen"
    waiting = []
    for name, gb in ISPRS_EXPECTED.items():
        ingested = (dest / name).exists() or (dest / Path(name).stem).is_dir()
        if ingested:
            lines.append(row(f"  ✓ {name:<28} {gb:>7.1f} GB   ingested", "dgreen"))
        elif (DOWNLOADS / name).exists():
            lines.append(row(f"  ✓ {name:<28} {gb:>7.1f} GB   finished; waiting for the ingest watcher", "green"))
        elif name not in {t for t, _ in names.values()}:
            waiting.append(f"{Path(name).stem} {gb:g} GB")
    if waiting and partials:
        lines.append(row(f"  expected when done: {' · '.join(waiting)}", "grey"))
    if not partials:
        lines.append(row("  no Chrome downloads in progress", "grey"))
    if INGEST_LOG.exists():
        last = INGEST_LOG.read_text(errors="ignore").strip().splitlines()[-1:]
        active = subprocess.run(["systemctl", "--user", "is-active", "satquery-ingest-isprs"],
                                capture_output=True, text=True).stdout.strip()
        lines.append(row(f"  ingest watcher: {active}   {last[0][11:80] if last else ''}", "magenta"))
    return lines


# ---------------------------------------------------------------- system
_net_prev: tuple[float, int] | None = None


def net_rate() -> float:
    global _net_prev
    rx = 0
    for line in Path("/proc/net/dev").read_text().splitlines()[2:]:
        iface, data = line.split(":", 1)
        if iface.strip() != "lo" and not iface.strip().startswith(("docker", "veth", "tailscale", "br-")):
            rx += int(data.split()[0])
    now = time.time()
    rate = (rx - _net_prev[1]) / (now - _net_prev[0]) if _net_prev else 0.0
    _net_prev = (now, rx)
    return rate


def render_system() -> list[str]:
    mem = {l.split(":")[0]: int(l.split()[1]) for l in Path("/proc/meminfo").read_text().splitlines()}
    total, avail = mem["MemTotal"] / 1024, mem["MemAvailable"] / 1024
    swap_used = (mem["SwapTotal"] - mem["SwapFree"]) / 1024
    ram_frac = 1 - avail / total
    gpu = "n/a"
    try:
        g = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5).stdout
        u, mu, mt, t = [x.strip() for x in g.split(",")]
        gpu = f"{u:>3}%  {int(mu) / 1024:.1f}/{int(mt) / 1024:.1f} GB  {t}°C"
    except Exception:
        pass
    disk = shutil.disk_usage(ROOT)
    ram_color = "red" if avail < 1536 else "yellow" if avail < 3072 else "green"
    lines = [row("  S Y S T E M", "cyan"), rule(),
             row(f"  RAM  [{bar(ram_frac, 30)}] available {avail / 1024:.1f} GB of {total / 1024:.1f} GB"
                 f"   swap used {swap_used / 1024:.1f} GB", ram_color),
             row(f"  GPU  {gpu}", "blue"),
             row(f"  NET ↓ {human(net_rate())}/s total · mine {human(_our_rate)}/s · rest Chrome/other"
                 f" · disk free {human(disk.free)}", "magenta")]
    guard = TRAIN_LOGS / "mem_guard.log"
    active = subprocess.run(["systemctl", "--user", "is-active", "satquery-mem-guard"],
                            capture_output=True, text=True).stdout.strip()
    last = ""
    if guard.exists():
        events = [l for l in guard.read_text().splitlines() if "SIGTERM" in l and "sleep 600" not in l]
        last = f"   last stop: {events[-1][:60]}" if events else "   no stops yet"
    lines.append(row(f"  mem-guard (≥1 GB free): {active}{last}", "green" if active == "active" else "red"))
    return lines



# ---------------------------------------------------------------- queue, resources, background work
QUEUE_SH = RAW / "_jobs/train_queue.sh"
QUEUE_LOG = TRAIN_LOGS / "train_queue.log"
CLAUDE_PROJECT = Path.home() / ".claude/projects/-home-natsu-dev-isro"
CLAUDE_TASKS = Path(f"/tmp/claude-{os.getuid()}/-home-natsu-dev-isro")
_cpu_prev: dict[str, tuple[float, int]] = {}


def _sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def _queue_steps() -> list[tuple[str, Path | None, Path | None]]:
    """(unit, file whose existence makes the queue skip it, the step's log) for every `run` step, in order."""
    env = {"ROOT": str(ROOT), "R": str(TRAIN_LOGS), "C": str(ROOT / "checkpoints")}
    expand = lambda t, extra={}: re.sub(r"\$\{?(\w+)\}?", lambda m: {**env, **extra}.get(m[1], m[0]), t)  # noqa: E731
    steps, cond, loop = [], None, None
    for line in QUEUE_SH.read_text().splitlines():
        s = line.strip()
        if m := re.match(r"for (\w+) in ([^;]+); do", s):
            loop = (m[1], m[2].split())
        elif s == "done":
            loop = None
        elif s.startswith("if [ ! -"):  # `if [ ! -f A ] && [ ! -d B ]`: the step is skipped if ANY of them exists
            cond = re.findall(r"\[ ! -[fd] (\S+) \]", s) or None
        elif m := re.match(r"run (\S+) (\S+)", s):
            for v in (loop[1] if loop else [None]):
                extra = {loop[0]: v} if loop else {}
                paths = [Path(expand(c, extra)) for c in cond] if cond else []
                steps.append((expand(m[1], extra), [x if x.is_absolute() else ROOT / x for x in paths] or None,
                              Path(expand(m[2], extra))))
    return steps


# Plain-English names for runs (log stem) and queue steps; anything unlisted falls back to its own name.
JOB_TITLES = {
    "grounding_options": "Grounding check: which detector path wins (VRSBench sample 1)",
    "grounding_options_confirm": "Grounding check: confirmation (VRSBench sample 2)",
    "grounding_options_smoke": "Grounding check: smoke test",
    "grounding_dino_rsvg": "Grounding DINO fine-tune on DIOR-RSVG",
    "grounding_dino_rsvg_smoke": "Grounding DINO fine-tune: smoke test",
    "buildings_whu_ma_inria_r50": "Buildings model, retrained with Inria",
    "ships_yolo": "Ship detector (MASATI)",
    "ship_h2h": "Ships: YOLO vs Grounding DINO",
    "builtup_sn7": "Built-up model (SpaceNet 7)",
    "builtup_trend": "Built-up: does it track change over time",
    "cloud_rgbn": "Cloud model with near-infrared",
    "isprs_eroded": "ISPRS scores, benchmark protocol",
    "buildings_on_inria": "Served buildings model on Inria",
    "buildings_ood": "Buildings on unseen cities (LoveDA, OpenEarthMap)",
    "prepare_inria": "Cut Inria tiles", "prepare_spacenet7": "Prepare SpaceNet 7",
    "unit_tests": "Unit tests, one file at a time (CPU)",
    "grounding_pipe_ref": "Grounding: new referring path, end to end (VRSBench sample 1)",
    "grounding_pipe_ref_confirm": "Grounding: new referring path, end to end (VRSBench sample 2)",
}


def title_for(stem: str) -> str:
    return JOB_TITLES.get(stem, stem.replace("_", " "))


def _queue_info() -> dict:
    """The persistent queue as data: its state and every step's status, newest pass first-class."""
    state = _sh(["systemctl", "--user", "is-active", "satquery-train-queue"]) or "unknown"
    log = QUEUE_LOG.read_text(errors="ignore").splitlines() if QUEUE_LOG.exists() else []
    starts = [i for i, l in enumerate(log) if "queue start" in l]
    this_pass = log[starts[-1]:] if starts else []
    started, ended = {}, {}
    for l in this_pass:
        if m := re.match(r"\S+ \S+ start (\S+):", l):
            started[m[1]] = l[:19]
        elif m := re.match(r"\S+ \S+ (\S+) exit=(\d+)", l):
            ended[m[1]] = (l[:19], int(m[2]))

    def ts(a: str) -> float:
        return time.mktime(time.strptime(a, "%Y-%m-%d %H:%M:%S"))

    steps = []
    for unit, path, steplog in _queue_steps():
        d = {"unit": unit, "short": unit.removeprefix("satquery-"), "log": steplog,
             "title": title_for(steplog.stem) if steplog else unit.removeprefix("satquery-")}
        if unit in ended:
            e, rc = ended[unit]
            d.update(status="done" if rc == 0 else "failed", rc=rc, end=ts(e), took=ts(e) - ts(started[unit]))
        elif unit in started and state == "active":
            d.update(status="running", start=ts(started[unit]))
        elif path and any(x.exists() for x in path):
            d.update(status="done_earlier")
        else:
            d.update(status="pending" if state == "active" else "not_run")
        steps.append(d)
    return {"state": state, "steps": steps}


def render_queue(tick: bool) -> list[str]:
    """The persistent GPU queue: every step, done / running / failed / waiting, with durations."""
    if not QUEUE_SH.exists():
        return []
    q = _queue_info()
    steps = q["steps"]
    n_done = sum(st["status"] in ("done", "done_earlier") for st in steps)
    running = q["state"] == "active"
    head = [row(f"  Q U E U E   ::  GPU job queue is {'RUNNING' if running else 'stopped (nothing will start by itself)'}"
                f"   {n_done}/{len(steps)} steps done", "cyan"), rule()]
    earlier = [st["short"] for st in steps if st["status"] == "done_earlier"]
    rows = []
    if earlier:
        txt = ", ".join(earlier)
        rows.append(row(f"  ✓ done in earlier passes ({len(earlier)}): {txt[:W - 36]}{'…' if len(txt) > W - 36 else ''}", "dgreen"))
    for st in steps:
        name = st["title"][:44]
        if st["status"] in ("done", "failed"):
            ok = st["status"] == "done"
            rows.append(row(f"  {'✓' if ok else '✗'} {name:<45} {'finished' if ok else 'FAILED exit ' + str(st['rc']):<14} "
                            f"{time.strftime('%H:%M', time.localtime(st['end']))}  took {short(st['took'])}",
                            "green" if ok else "red"))
        elif st["status"] == "running":
            rows.append(row(f"  {'▶' if tick else '▷'} {name:<45} {'RUNNING':<14} for {short(time.time() - st['start'])}", "yellow"))
            if st["log"] and st["log"].exists():  # the step's own latest line, e.g. an eval's "120/300"
                tail = [l for l in tail_lines(st["log"], 4000)][-1:]
                if tail:
                    latest = re.sub(r"\s+", " ", tail[0]).strip()
                    rows.append(row(f"      latest: {latest[:W - 16]}", "grey"))
        elif st["status"] in ("pending", "not_run"):
            rows.append(row(f"  · {name:<45} {'waiting' if st['status'] == 'pending' else 'not started':<14}", "grey"))
    return head + rows


def _gpu_by_pid() -> dict[int, int]:
    out = _sh(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"])
    res = {}
    for line in out.splitlines():
        try:
            pid, mib = (int(x) for x in line.split(","))
            res[pid] = mib
        except ValueError:
            pass
    return res


def _cmd(pid: int) -> str:
    try:
        c = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore").strip()
    except OSError:
        return "?"
    if "eval '" in c:  # Claude Code's Bash tool wraps the real command in a shell snapshot + eval
        c = c.split("eval '", 1)[1].split("' <", 1)[0]
    return re.sub(r"\s+", " ", c).replace(str(ROOT) + "/", "").replace(".venv/bin/", "")


def render_resources() -> list[str]:
    """Every job in satquery.slice (memory, CPU, GPU) against the slice's caps, plus GPU users outside it."""
    cg = _sh(["systemctl", "--user", "show", "satquery.slice", "-p", "ControlGroup", "--value"])
    base = Path("/sys/fs/cgroup" + cg) if cg else None
    gpu = _gpu_by_pid()
    lines = []
    if base and base.exists():
        rd = lambda p: (p.read_text().strip() if p.exists() else "")  # noqa: E731
        cur, mx = int(rd(base / "memory.current") or 0), rd(base / "memory.max")
        mx_txt = "no cap" if mx in ("", "max") else human(int(mx))
        lines += [row(f"  R E S O U R C E S   satquery.slice  RAM {human(cur)} of {mx_txt} cap", "cyan"), rule()]
        now, seen_pids = time.time(), set()
        units = sorted(d for d in base.iterdir() if d.is_dir() and d.name.endswith((".service", ".scope")))
        for d in units:
            pids = [int(x) for x in rd(d / "cgroup.procs").split()]
            if not pids:
                continue
            seen_pids.update(pids)
            mem = int(rd(d / "memory.current") or 0)
            usage = int(re.search(r"usage_usec (\d+)", rd(d / "cpu.stat"))[1])
            prev = _cpu_prev.get(d.name)
            cpu = (usage - prev[1]) / 1e6 / (now - prev[0]) * 100 if prev and now > prev[0] else 0.0
            _cpu_prev[d.name] = (now, usage)
            g = sum(gpu.get(p, 0) for p in pids)
            name = d.name.removesuffix(".service").removeprefix("satquery-")
            lines.append(row(f"  ▶ {name[:26]:<26} RAM {human(mem):>9}  CPU {cpu:5.0f}%  GPU {g / 1024:4.1f} GB"
                             f"  {len(pids)} proc", "yellow"))
            lines.append(row(f"      {_cmd(pids[0])[:W - 8]}", "grey"))
        if not any(True for d in units if rd(d / "cgroup.procs")):
            lines.append(row("  no jobs running in the slice", "grey"))
        outside = {p: m for p, m in gpu.items() if p not in seen_pids and m > 100}
        for p, m in outside.items():
            lines.append(row(f"  GPU outside slice: pid {p} {m / 1024:.1f} GB  {_cmd(p)[:W - 40]}", "magenta"))
    return lines


def _open_task_outputs() -> dict[str, int]:
    """Background shell tasks still running: their .output file is held open by a live process."""
    held = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                t = os.readlink(f"/proc/{pid}/fd/{fd}")
                if t.endswith(".output") and str(CLAUDE_TASKS) in t:
                    held.setdefault(t, int(pid))
        except OSError:
            continue
    return held


_tool_counts: dict[str, tuple[int, int, str]] = {}  # transcript -> (bytes scanned, tool calls, last tool)


def _agent_progress(jsonl: Path) -> tuple[int, str]:
    """(tool calls so far, last tool) from the agent transcript, scanning only bytes added since last frame."""
    key = str(jsonl)
    done, n, last = _tool_counts.get(key, (0, 0, ""))
    try:
        size = jsonl.stat().st_size
        if size > done:
            with jsonl.open("rb") as f:
                f.seek(max(0, done - 200))  # small overlap so a call split across reads is not lost
                chunk = f.read().decode(errors="ignore")
            found = re.findall(r'"type":"tool_use","id":"([^"]+)","name":"([^"]+)"', chunk)
            seen = _tool_counts.get(key + ":ids", (0, 0, ""))[2]
            fresh = [(i, nm) for i, nm in found if i not in seen]
            n += len(fresh)
            last = fresh[-1][1] if fresh else last
            _tool_counts[key + ":ids"] = (0, 0, seen + "".join(i for i, _ in fresh))
            _tool_counts[key] = (size, n, last)
    except OSError:
        pass
    return n, last


def _proc_age(pid: int) -> float | None:
    """Seconds since a process started (from /proc/<pid>/stat field 22)."""
    try:
        ticks = int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])
        boot = float(Path("/proc/uptime").read_text().split()[0])
        return boot - ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError):
        return None


def render_background(tick: bool) -> list[str]:
    """Claude's background work for this project: workflow agents and background shell tasks.

    An agent has no known amount of work, so nothing can compute its true ETA. What is shown is measured:
    elapsed time and tool calls; the ETA is an *estimate* from the agents of the same workflow that have
    already finished (their median duration and tool-call count), and is labelled as one."""
    lines = [row("  B A C K G R O U N D   W O R K   (Claude agents and background tasks)", "cyan"), rule()]
    now, shown = time.time(), 0
    for journal in sorted(CLAUDE_PROJECT.glob("*/subagents/workflows/*/journal.jsonl")):
        if now - journal.stat().st_mtime > 6 * 3600:
            continue
        started, finished = {}, {}
        for l in journal.read_text(errors="ignore").splitlines():
            try:
                e = json.loads(l)
            except ValueError:
                continue
            if e.get("type") == "started":
                started[e["agentId"]] = e.get("label", e["agentId"])
            elif e.get("agentId"):
                finished[e["agentId"]] = e.get("type", "done")
        running = [a for a in started if a not in finished]
        if not running and now - journal.stat().st_mtime > 900:
            continue  # finished more than 15 min ago
        info = {}
        for a in started:
            meta, tr = journal.parent / f"agent-{a}.meta.json", journal.parent / f"agent-{a}.jsonl"
            t0 = meta.stat().st_mtime if meta.exists() else journal.stat().st_ctime
            t1 = tr.stat().st_mtime if (a in finished and tr.exists()) else now
            calls, last = _agent_progress(tr) if tr.exists() else (0, "")
            idle = now - tr.stat().st_mtime if tr.exists() else 0.0
            info[a] = dict(dur=t1 - t0, calls=calls, last=last, idle=idle)
        fin = sorted(info[a]["dur"] for a in finished if a in info)
        fin_calls = sorted(info[a]["calls"] for a in finished if a in info)
        med = fin[len(fin) // 2] if fin else None
        med_calls = fin_calls[len(fin_calls) // 2] if fin_calls else None
        wf_elapsed = max(i["dur"] for i in info.values()) if info else 0
        etas = [max(med - info[a]["dur"], 0) for a in running] if med else []
        wf_eta = f"≈ {dur(max(etas))} (est.)" if etas else ("--" if running else "done")
        lines.append(row(f"  workflow {journal.parent.name}: {len(finished)}/{len(started)} agents finished · "
                         f"elapsed {dur(wf_elapsed)} · ETA {wf_eta}", "magenta"))
        for a, label in started.items():
            i = info[a]
            if a in finished:
                lines.append(row(f"    ✓ {label:<26} {finished[a]:<7} took {dur(i['dur'])} · {i['calls']} tool calls",
                                 "dgreen"))
                continue
            frac = min(i["calls"] / med_calls, 0.99) if med_calls else 0.0
            if med is None:
                eta = "ETA unknown (no finished sibling to time against)"
            elif i["dur"] <= med:
                eta = f"ETA ≈ {dur(med - i['dur'])} (est. from siblings)"
            else:
                eta = f"past siblings' median by {dur(i['dur'] - med)}"
            lines.append(row(f"    {'◉' if tick else '○'} {label:<26} [{bar(frac, 14)}] {i['calls']}"
                             f"{f'/~{med_calls}' if med_calls else ''} tool calls · elapsed {dur(i['dur'])}", "yellow"))
            lines.append(row(f"        {eta} · last tool {i['last'] or '-'} {dur(i['idle'])} ago", "grey"))
        shown += 1
    for out, pid in sorted(_open_task_outputs().items()):
        task, age = Path(out).stem, _proc_age(pid)
        last = ""
        try:
            last = Path(out).read_text(errors="ignore").strip().splitlines()[-1:][0] if Path(out).stat().st_size else ""
        except (OSError, IndexError):
            pass
        lines.append(row(f"  {'◉' if tick else '○'} task {task} · elapsed {dur(age)} · ETA n/a (shell command)", "yellow"))
        lines.append(row(f"      {_cmd(pid)[:W - 8]}", "grey"))
        if last:
            lines.append(row(f"      last output: {last[:W - 22]}", "grey"))
        shown += 1
    if not shown:
        lines.append(row("  nothing running in the background", "grey"))
    return lines


# ---------------------------------------------------------------- shared helpers (synth-veda/dizzy style)
import socket
import threading
from collections import deque

CLK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")
SPARK = "  ··░░██"  # Ubuntu Sans Mono lacks ▁-▇; these glyphs do not overlap cells
DETAIL = 3  # 3 = everything; lowered per frame until the frame fits the terminal height
LOG_MAX_AGE_S = 12 * 3600
STACK = [("backend", 8000), ("frontend-v2", 3000)]
WRAPPER_RE = re.compile(r"(/usr)?(/bin/)?(ba)?sh -c |grep |pgrep |ssh |/usr/bin/time |systemd-run ")
SCRIPT_RE = re.compile(r"python[\d.]*\s+(?:-\S+\s+)*(\S+\.py)\b")
JOBS = [  # (label, regex on the command line) - ISRO jobs, most specific first
    ("seg train", r"training\.segmentation\.train_seg"),
    ("lc train", r"training\.segmentation\.train_landcover"),
    ("ship train", r"training\.detection\.train_ships"),
    ("crater train", r"training\.detection\.train_craters"),
    ("grounding ft", r"training\.grounding\.finetune_grounding_dino"),
    ("prepare", r"training\.segmentation\.prepare_\w+"),
    ("eval", r"scripts/(eval|evaluate)_\w+\.py"),
    ("download", r"download_training_data\.py|parallel_fetch\.py"),
    ("backend", r"uvicorn\s+backend\.app|backend\.app\.main"),
    ("frontend", r"next(-server| dev| start)"),
    ("pytest", r"-m pytest|bin/pytest"),
    ("modal", r"bin/modal (deploy|run|volume|serve)"),
]


def title(t: str, sub: str = "") -> list[str]:
    return [row("  " + " ".join(t) + (f"   ::  {sub}" if sub else ""), "cyan"), rule()]


def short(s: float | None) -> str:
    """Compact duration: 45s, 12m03s, 3h07m, 2d04h."""
    if s is None or s < 0 or s != s:
        return "--"
    s = int(s)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s // 3600}h{s // 60 % 60:02d}m" if s < 86400 else f"{s // 86400}d{s // 3600 % 24:02d}h"


def tail_lines(path: Path, nbytes: int = 200_000) -> list[str]:
    """Last lines of a log, splitting tqdm's \\r-separated updates into separate lines."""
    try:
        with path.open("rb") as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - nbytes))
            text = f.read().decode(errors="ignore")
    except OSError:
        return []
    return [l for l in re.split(r"[\r\n]", text.replace("\x00", "")) if l.strip()]


def rel(cmd: str) -> str:
    if "eval '" in cmd:  # Claude Code's Bash tool wraps the real command in a shell snapshot + eval
        cmd = cmd.split("eval '", 1)[1].split("' <", 1)[0]
    cmd = re.sub(r"\s+", " ", cmd)
    return cmd.replace(str(ROOT) + "/", "").replace(".venv/bin/python", "py").replace(".venv/bin/", "")


_cache: dict[str, tuple[float, object]] = {}


def cached(key: str, ttl: float, fn):
    """fn() at most every ttl seconds (git and du are too slow for every frame)."""
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        val = fn()
    except Exception:
        val = hit[1] if hit else None
    _cache[key] = (now, val)
    return val


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=10).stdout.strip()


# ---------------------------------------------------------------- processes
_pcpu_prev: dict[int, tuple] = {}


class Procs:
    """One /proc scan per frame: command lines of everything, stat details only for jobs shown."""

    def __init__(self) -> None:
        self.cmd: dict[int, str] = {}
        me = os.getpid()
        for d in os.listdir("/proc"):
            if d.isdigit() and int(d) != me:
                try:
                    c = Path(f"/proc/{d}/cmdline").read_bytes()
                except OSError:
                    continue
                if c:
                    self.cmd[int(d)] = c.replace(b"\0", b" ").decode(errors="ignore").strip()
        self.uptime = float(Path("/proc/uptime").read_text().split()[0])

    def find(self, pattern: str) -> list[int]:
        rx = re.compile(pattern)
        return sorted(p for p, c in self.cmd.items() if rx.search(c) and not WRAPPER_RE.match(c))

    def info(self, pid: int) -> dict | None:
        try:
            st = Path(f"/proc/{pid}/stat").read_text()
        except OSError:
            return None
        f = st[st.rindex(")") + 2:].split()
        cpu_s = (int(f[11]) + int(f[12])) / CLK
        now = time.time()
        prev = _pcpu_prev.get(pid)
        if prev and now - prev[1] < 1.0:
            pct = prev[2]
        else:
            pct = (cpu_s - prev[0]) / (now - prev[1]) * 100 if prev else None
            _pcpu_prev[pid] = (cpu_s, now, pct)
        return {"state": f[0], "age": self.uptime - int(f[19]) / CLK, "rss": int(f[21]) * PAGE, "cpu": pct,
                "ppid": int(f[1])}

    def stdout(self, pid: int) -> Path | None:
        try:
            p = os.readlink(f"/proc/{pid}/fd/1")
        except OSError:
            return None
        return Path(p) if p.startswith("/") and p.endswith(".log") else None


def isro_jobs(procs: Procs) -> list[tuple[str, int]]:
    """(label, pid) of everything this project runs: known jobs, then any python script run in or from the
    repo, then any other CUDA process, so nothing is invisible. DataLoader workers fold into their parent."""
    out, seen = [], set()
    for label, pat in JOBS:
        for pid in procs.find(pat):
            i = procs.info(pid)
            if i and i["ppid"] in seen:
                seen.add(pid)
                continue
            out.append((label, pid))
            seen.add(pid)
    for pid, cmd in sorted(procs.cmd.items()):
        if pid in seen or WRAPPER_RE.match(cmd):
            continue
        m = SCRIPT_RE.search(cmd)
        if not m or Path(m.group(1)).name == "watch_training.py":
            continue
        i = procs.info(pid)
        if i and i["ppid"] in seen:
            seen.add(pid)
            continue
        try:
            cwd = Path(os.readlink(f"/proc/{pid}/cwd"))
        except OSError:
            cwd = Path("/")
        if cwd == ROOT or ROOT in cwd.parents or str(ROOT) in cmd:
            out.append((Path(m.group(1)).stem[:13], pid))
            seen.add(pid)
    for pid in sorted(_gpu_apps):
        if pid not in seen and pid in procs.cmd:
            out.append(("GPU: " + Path(procs.cmd[pid].split()[0]).name[:8], pid))
    return out


def _job_step(label: str, cmd: str, procs: Procs, pid: int) -> str:
    """Plain words for what a job is doing right now, with its position when its log says so."""
    log = procs.stdout(pid)
    lines = tail_lines(log, 6000) if log else []
    p = [m for l in lines if (m := PROGRESS_RE.search(l))]
    e = [m for l in lines if (m := EVAL_RE.search(l))]
    where = ""
    if lines and (p or e):
        last_p = max((i for i, l in enumerate(lines) if PROGRESS_RE.search(l)), default=-1)
        last_e = max((i for i, l in enumerate(lines) if EVAL_RE.search(l)), default=-1)
        if last_e > last_p:
            where = f": scoring {e[-1][1]} {e[-1][2]}/{e[-1][3]}"
        else:
            where = f": epoch {p[-1][1]}/{p[-1][2]}, step {p[-1][3]}/{p[-1][4]}"
    task = re.search(r"--task (\S+)", cmd)
    if label == "seg train":
        return f"training segmenter {task[1] if task else '?'} (U-Net, GPU){where}"
    if label == "lc train":
        return f"training land-cover/ISPRS {task[1] if task else '?'} (GPU){where}"
    if label in ("ship train", "crater train"):
        return f"training the {label.split()[0]} detector (YOLO11s, GPU){where}"
    if label == "grounding ft":
        return f"fine-tuning Grounding DINO on DIOR-RSVG (GPU){where}"
    if label == "prepare":
        m = re.search(r"prepare_(\w+)", cmd)
        return f"preparing {m[1] if m else '?'} tiles (CPU)"
    if label == "eval":
        m = re.search(r"scripts/(\w+)\.py", cmd)
        mid = re.search(r"--grounding-model-id (\S+)", cmd)
        tail = next((re.sub(r"\s+", " ", l)[-50:] for l in reversed(lines)), "") if lines else ""
        return f"{m[1] if m else 'eval'}{' [' + Path(mid[1]).name + ']' if mid else ''}{where or (': ' + tail if tail else '')}"
    if label == "download":
        return "downloading training data"
    if label == "backend":
        return "SatQuery backend (FastAPI) on :8000"
    if label == "frontend":
        return "frontend-v2 (Next.js) on :3000"
    if label == "pytest":
        return "running tests"
    if label == "modal":
        return "Modal CLI (cloud deploy/volume)"
    return rel(cmd)[:70]


# ---------------------------------------------------------------- GPU / system
_prev: dict[str, tuple] = {}
_util_hist: deque = deque(maxlen=30)
_gpu_apps: dict[int, int] = {}  # pid -> MiB, refreshed by gpu_query() each frame
_pmon: dict[int, int] = {}  # pid -> GPU SM % (nvidia-smi pmon, background thread)
_cpu_tot: dict[str, tuple] = {}


def _rate(key: str, value: float) -> float:
    """Per-second rate since the last sample >= 1 s ago (a frame may be built several times while fitting)."""
    now = time.time()
    p = _prev.get(key)
    if p and now - p[0] < 1.0:
        return p[2]
    r = (value - p[1]) / (now - p[0]) if p else 0.0
    _prev[key] = (now, value, r)
    return r


def _disk_dev() -> str | None:
    try:
        st = os.stat(ROOT)
        return Path(f"/sys/dev/block/{os.major(st.st_dev)}:{os.minor(st.st_dev)}/uevent").read_text() \
            .split("DEVNAME=")[1].split()[0]
    except (OSError, IndexError):
        return None


DISK_DEV = _disk_dev()


def gpu_query() -> list[str] | None:
    global _gpu_apps
    try:
        g = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,"
                            "power.draw,power.limit,fan.speed,clocks.sm", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=5).stdout.strip().split(", ")
        apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=5).stdout
        _gpu_apps = {int(a.split(",")[0]): int(a.split(",")[1]) for a in apps.strip().splitlines() if "," in a}
        return g if len(g) == 9 else None
    except Exception:
        _gpu_apps = {}
        return None


def _pmon_loop() -> None:
    while True:
        try:
            out = subprocess.run(["nvidia-smi", "pmon", "-c", "1", "-s", "u"], capture_output=True,
                                 text=True, timeout=10).stdout
            d = {}
            for line in out.splitlines():
                f = line.split()
                if len(f) > 3 and f[1].isdigit():
                    d[int(f[1])] = int(f[3]) if f[3].isdigit() else 0
            _pmon.clear(); _pmon.update(d)
        except Exception:
            pass
        time.sleep(2)


def _machine_cpu() -> float | None:
    f = [int(x) for x in Path("/proc/stat").read_text().split("\n", 1)[0].split()[1:]]
    idle, total = f[3] + f[4], sum(f)
    prev = _cpu_tot.get("all")
    if prev and time.time() - prev[2] < 1.0:
        return prev[3]
    pct = 100 * (1 - (idle - prev[0]) / (total - prev[1])) if prev and total != prev[1] else None
    _cpu_tot["all"] = (idle, total, time.time(), pct)
    return pct


def sys_rows(procs: Procs) -> list[str]:
    out = title("SYSTEM")
    mem = {l.split(":")[0]: int(l.split()[1]) for l in Path("/proc/meminfo").read_text().splitlines()}
    total, avail = mem["MemTotal"] / 1024, mem["MemAvailable"] / 1024
    swap_used = (mem["SwapTotal"] - mem["SwapFree"]) / 1024
    ram_color = "red" if avail < 1536 else "yellow" if avail < 3072 else "green"
    out.append(row(f"  RAM  [{bar(1 - avail / total, 30)}] available {avail / 1024:.1f} GB of {total / 1024:.1f} GB"
                   f"   swap used {swap_used / 1024:.1f} GB", ram_color))
    cpu = [int(x) for x in Path("/proc/stat").read_text().split("\n", 1)[0].split()[1:]]
    busy_r, all_r = _rate("cpu_busy", sum(cpu) - cpu[3] - cpu[4]), _rate("cpu_all", sum(cpu))
    cpu_f = busy_r / all_r if all_r else 0
    load = " ".join(Path("/proc/loadavg").read_text().split()[:3])
    out.append(row(f"  CPU  [{bar(cpu_f, 30)}] {cpu_f * 100:5.1f}% of {os.cpu_count()} threads   load {load}",
                   "red" if cpu_f > 0.9 else "yellow" if cpu_f > 0.6 else "green"))
    g = gpu_query()
    if g:
        name, util, mu, mt, temp, pw, pl, fan, clk = g
        u, used, tot, t = int(util), int(mu), int(mt), int(temp)
        _util_hist.append(u)
        spark = "".join(SPARK[min(7, x * 8 // 101)] for x in _util_hist)
        out.append(row(f"  GPU  [{bar(u / 100, 30)}] util {u:>3}%  last {len(_util_hist)} frames {spark}", "blue"))
        out.append(row(f"  VRAM [{bar(used / tot, 30)}] {used / 1024:.1f}/{tot / 1024:.1f} GB   {t}°C  "
                       f"{float(pw):.0f}/{float(pl):.0f} W  fan {fan}%  SM {clk} MHz",
                       "red" if t >= 83 or used / tot > 0.95 else "yellow" if t >= 75 or used / tot > 0.85 else "blue"))
        if DETAIL >= 2:
            for pid, mib in sorted(_gpu_apps.items()):
                out.append(row(f"       → pid {pid:>7}  {mib:>5} MiB  {rel(procs.cmd.get(pid, '?'))}", "yellow"))
    else:
        out.append(row("  GPU  nvidia-smi unavailable", "red"))
    du = shutil.disk_usage(ROOT)
    free_gb = du.free / 1e9
    io = ""
    if DISK_DEV:
        for l in Path("/proc/diskstats").read_text().splitlines():
            f = l.split()
            if f[2] == DISK_DEV:
                io = f"   {DISK_DEV} write {human(_rate('dw', int(f[9]) * 512))}/s read {human(_rate('dr', int(f[5]) * 512))}/s"
    out.append(row(f"  DISK [{bar(1 - du.free / du.total, 30)}] free {free_gb:.0f} GB of {du.total / 1e9:.0f} GB{io}",
                   "red" if free_gb < 20 else "yellow" if free_gb < 60 else "green"))
    rx = tx = 0
    for l in Path("/proc/net/dev").read_text().splitlines()[2:]:
        iface, d = l.split(":", 1)
        if not iface.strip().startswith(("lo", "docker", "veth", "br-", "tailscale")):
            rx, tx = rx + int(d.split()[0]), tx + int(d.split()[8])
    out.append(row(f"  NET ↓ {human(_rate('rx', rx))}/s   ↑ {human(_rate('tx', tx))}/s", "magenta"))
    # The SatQuery memory guards: the slice's aggregate cap and the guard service that stops its largest job.
    cg = cached("slice_cg", 300, lambda: _sh(["systemctl", "--user", "show", "satquery.slice", "-p", "ControlGroup", "--value"]))
    base = Path("/sys/fs/cgroup" + cg) if cg else None
    if base and (base / "memory.current").exists():
        cur, mx = int((base / "memory.current").read_text()), (base / "memory.max").read_text().strip()
        mx_txt = "no cap" if mx == "max" else human(int(mx))
        guard = cached("guard", 10, lambda: _sh(["systemctl", "--user", "is-active", "satquery-mem-guard"]))
        out.append(row(f"  satquery.slice RAM {human(cur)} of {mx_txt} cap · mem-guard {guard}",
                       "green" if guard == "active" else "red"))
    return out


# ---------------------------------------------------------------- NOW RUNNING / PROCESSES
def now_rows(procs: Procs, tick: bool) -> list[str]:
    """What is running right now and where the CPU, RAM and GPU go: one plain line per active job,
    then Claude's agents, then everything else on the machine, so the columns add up to the totals."""
    ncpu = os.cpu_count() or 1
    out = title("NOW RUNNING", "what each job is doing and what it uses")
    out.append(row(f"    {'job':<13} {f'CPU (of {ncpu})':>11} {'RAM':>9} {'GPU use':>8} {'GPU mem':>9}   doing", "grey"))
    jobs_cpu = jobs_rss = jobs_vram = jobs_gpu = 0.0
    n = 0
    for label, pid in isro_jobs(procs):
        i = procs.info(pid)
        if not i:
            continue
        kids = [p for p in procs.cmd if p != pid and (k := procs.info(p)) and k["ppid"] == pid]
        rss = i["rss"] + sum((procs.info(k) or {}).get("rss", 0) for k in kids)
        n += 1
        cpu = ((i["cpu"] or 0) + sum((procs.info(k) or {}).get("cpu") or 0 for k in kids)) / ncpu
        vram, sm = _gpu_apps.get(pid, 0), _pmon.get(pid, 0)
        jobs_cpu += cpu; jobs_rss += rss; jobs_vram += vram; jobs_gpu += sm
        out.append(row(f"  {'◉' if tick else '○'} {label:<13} {cpu:>10.0f}% {human(rss):>9} {sm:>7}% {vram:>6} MiB   "
                       f"{_job_step(label, procs.cmd[pid], procs, pid)}", "yellow"))
    agents = _running_agents()
    for label, elapsed in agents:
        out.append(row(f"  {'◉' if tick else '○'} {'agent':<13} {'-':>11} {'-':>9} {'-':>8} {'-':>9}   "
                       f"Claude {label} (remote model; local cost is the CLI) · {short(elapsed)}", "magenta"))
    g = gpu_query()
    if not n and not agents:
        busy = bool(g) and int(g[1]) >= 20
        out.append(row("  nothing from SatQuery is running" + (f", but the GPU is {g[1]}% busy: see PROCESSES"
                       if busy else ": CPU and GPU are free"), "yellow" if busy else "green"))
    mcpu = _machine_cpu()
    mem = {l.split(":")[0]: int(l.split()[1]) * 1024 for l in Path("/proc/meminfo").read_text().splitlines()}
    used = mem["MemTotal"] - mem["MemAvailable"]
    gutil, gmem = (int(g[1]), int(g[2])) if g else (0, 0)
    gtot = int(g[3]) if g else 0
    out.append(row(f"  · {'other':<13} {max(0.0, (mcpu or 0) - jobs_cpu):>10.0f}% {human(max(0, used - jobs_rss)):>9} "
                   f"{max(0, gutil - jobs_gpu):>7.0f}% {max(0, gmem - jobs_vram):>6.0f} MiB   "
                   "everything else: desktop, IDE, Claude CLI, this dashboard", "white"))
    out.append(row(f"  = {'TOTAL':<13}{(mcpu or 0):>10.0f}% {human(used):>9} {gutil:>7}% {gmem:>6} MiB   "
                   f"of {ncpu} CPU threads · {human(mem['MemTotal'])} RAM · {gtot} MiB GPU memory", "cyan"))
    return out


def proc_rows(procs: Procs, tick: bool) -> list[str]:
    out = title("PROCESSES")
    out.append(row(f"    {'job':<13} {'pid':>7}  st  {'up':>7}  {'cpu':>5}  {'rss':>9}  {'vram':>8}  command", "grey"))
    n = 0
    for label, pid in isro_jobs(procs):
        i = procs.info(pid)
        if not i:
            continue
        n += 1
        cpu = f"{i['cpu']:.0f}%" if i["cpu"] is not None else "--"
        vram = f"{_gpu_apps[pid]} MiB" if pid in _gpu_apps else ""
        busy = i["state"] == "R" or (i["cpu"] or 0) > 5
        mark = ("◉" if tick else "○") if busy else ("■" if i["state"] == "T" else "·")
        out.append(row(f"  {mark} {label:<13} {pid:>7}  {i['state']:<2}  {short(i['age']):>7}  {cpu:>5}  "
                       f"{human(i['rss']):>9}  {vram:>8}  {rel(procs.cmd[pid])}",
                       "red" if i["state"] in "TZ" else "yellow" if busy else "white"))
    if not n:
        out.append(row("  no SatQuery processes running", "grey"))
    return out


def _running_agents() -> list[tuple[str, float]]:
    """(label, elapsed) of workflow agents still working, from the journals render_background reads."""
    res, now = [], time.time()
    for journal in CLAUDE_PROJECT.glob("*/subagents/workflows/*/journal.jsonl"):
        if now - journal.stat().st_mtime > 6 * 3600:
            continue
        started, ended = {}, set()
        for l in journal.read_text(errors="ignore").splitlines():
            try:
                e = json.loads(l)
            except ValueError:
                continue
            if e.get("type") == "started":
                started[e["agentId"]] = e.get("label", e["agentId"])
            elif e.get("agentId"):
                ended.add(e["agentId"])
        for a, label in started.items():
            if a not in ended:
                meta = journal.parent / f"agent-{a}.meta.json"
                res.append((label, now - (meta.stat().st_mtime if meta.exists() else journal.stat().st_ctime)))
    return res


# ---------------------------------------------------------------- PROJECT / MODELS / JOB LOGS / DATA / STACK
QNA = ROOT / "project/qna.md"


def project_rows(tick: bool) -> list[str]:
    out = title("PROJECT", "git, worktrees, change transcript")
    head = cached("git_head", 30, lambda: git("log", "-1", "--format=%h %s"))
    branch = cached("git_branch", 30, lambda: git("rev-parse", "--abbrev-ref", "HEAD"))
    dirty = cached("git_dirty", 30, lambda: git("status", "--porcelain"))
    nd = len(dirty.splitlines()) if dirty else 0
    out.append(row(f"  git {branch} @ {head}"[:W], "white"))
    out.append(row(f"  working tree: {nd} uncommitted file(s)" + ("" if nd else " (clean)"), "yellow" if nd else "green"))

    def worktrees() -> list[str]:
        res = []
        for block in git("worktree", "list", "--porcelain").split("\n\n")[1:]:
            path = next((l[9:] for l in block.splitlines() if l.startswith("worktree ")), "")
            br = next((l[18:] for l in block.splitlines() if l.startswith("branch refs/heads/")), "?")
            ahead = git("rev-list", "--count", f"{branch}..{br}") if br != "?" else "0"
            dirt = len(git("status", "--porcelain", cwd=Path(path)).splitlines()) if path else 0
            if ahead not in ("", "0") or dirt:
                res.append(f"  ⇢ {br:<34} {ahead} commit(s) not merged into {branch}" + (f", {dirt} uncommitted" if dirt else ""))
        return res
    for line in cached("worktrees", 120, worktrees) or []:
        out.append(row(line, "magenta"))
    if QNA.exists():
        heads = [l for l in tail_lines(QNA, 400_000) if l.startswith("## Q-")]
        for h in heads[-3:] if DETAIL >= 2 else heads[-1:]:
            out.append(row(f"  transcript {h[3:]}"[:W], "dcyan"))
    return out


def _served_models() -> list[tuple[str, str, bool, bool]]:
    cfg = yaml.safe_load((ROOT / "configs/models.yaml").read_text()) or {}
    models = cfg.get("models", cfg)
    res = []
    for key, m in models.items():
        if not isinstance(m, dict):
            continue
        ck = m.get("checkpoint_path") or ""
        mid = m.get("model_id") or ""
        # Adapters with a model_id load it from the Hugging Face cache (or a local dir); checkpoint_path is legacy.
        hf = Path.home() / ".cache/huggingface/hub" / ("models--" + mid.replace("/", "--")) if mid else None
        exists = bool(ck and (ROOT / ck).exists()) or bool(mid and ((ROOT / mid).exists() or (hf and hf.exists())))
        res.append((key, m.get("version") or mid or "?", bool(m.get("enabled", True)), exists))
    return res


def models_rows(tick: bool) -> list[str]:
    out = title("MODELS", "configs/models.yaml (served) · trained but not served")
    served = cached("served", 30, _served_models) or []
    cells = [f"{'✓' if ok and en else '✗' if en else '·'} {k}" for k, _, en, ok in served]
    per = max(1, (W - 2) // 30)
    for i in range(0, len(cells), per):
        out.append(row("  " + "".join(f"{c[:29]:<30}" for c in cells[i:i + per]), "green"))
    missing = [k for k, _, en, ok in served if en and not ok]
    if missing:
        out.append(row(f"  ! enabled but weights missing on disk: {', '.join(missing)}", "red"))
    used = (ROOT / "configs/models.yaml").read_text()
    idle = sorted(d.name for d in (ROOT / "checkpoints").iterdir()
                  if d.is_dir() and (any(d.glob("report.json")) or any(d.glob("*.pt")) or any(d.glob("*.safetensors")))
                  and f"checkpoints/{d.name}" not in used)
    if idle and DETAIL >= 2:
        txt = ", ".join(idle)
        out.append(row(f"  kept, not served ({len(idle)}): {txt}"[:W], "grey"))
    return out


def logs_rows(procs: Procs, tick: bool) -> list[str]:
    """Every results/training or results/eval log written in the last 12 h: running or finished, last line."""
    out = title("JOB LOGS", "results/training + results/eval, last 12 h")
    now = time.time()
    running_logs = {str(procs.stdout(p)) for p in procs.cmd if procs.stdout(p)}
    logs = [p for d in (TRAIN_LOGS, ROOT / "results/eval") if d.exists() for p in d.glob("*.log")
            if p.name not in ("sysmon.log", "mem_guard.log", "train_queue.log") and now - p.stat().st_mtime < LOG_MAX_AGE_S]
    logs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        out.append(row("  no job logs in the last 12 h", "grey"))
    for p in logs[: (8 if DETAIL >= 3 else 4)]:
        live = str(p) in running_logs
        last = next((re.sub(r"\s+", " ", l).strip() for l in reversed(tail_lines(p, 8000))
                     if len(re.findall(r"[A-Za-z0-9]", l)) >= 8  # skip "}" / "]" closing JSON blocks
                     and not l.startswith(("Loading weights", "  warnings.warn"))), "")
        mark = ("◉" if tick else "○") if live else "·"
        out.append(row(f"  {mark} {p.stem[:30]:<30} {short(now - p.stat().st_mtime):>7} ago  {last}"[:W + 2],
                       "yellow" if live else "white"))
    return out


_sizes: dict[str, int] = {}
_size_thread: threading.Thread | None = None


def _du_loop() -> None:
    while True:
        try:
            res = {}
            for d in sorted(RAW.iterdir()):
                if d.is_dir() and not d.name.startswith("_"):
                    total = 0
                    for root, _, files in os.walk(d):
                        for f in files:
                            try:
                                total += os.lstat(os.path.join(root, f)).st_size
                            except OSError:
                                pass
                    res[d.name] = total
            _sizes.clear(); _sizes.update(res)
        except Exception:
            pass
        time.sleep(300)


def data_rows(manifest: list[dict], tick: bool) -> list[str]:
    out = title("DATA", "datasets/raw (sizes refresh every 5 min)")
    if not _sizes:
        out.append(row("  measuring dataset sizes…", "grey"))
        return out
    total = sum(_sizes.values())
    cells = [f"{k[:22]} {human(v)}" for k, v in sorted(_sizes.items(), key=lambda kv: -kv[1])]
    per = max(1, (W - 2) // 33)
    for i in range(0, len(cells), per):
        out.append(row("  " + "".join(f"{c:<33}" for c in cells[i:i + per]), "white"))
    pruned = sorted((RAW / "_pruned").glob("apply_phase*.sh")) if (RAW / "_pruned").exists() else []
    out.append(row(f"  total {human(total)} · prune scripts kept: {', '.join(p.stem for p in pruned) or 'none'}"
                   " (qna Q-070, Q-073, Q-077)", "grey"))
    if active_downloads(manifest):
        out += render_downloads(manifest, tick)[2:]
    return out


def _port_up(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def stack_rows() -> list[str]:
    out = title("STACK", "local services (TCP connect only)")
    out.append(row("  " + "   ".join(f"{'●' if _port_up(p) else '○'} {n} :{p}" for n, p in STACK), "white"))
    return out


def render_status(run: dict | None, procs: "Procs", tick: bool) -> list[str]:
    """The answer to "what is going on?" in plain words, before any detail."""
    out = title("STATUS", "what is happening, in plain words")
    q = _queue_info() if QUEUE_SH.exists() else {"state": "unknown", "steps": []}
    running_step = next((st for st in q["steps"] if st["status"] == "running"), None)
    jobs = [l for l, _ in isro_jobs(procs) if not l.startswith("GPU:")]
    agents = _running_agents()
    if run and run.get("running"):
        eta = run.get("eta")
        when = time.strftime("%H:%M", time.localtime(time.time() + eta)) if eta is not None else None
        left = f"about {short(eta)} left, done around {when}" if eta is not None else "time left not known yet"
        out.append(row(f"  {'▶' if tick else '▷'} RUNNING: {run['title']}", "yellow"))
        out.append(row(f"      {run['frac'] * 100:.0f}% done · {left} · running for {short(run['elapsed'])}", "yellow"))
        if run.get("now"):
            out.append(row(f"      now: {run['now']}", "grey"))
    elif running_step:
        out.append(row(f"  {'▶' if tick else '▷'} RUNNING: {running_step['title']} (for {short(time.time() - running_step['start'])};"
                       " this step reports no progress, so no ETA)", "yellow"))
    elif jobs:
        out.append(row(f"  {'▶' if tick else '▷'} RUNNING outside the queue: {', '.join(sorted(set(jobs)))} (see NOW RUNNING)", "yellow"))
    else:
        out.append(row("  ● IDLE: nothing from SatQuery is running. GPU and job pool are free.", "green"))
    done = [st for st in q["steps"] if st["status"] in ("done", "failed")]
    last = max(done, key=lambda st: st["end"], default=None)
    if last:
        ok = last["status"] == "done"
        out.append(row(f"  {'✓' if ok else '✗'} last {'finished' if ok else 'FAILED'}: {last['title']} at "
                       f"{time.strftime('%a %H:%M', time.localtime(last['end']))} (took {short(last['took'])})",
                       "green" if ok else "red"))
    elif run and run.get("finished"):
        out.append(row(f"  ✓ last finished: {run['title']} at {time.strftime('%a %H:%M', time.localtime(run['ended']))}"
                       f" (took {short(run['took'])})", "green"))
    waiting = [st["title"] for st in q["steps"] if st["status"] in ("pending", "not_run")]
    if waiting:
        how = "will run next" if q["state"] == "active" else "queued but the queue is stopped — they start only when it is started"
        out.append(row(f"  … {len(waiting)} step(s) {how}: {', '.join(waiting)}"[:W], "grey"))
    else:
        out.append(row(f"  ✓ queue: all {len(q['steps'])} steps done, nothing waiting", "dgreen"))
    out.append(row(f"  Claude agents working: {len(agents)}" + (f" ({', '.join(a for a, _ in agents)})" if agents else ""),
                   "magenta" if agents else "grey"))
    return out


def build_frame(args, manifest, tick: bool) -> list[str]:
    procs = Procs()
    out = [rule("top"), row(f"  {'◉' if tick else '○'} S A T Q U E R Y   A I  on {socket.gethostname()}   ::   "
                            f"~/dev/isro   ::   {time.strftime('%a %d %b  %H:%M:%S')}", "bold"), rule()]
    sysr = sys_rows(procs)  # first: it refreshes the GPU pid list NOW RUNNING and PROCESSES use
    log = args.log or newest_train_log()
    run_st = parse_train(log) if log and log.exists() else None
    run_lines = render_train(run_st, tick) if run_st else [row("  no run log yet", "grey")]
    out += render_status(run_st.get("summary") if run_st else None, procs, tick) + [rule()]
    out += now_rows(procs, tick) + [rule()]
    out += render_queue(tick) + [rule()]
    out += run_lines
    out += [rule()] + render_background(tick) + [rule()]
    if DETAIL >= 1:
        out += project_rows(tick) + [rule()] + models_rows(tick) + [rule()]
    if DETAIL >= 2:
        out += logs_rows(procs, tick) + [rule()] + data_rows(manifest, tick) + [rule()]
    out += stack_rows() + [rule()]
    if DETAIL >= 3:
        out += proc_rows(procs, tick) + [rule()]
    out += sysr + [rule("bot")]
    out.append(paint(f"  {time.strftime('%H:%M:%S')}   Ctrl+C to exit (read-only; nothing is stopped)", "grey"))
    return out


def fit_frame(args, manifest, tick: bool) -> list[str]:
    """Shrink W to the terminal, then fewer epoch rows, then less detail, then cut with a note."""
    global W, DETAIL, HISTORY_N
    cols, rows_ = shutil.get_terminal_size((110, 60))
    W = max(60, min(cols - 2, 120))
    DETAIL, HISTORY_N = 3, 12
    out = build_frame(args, manifest, tick)
    if len(out) > rows_:
        HISTORY_N = max(0, 12 - (len(out) - rows_))
        out = build_frame(args, manifest, tick)
    for DETAIL in (2, 1, 0):
        if len(out) <= rows_:
            break
        out = build_frame(args, manifest, tick)
    if len(out) > rows_:
        hidden = len(out) - rows_ + 1
        out = out[: rows_ - 1] + [paint(f"  … {hidden} more lines; enlarge the window to see them", "grey")]
    return out


def main() -> None:
    global _size_thread
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=None, help="training log (default: newest)")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--once", action="store_true", help="print one frame and exit (for testing)")
    args = ap.parse_args()
    threading.Thread(target=_pmon_loop, daemon=True, name="pmon").start()
    _size_thread = threading.Thread(target=_du_loop, daemon=True, name="du")
    _size_thread.start()
    manifest_path = ROOT / "datasets/manifests/training_sources.yaml"

    def frame(tick: bool) -> list[str]:
        manifest = yaml.safe_load(manifest_path.read_text())["datasets"]
        try:
            return fit_frame(args, manifest, tick)
        except Exception as e:  # one malformed log line must not close the window; show it and retry
            return [paint(f"  dashboard error: {type(e).__name__}: {e} (retrying every {args.interval:.0f}s)", "red")]

    if args.once:
        frame(False)  # primes the rate counters
        time.sleep(3)
        print("\n".join(frame(False)))
        return
    tick = False
    sys.stdout.write("\033[?1049h\033[?25l")  # alternate screen, like top: nothing piles up in scrollback
    try:
        while True:
            tick = not tick
            out = frame(tick)
            sys.stdout.write("\033[H" + "\n".join(line + "\033[K" for line in out) + "\033[J")
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\033[?1049l")


if __name__ == "__main__":
    main()
