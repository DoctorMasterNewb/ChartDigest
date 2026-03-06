#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/.run-logs"
PID_DIR="$ROOT/.run-pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

if [[ -f "$BACKEND_PID_FILE" ]] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
  echo "Backend already running (pid $(cat "$BACKEND_PID_FILE"))"
else
  echo "Starting backend..."
  nohup "$ROOT/.venv/bin/uvicorn" app.main:app --app-dir "$ROOT/backend" --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
  echo $! > "$BACKEND_PID_FILE"
fi

if [[ -f "$FRONTEND_PID_FILE" ]] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
  echo "Frontend already running (pid $(cat "$FRONTEND_PID_FILE"))"
else
  echo "Starting frontend..."
  cd "$ROOT/frontend"
  nohup npm run dev -- --host 0.0.0.0 --port 5173 > "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$FRONTEND_PID_FILE"
fi

sleep 2

echo "\nServices launched:"
echo "- Backend:  http://127.0.0.1:8000/health"
echo "- Frontend: http://127.0.0.1:5173"
echo "\nLogs:"
echo "- $LOG_DIR/backend.log"
echo "- $LOG_DIR/frontend.log"
