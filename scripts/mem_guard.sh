#!/bin/bash
# Keep at least MIN_AVAIL_MB of RAM available system-wide by stopping the largest process in
# satquery.slice (training / downloads) when MemAvailable drops below it. Never touches
# anything outside that slice.
MIN_AVAIL_MB=${MIN_AVAIL_MB:-1024}
LOG=/home/natsu/dev/isro/results/training/mem_guard.log
CG=/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/satquery.slice

while true; do
  avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  if (( avail < MIN_AVAIL_MB )) && [[ -d $CG ]]; then
    pids=$(cat "$CG"/*/cgroup.procs "$CG"/cgroup.procs 2>/dev/null)
    if [[ -n $pids ]]; then
      victim=$(ps -o pid=,rss=,args= -p $(echo $pids | tr ' ' ',') | sort -k2 -nr | head -1)
      pid=$(echo "$victim" | awk '{print $1}')
      echo "$(date '+%F %T') avail=${avail}M < ${MIN_AVAIL_MB}M -> SIGTERM $victim" | cut -c1-240 >> "$LOG"; sync "$LOG"
      kill -TERM "$pid" 2>/dev/null
      sleep 5
      kill -0 "$pid" 2>/dev/null && kill -KILL "$pid"
      notify-send -u critical "SatQuery mem-guard" "RAM available ${avail} MB; stopped PID $pid" 2>/dev/null
    fi
  fi
  sleep 2
done
