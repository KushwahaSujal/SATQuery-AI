"""Runs the four recorded-demo prompts against the deployed backend and prints what each returned.

Run it ~5 minutes before recording: it wakes the Modal GPU container and loads every model the demo
touches, so nothing on camera pays the cold start. It also re-measures the numbers the runbook quotes
(demo_resources/RECORDING.md), so what you say on camera matches what the site will show.

Usage:
    .venv/bin/python scripts/demo/rehearse_deployed.py            # all four
    .venv/bin/python scripts/demo/rehearse_deployed.py mask vqa   # a subset
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "demo_resources"


def _env(name: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


BASE = _env("SATQUERY_CLOUD_URL").rstrip("/")
KEY = _env("SATQUERY_TEAM_API_KEYS").split(",")[0].strip()

CASES = {
    "mask": ("image", [R / "1_masking/airport_airplanes__P0173_0003.png"], "mask airplanes"),
    "vqa": ("image", [R / "1_masking/airport_airplanes__P0173_0003.png"], "what type of area is shown in this image?"),
    "change": ("image", [R / "2_change_detection/levir_scene_100/before.png",
                         R / "2_change_detection/levir_scene_100/after.png"], "detect building changes"),
    "video": ("video", [R / "4_video/real_aerial_footage.mp4"], "find all vehicles"),
}


def run(c: httpx.Client, kind: str, files: list, q: str) -> dict:
    t = time.time()
    if kind == "video":
        d = c.post(f"{BASE}/api/video/analyze",
                   files={"file": (files[0].name, files[0].read_bytes(), "video/mp4")}, data={"query": q}).json()
        out = {"job": d.get("job_id"), "status": d.get("status"),
               "events": [(f["start_timestamp"], f["end_timestamp"]) for f in d.get("flags", [])]}
    else:
        up = c.post(f"{BASE}/api/upload", files=[("files", (f.name, f.read_bytes())) for f in files]).json()
        d = c.post(f"{BASE}/api/analyze", json={"query": q, "image_filenames": [f.name for f in files],
                                                 "request_id": up["request_id"]}).json()
        out = {"job": d.get("request_id"), "status": d.get("status"), "workflow": d.get("workflow"),
               "confidence": d.get("confidence"), "answer": d.get("answer")}
    return {"secs": round(time.time() - t, 1), **out}


def main() -> int:
    if not BASE or not KEY:
        print("SATQUERY_CLOUD_URL / SATQUERY_TEAM_API_KEYS missing from .env", file=sys.stderr)
        return 1
    picked = sys.argv[1:] or list(CASES)
    rows, failed = [], False
    with httpx.Client(timeout=900, headers={"X-API-Key": KEY}) as c:
        t = time.time()
        h = c.get(f"{BASE}/api/health").json()
        print(f"health {h.get('status')} in {time.time() - t:.1f}s, "
              f"{sum(h.get('models_available', {}).values())}/{len(h.get('models_available', {}))} models")
        for name in picked:
            kind, files, q = CASES[name]
            try:
                row = {"case": name, "query": q, **run(c, kind, files, q)}
                failed |= row.get("status") not in ("COMPLETED", "completed")
            except Exception as e:  # keep going: one broken case should not hide the others
                row, failed = {"case": name, "query": q, "error": f"{type(e).__name__}: {e}"}, True
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False)[:600])
    out = ROOT / "results/evaluations" / f"demo_rehearsal_{datetime.now():%Y%m%d_%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"base": BASE, "rows": rows}, indent=1, ensure_ascii=False))
    print("->", out.relative_to(ROOT))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
