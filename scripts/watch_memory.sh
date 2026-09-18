#!/bin/bash
# Live, read-only memory/GPU monitor. Run this yourself in any terminal:
#   ~/dev/isro/scripts/watch_memory.sh
# Ctrl+C to exit. Touches nothing, kills nothing.

while true; do
  clear
  echo "=== $(date '+%H:%M:%S') ==="
  echo
  free -h
  echo
  echo "--- GPU ---"
  nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu \
    --format=csv,noheader 2>/dev/null || echo "(no GPU or nvidia-smi unavailable)"
  echo
  echo "--- top 8 processes by RAM (RSS) ---"
  ps -eo pid,rss,pcpu,etime,args --sort=-rss | head -9 | \
    awk 'NR==1{print; next} {rss=$2/1024; printf "%-8s %7.0fMB %6s%% %10s  %s\n", $1, rss, $3, $4, substr($0, index($0,$5))}'
  echo
  echo "--- outside satquery.slice (NOT memory-capped — watch these) ---"
  for pid in $(ps -eo pid --sort=-rss --no-headers | head -30); do
    cg=$(cat /proc/$pid/cgroup 2>/dev/null | tail -1 | cut -d: -f3)
    [[ "$cg" == *satquery.slice* ]] && continue
    rss_kb=$(awk '/VmRSS/{print $2}' /proc/$pid/status 2>/dev/null)
    [[ -z "$rss_kb" || "$rss_kb" -lt 500000 ]] && continue  # only show >500MB
    comm=$(ps -p $pid -o args= 2>/dev/null | cut -c1-60)
    printf "  pid %-8s %6dMB  %s\n" "$pid" "$((rss_kb/1024))" "$comm"
  done
  echo
  echo "(Ctrl+C to exit)"
  sleep 3
done
