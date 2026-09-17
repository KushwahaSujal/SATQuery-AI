"""Runs the demo prompts against a SatQuery backend and records latency and answer sources (Q-022)."""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# Usage check - fail with short message if args missing
if len(sys.argv) < 2:
    print("Usage: cloud_smoke.py <base_url> [api_key]", file=sys.stderr)
    sys.exit(1)

BASE, KEY = sys.argv[1].rstrip("/"), (sys.argv[2] if len(sys.argv) > 2 else "")
H = {"Authorization": f"Bearer {KEY}"} if KEY else {}
R = Path("demo_resources")
CASES = [
    ("image", [R / "1_masking/airport_airplanes__P0173_0003.png"], "mask airplanes"),
    ("image", [R / "1_masking/suburb_white_houses_red_cars__P0897_0048.png"], "mask white houses"),
    ("image", [R / "1_masking/street_houses_trees_cars__P0725_0005.png"], "what is in this image?"),
    ("image", [R / "2_change_detection/levir_scene_100/before.png", R / "2_change_detection/levir_scene_100/after.png"],
     "has any new building been constructed?"),
    ("video", [R / "4_video/real_aerial_footage.mp4"], "find red car"),
]
rows = []
failed_any = False

# Create results/evaluations directory if missing
out_dir = Path("results/evaluations")
out_dir.mkdir(parents=True, exist_ok=True)

with httpx.Client(timeout=900, headers=H) as c:
    # Health check
    try:
        t = time.time()
        c.get(f"{BASE}/api/health").raise_for_status()
        rows.append({"case": "health", "secs": round(time.time() - t, 1)})
    except Exception as e:
        failed_any = True
        rows.append({"case": "health", "error": f"{type(e).__name__}: {str(e)}"})

    # Test cases
    for kind, files, q in CASES:
        try:
            t = time.time()
            if kind == "video":
                d = c.post(f"{BASE}/api/video/analyze", files={"file": (files[0].name, files[0].read_bytes(), "video/mp4")}, data={"query": q}).json()
                job, summary = d["job_id"], {"flags": [(f["start_timestamp"], f["end_timestamp"]) for f in d.get("flags", [])]}
            else:
                up = c.post(f"{BASE}/api/upload", files=[("files", (f.name, f.read_bytes())) for f in files]).json()
                d = c.post(f"{BASE}/api/analyze", json={"query": q, "image_filenames": [f.name for f in files], "request_id": up["request_id"]}).json()
                job, summary = d["request_id"], {"answer": d.get("answer"), "answer_source": d.get("answer_source"), "status": d.get("status")}
            z = c.get(f"{BASE}/api/results/{job}/download")
            rows.append({"case": q, "secs": round(time.time() - t, 1), "zip_status": z.status_code, "zip_bytes": len(z.content), **summary})
            print(json.dumps(rows[-1])[:300])
        except Exception as e:
            failed_any = True
            rows.append({"case": q, "error": f"{type(e).__name__}: {str(e)}"})
            print(f"ERROR: {q}: {type(e).__name__}: {str(e)}"[:300])

out = out_dir / f"cloud_smoke_{datetime.now():%Y%m%d_%H%M}.json"
out.write_text(json.dumps({"base": BASE, "rows": rows}, indent=1))
print("->", out)

# Exit with error code if any case failed
if failed_any:
    sys.exit(1)
