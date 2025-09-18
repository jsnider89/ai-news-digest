#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/run/uvicorn.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No uvicorn pid file found at $PID_FILE. Nothing to stop." >&2
  exit 0
fi

pid="$(<"$PID_FILE")"
if [[ -z "$pid" || ! -d "/proc/$pid" ]]; then
  echo "Stale pid file detected. Removing $PID_FILE." >&2
  rm -f "$PID_FILE"
  exit 0
fi

echo "Stopping uvicorn process $pid..."
kill "$pid"

for _ in {1..10}; do
  if [[ ! -d "/proc/$pid" ]]; then
    rm -f "$PID_FILE"
    echo "Uvicorn stopped."
    exit 0
  fi
  sleep 0.5
done

echo "Process $pid did not terminate gracefully; sending SIGKILL." >&2
kill -9 "$pid" || true
rm -f "$PID_FILE"
echo "Uvicorn force-stopped."
