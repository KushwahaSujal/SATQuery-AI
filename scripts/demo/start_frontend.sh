#!/usr/bin/env bash
# Starts the SatQuery AI frontend (frontend-v2) for the recorded demo.
#
#   scripts/demo/start_frontend.sh          # cloud: production deploy to Vercel, prints the live URL
#   scripts/demo/start_frontend.sh local    # local: next dev on :3000 (the only port CORS allows)
#
# NEXT_PUBLIC_API_BASE_URL / NEXT_PUBLIC_API_KEY come from the Vercel project settings and are compiled
# in at build time, so the deployed site talks to the Modal backend, never to a local one.
set -euo pipefail
cd "$(dirname "$0")/../../frontend-v2"

say() { printf '\n\033[1;36m$ %s\033[0m\n' "$*"; }
SITE=https://satquery-ai-smoky.vercel.app

if [[ "${1:-cloud}" == "local" ]]; then
  say "cd frontend-v2 && npm run dev"
  exec npm run dev
fi

say "cd frontend-v2 && vercel deploy --prod"
vercel deploy --prod

say "curl -I $SITE"
curl -sI -m 30 "$SITE" | head -1
printf '\033[1;32mFrontend live at %s\033[0m\n' "$SITE"
