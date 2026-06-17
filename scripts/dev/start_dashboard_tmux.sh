#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="${ROOT_DIR}/reservationApp"
SESSION="${SESSION:-evo-dashboard}"
HOST="${DASHBOARD_HOST:-127.0.0.1}"
PORT="${DASHBOARD_PORT:-8000}"
VITE_HOST="${VITE_HOST:-127.0.0.1}"
ATTACH="${ATTACH:-1}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "[dashboard-tmux] tmux is not installed on this Mac."
  echo "[dashboard-tmux] Install it once with: brew install tmux"
  exit 1
fi

if [[ ! -d "$APP_DIR" ]]; then
  echo "[dashboard-tmux] Missing reservation app directory: ${APP_DIR}"
  exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[dashboard-tmux] Session '${SESSION}' already exists."
else
  echo "[dashboard-tmux] Starting '${SESSION}'"
  tmux new-session -d -s "$SESSION" -c "$APP_DIR" -n laravel \
    "php artisan serve --host=${HOST} --port=${PORT}"

  tmux new-window -t "$SESSION:" -c "$APP_DIR" -n vite \
    "npm run dev -- --host ${VITE_HOST}"

  tmux select-window -t "$SESSION:laravel"
  echo "[dashboard-tmux] Started '${SESSION}' with windows: laravel, vite"
fi

if [[ "$ATTACH" == "1" ]]; then
  echo "[dashboard-tmux] Attaching. Detach with: Ctrl-b then d"
  tmux attach-session -t "$SESSION"
else
  echo "[dashboard-tmux] Attach later with:"
  echo "  tmux attach-session -t ${SESSION}"
fi
