#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/.run-logs"
PID_DIR="$ROOT/.run-pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_PORT="${CHARTDIGEST_BACKEND_PORT:-8010}"
FRONTEND_PORT="${CHARTDIGEST_FRONTEND_PORT:-5173}"
API_BASE="http://127.0.0.1:${BACKEND_PORT}/api"

read_pid () {
  local pid_file="$1"
  if [[ ! -s "$pid_file" ]]; then
    return 1
  fi

  local pid
  pid="$(tr -d '[:space:]' < "$pid_file")"
  if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
    return 1
  fi

  printf '%s' "$pid"
}

if backend_pid="$(read_pid "$BACKEND_PID_FILE")" && kill -0 "$backend_pid" 2>/dev/null; then
  echo "Backend already running (pid $backend_pid)"
else
  echo "Starting backend..."
  nohup "$ROOT/.venv/bin/uvicorn" app.main:app --app-dir "$ROOT/backend" --host 0.0.0.0 --port "$BACKEND_PORT" > "$LOG_DIR/backend.log" 2>&1 &
  echo $! > "$BACKEND_PID_FILE"
fi

if frontend_pid="$(read_pid "$FRONTEND_PID_FILE")" && kill -0 "$frontend_pid" 2>/dev/null; then
  echo "Frontend already running (pid $frontend_pid)"
else
  echo "Starting frontend..."
  cd "$ROOT/frontend"
  VITE_API_BASE="$API_BASE" nohup npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" --strictPort > "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$FRONTEND_PID_FILE"
fi

sleep 2

echo "\nServices launched:"
echo "- Backend:  http://127.0.0.1:${BACKEND_PORT}/health"
echo "- Frontend: http://127.0.0.1:${FRONTEND_PORT}"
echo "- Frontend API base: ${API_BASE}"
echo "\nLogs:"
echo "- $LOG_DIR/backend.log"
echo "- $LOG_DIR/frontend.log"
