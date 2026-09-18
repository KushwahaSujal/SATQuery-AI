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
HISTORY_N = 12  # epoch rows shown; reduced per frame to fit the terminal height
COMPACT_DONE = False  # collapse finished downloads into one line when the terminal is short

C = {"cyan": "36", "dcyan": "2;36", "green": "32", "dgreen": "2;32", "blue": "34", "yellow": "33",
     "magenta": "35", "red": "31", "grey": "2;37", "white": "37", "bold": "1"}

EPOCH_RE = re.compile(r'^\{"epoch": (\d+)')
PROGRESS_RE = re.compile(r"progress epoch=(\d+)/(\d+) step=(\d+)/(\d+) elapsed=([\d.]+)s rate=([\d.]+)it/s")
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


def parse_train(log: Path) -> dict:
    text = log.read_text(errors="ignore").replace("\x00", "")
    st = {"log": log, "epochs": [], "progress": None, "phase": "train", "tiles": None,
          "total_epochs": None, "report": None, "failed": None}
    for line in text.splitlines():
        if line.startswith("tiles:"):
            st["tiles"] = json.loads(line[len("tiles:"):])
        elif EPOCH_RE.match(line):
            st["epochs"].append(json.loads(line))
            st["progress"], st["phase"] = None, "train"
        elif m := PROGRESS_RE.search(line):  # YOLO's tqdm bar can precede it on the same line
            st["progress"] = dict(epoch=int(m[1]), total=int(m[2]), step=int(m[3]), steps=int(m[4]),
                                  elapsed=float(m[5]), rate=float(m[6]))
            st["total_epochs"] = int(m[2])
        elif m := re.search(r"phase=(\w+)", line):
            st["phase"] = m[1]
        elif "Error" in line and "Traceback" not in line:
            st["failed"] = line.strip()
    # --task / --epochs come from the matching checkpoint report, or the command line of the process.
    task = log.stem
    report = ROOT / f"checkpoints/{task}_seg/report.json"
    if report.exists() and report.stat().st_mtime >= log.stat().st_mtime - 5:
        st["report"] = json.loads(report.read_text())
        st["total_epochs"] = st["report"]["args"]["epochs"]
    if st["total_epochs"] is None:
        st["total_epochs"] = _epochs_from_cmdline(task) or 40
    st["running"] = _is_running(task)
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


def _is_running(task: str) -> bool:
    for c in _cmdlines():
        if "training." not in c:
            continue
        if f"--task {task} " in c + " ":
            return True
        if task == "craters_yolo" and "train_craters" in c:
            return True
    return False


def _epochs_from_cmdline(task: str) -> int | None:
    for c in _cmdlines():
        if "training." in c and (f"--task {task} " in c + " " or (task == "craters_yolo" and "train_craters" in c)) \
                and (m := re.search(r"--epochs (\d+)", c)):
            return int(m[1])
    return None


def render_train(st: dict, tick: bool) -> list[str]:
    lines = []
    total_ep = st["total_epochs"]
    done = len(st["epochs"])
    ep_secs = [e.get("sec", 0) for e in st["epochs"]]
    avg_ep = sum(ep_secs[-5:]) / max(len(ep_secs[-5:]), 1) if ep_secs else None
    prog = st["progress"]
    if avg_ep is None and prog and prog["rate"]:
        # No epoch has finished yet (still epoch 1): estimate seconds/epoch from the current step
        # rate instead of waiting for a completed epoch, so Total ETA isn't "--" the whole first epoch.
        avg_ep = prog["steps"] / prog["rate"]
    blink = "◉" if tick else "○"

    if prog:
        frac_ep, ep_elapsed = prog["step"] / prog["steps"], prog["elapsed"]
        ep_eta = (prog["steps"] - prog["step"]) / prog["rate"] if prog["rate"] else None
        status = f"Step {prog['step']}/{prog['steps']}  {prog['rate']:.2f} it/s"
        cur = prog["epoch"]
    else:  # older log format: estimate from the time since the last epoch line
        ep_elapsed = time.time() - st["log_mtime"] if st["running"] else 0
        frac_ep = min(ep_elapsed / avg_ep, 0.99) if (avg_ep and st["running"]) else 0.0
        ep_eta = max(avg_ep - ep_elapsed, 0) if (avg_ep and st["running"]) else None
        status = "estimated from previous epoch time (run predates per-step logging)"
        cur = done + 1
    if st["phase"] in ("validate", "test"):
        status = f"{st['phase']}…"
    if st["report"]:
        frac_total, status = 1.0, "complete"
    else:
        frac_total = (done + frac_ep) / total_ep
    total_elapsed = sum(ep_secs) + (ep_elapsed if st["running"] else 0)
    total_eta = (ep_eta or 0) + (total_ep - cur) * avg_ep if (avg_ep and st["running"]) else None

    name = st["log"].stem
    state = "RUNNING" if st["running"] else ("COMPLETE" if st["report"] else "STOPPED")
    lines.append(row(f"  S A T Q U E R Y  ::  {name}  TRAIN   [{state}]", "cyan"))
    lines.append(rule())
    lines.append(row(f"  TOTAL [{bar(frac_total, 44)}] {frac_total * 100:6.2f}%", "green"))
    lines.append(row(f"  Total elapsed: {dur(total_elapsed)}     Total ETA: {dur(total_eta)}", "green"))
    if not st["report"]:
        lines.append(row(f"  EPOCH {cur}/{total_ep} [{bar(frac_ep, 36)}] {frac_ep * 100:6.2f}%", "blue"))
        lines.append(row(f"  Epoch elapsed: {dur(ep_elapsed)}     Epoch ETA: {dur(ep_eta)}", "blue"))
        lines.append(row(f"  {blink if st['running'] else '■'} {status}", "yellow"))
    if st["tiles"]:
        t = " · ".join(f"{k} {v['train']}/{v['val']}/{v['test']}" for k, v in st["tiles"].items())
        lines.append(row(f"  tiles (train/val/test): {t}", "magenta"))
    if st["failed"] and not st["running"]:
        lines.append(row(f"  ✗ {st['failed']}", "red"))
    lines.append(rule())

    best = max((e["val"]["iou"] for e in st["epochs"]), default=None)
    shown = st["epochs"][-HISTORY_N:] if HISTORY_N else []
    if len(st["epochs"]) > len(shown):
        lines.append(row(f"  … {len(st['epochs']) - len(shown)} earlier epochs", "grey"))
    for e in shown:
        v = e["val"]
        a, b = e.get("labels", ["Val IoU", "F1"])
        is_best = v["iou"] == best
        mark = "  [BEST]" if is_best else ""
        thr = f"  thr={v['threshold']:.2f}" if v.get("threshold") else ""
        lines.append(row(f"  [OK] Epoch {e['epoch']:>2}/{total_ep}  Loss={e['loss']:.3f}  {a}={v['iou']:.3f}  "
                         f"{b}={v['f1']:.3f}  P={v['precision']:.3f}  R={v['recall']:.3f}{thr}  "
                         f"{e.get('sec', 0):.0f}s{mark}", "green" if is_best else "dgreen"))
    if st["running"] and not st["report"]:
        lines.append(row(f"  [{blink}] Epoch {cur}/{total_ep} in progress...", "yellow"))
    if r := st["report"]:
        lines.append(rule())
        lines.append(row(f"  best epoch {r.get('best_epoch')}  threshold (frozen on val) {r.get('threshold_frozen_on_val')}"
                         f"  peak GPU {r.get('peak_gpu_mem_gb')} GB", "cyan"))
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


def build_frame(args, manifest, tick: bool) -> list[str]:
    out = [rule("top")]
    log = args.log or newest_train_log()
    out += render_train(parse_train(log), tick) if log and log.exists() else [row("  no training log yet", "grey")]
    out += [rule()] + render_downloads(manifest, tick) + [rule()] + render_browser(tick)
    out += [rule()] + render_system() + [rule("bot")]
    out.append(paint(f"  {time.strftime('%H:%M:%S')}   Ctrl+C to exit (read-only; nothing is stopped)", "grey"))
    return out


def main() -> None:
    global W, HISTORY_N, COMPACT_DONE
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=None, help="training log (default: newest)")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()
    tick = False
    # Alternate screen (like top/htop): each frame overwrites the last, nothing piles up in scrollback.
    sys.stdout.write("\033[?1049h\033[?25l")
    try:
        while True:
            tick = not tick
            cols, rows = shutil.get_terminal_size((100, 50))
            W = max(40, min(92, cols - 2))
            # Re-read every frame so datasets added while the dashboard is open show up.
            manifest = yaml.safe_load((ROOT / "datasets/manifests/training_sources.yaml").read_text())["datasets"]
            HISTORY_N, COMPACT_DONE = 12, False
            out = build_frame(args, manifest, tick)
            if len(out) > rows:  # too tall: fewer epoch rows first, then collapse finished downloads
                HISTORY_N = max(0, 12 - (len(out) - rows))
                out = build_frame(args, manifest, tick)
            if len(out) > rows:
                COMPACT_DONE = True
                out = build_frame(args, manifest, tick)
            if len(out) > rows:
                hidden = len(out) - rows + 1
                out = out[: rows - 1] + [paint(f"  … {hidden} more lines; enlarge the window to see them", "grey")]
            sys.stdout.write("\033[H" + "\n".join(line + "\033[K" for line in out) + "\033[J")
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\033[?1049l")


if __name__ == "__main__":
    main()
