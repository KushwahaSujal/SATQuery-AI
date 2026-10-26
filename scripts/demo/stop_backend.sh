#!/usr/bin/env bash
# Scales the Modal backend back to zero after recording. Without this the warm T4 bills around the clock.
set -euo pipefail
cd "$(dirname "$0")/../.."
printf '\n\033[1;36m$ modal deploy deploy/modal_app.py   # min_containers back to 0\033[0m\n'
.venv/bin/modal deploy deploy/modal_app.py
echo "Scaled to zero: the container sleeps after 5 min idle. Check credit at https://modal.com/settings/usage"
