#!/usr/bin/env bash
# Starts the SatQuery AI backend for the recorded demo, and waits until it answers.
#
#   scripts/demo/start_backend.sh          # cloud: deploy to Modal with one GPU container kept warm
#   scripts/demo/start_backend.sh local    # local: uvicorn on :8000 with the RTX 3070
#
# Cloud mode keeps a T4 running (and billing) until scripts/demo/stop_backend.sh scales it to zero.
# `modal deploy` ships backend/, configs/ and training/ from the working tree, uncommitted edits included.
set -euo pipefail
cd "$(dirname "$0")/../.."

say() { printf '\n\033[1;36m$ %s\033[0m\n' "$*"; }
URL=$(grep -E '^SATQUERY_CLOUD_URL=' .env | cut -d= -f2-)

if [[ "${1:-cloud}" == "local" ]]; then
  say ".venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
  exec .venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
fi

say "SATQUERY_MIN_CONTAINERS=1 modal deploy deploy/modal_app.py"
SATQUERY_MIN_CONTAINERS=1 .venv/bin/modal deploy deploy/modal_app.py

say "curl $URL/api/health"
for i in $(seq 1 40); do
  if body=$(curl -sf -m 20 "$URL/api/health"); then
    .venv/bin/python - "$body" <<'EOF'
import json, sys
h = json.loads(sys.argv[1]); m = h["models_available"]
print(f"status={h['status']}  device={h['device']}  database={'connected' if h['database_connected'] else 'DOWN'}  "
      f"models={sum(m.values())}/{len(m)}")
EOF
    printf '\033[1;32mBackend ready on the cloud GPU.\033[0m\n'
    exit 0
  fi
  printf '  waiting for the GPU container (%ss)\r' "$((i * 5))"; sleep 5
done
echo "backend did not answer within 200 s" >&2; exit 1
