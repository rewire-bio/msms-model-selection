#!/bin/bash
# Pause (SIGSTOP) and resume (SIGCONT) one training-queue process group on low disk.
# Usage: disk_guard.sh <runs-dir> <pgid> [pause_kib] [resume_kib]
# Only processes whose command line contains the workspace path are signalled.
# State in memory is preserved while paused; nothing is deleted.
set -u
RUNS="$1"; PGID="$2"
PAUSE_KIB="${3:-1572864}"    # 1.5 GiB
RESUME_KIB="${4:-2621440}"   # 2.5 GiB
WS="$(cd "$RUNS/.." && pwd)"
LOG="$RUNS/disk-guard.log"
STATE="$RUNS/DISK-GUARD-PAUSED.md"
paused=0

members() { ps -o pid=,pgid=,command= -ax | awk -v g="$PGID" '$2==g' | grep -F "$WS" | awk '{print $1}'; }
free_kib() { df -k "$RUNS" | tail -1 | awk '{print $4}'; }

echo "$(date -u +%FT%TZ) guard start pgid=$PGID pause<${PAUSE_KIB}KiB resume>${RESUME_KIB}KiB free=$(free_kib)KiB" >> "$LOG"
while true; do
  pids="$(members)"
  if [ -z "$pids" ]; then
    echo "$(date -u +%FT%TZ) no queue processes left; guard exits" >> "$LOG"; exit 0
  fi
  f=$(free_kib)
  if [ "$paused" -eq 0 ] && [ "$f" -lt "$PAUSE_KIB" ]; then
    kill -STOP $pids 2>/dev/null
    paused=1
    echo "$(date -u +%FT%TZ) PAUSED pids: $(echo $pids) free=${f}KiB" >> "$LOG"
    cat > "$STATE" <<EOF
# Training queue paused by disk guard

Paused at $(date -u +%FT%TZ) UTC with ${f} KiB free (threshold ${PAUSE_KIB} KiB).
Process group $PGID, pids: $(echo $pids)
Processes are stopped with SIGSTOP; model state is still in memory.

The guard resumes them automatically above ${RESUME_KIB} KiB free.
Manual resume after freeing space: kill -CONT $(echo $pids)
Do not start a second training run; do not delete checkpoints in runs/T0*.
EOF
  elif [ "$paused" -eq 1 ] && [ "$f" -gt "$RESUME_KIB" ]; then
    kill -CONT $pids 2>/dev/null
    paused=0
    echo "$(date -u +%FT%TZ) RESUMED pids: $(echo $pids) free=${f}KiB" >> "$LOG"
    mv "$STATE" "$RUNS/disk-guard-last-pause.md" 2>/dev/null
  fi
  sleep 30
done
