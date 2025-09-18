#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="$ROOT_DIR/.venv/bin"
PID_DIR="$ROOT_DIR/run"
PID_FILE="$PID_DIR/uvicorn.pid"
LOG_FILE="$PID_DIR/uvicorn.log"

if [[ ! -x "$VENV_BIN/uvicorn" ]];
then
  echo "uvicorn executable not found in $VENV_BIN. Activate the virtualenv and install dependencies first." >&2
  exit 1
fi

mkdir -p "$PID_DIR"

if [[ -f "$PID_FILE" ]];
then
  existing_pid="$(<"$PID_FILE")"
  if [[ -n "$existing_pid" && -d "/proc/$existing_pid" ]];
    then
      echo "Uvicorn appears to be running already (PID $existing_pid). Use scripts/stop_uvicorn.sh to stop it." >&2
      exit 1
    else
      rm -f "$PID_FILE"
    fi
fi

echo "Starting uvicorn on port 8002..."
nohup "$VENV_BIN/uvicorn" app.web.main:app --host 0.0.0.0 --port 8002 \
  >>"$LOG_FILE" 2>&1 &
uvicorn_pid=$!
echo "$uvicorn_pid" >"$PID_FILE"
echo "Uvicorn started with PID $uvicorn_pid (logs: $LOG_FILE)."
