#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT/.run-pids"

stop_pid_file () {
  local f="$1"
  local name="$2"
  if [[ -f "$f" ]]; then
    local pid
    pid=$(cat "$f")
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping $name (pid $pid)"
      kill "$pid" || true
    else
      echo "$name not running"
    fi
    rm -f "$f"
  else
    echo "$name pid file not found"
  fi
}

stop_pid_file "$PID_DIR/backend.pid" "backend"
stop_pid_file "$PID_DIR/frontend.pid" "frontend"
