#!/usr/bin/env bash
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${THIS_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${APP_ROOT}/.." && pwd)"

cd "$APP_ROOT"

if [ -f "${REPO_ROOT}/scripts/robot/config.sh" ]; then
  # Reuse JETSON_IP, APP_HOST, and APP_PORT saved by ./scripts/robot.sh config.
  # shellcheck disable=SC1091
  . "${REPO_ROOT}/scripts/robot/config.sh"
fi

: "${APP_SCHEME:=http}"
: "${APP_HOST:=}"
: "${APP_PORT:=8000}"
: "${VITE_PORT:=5173}"

detect_app_host() {
  if [ -n "${APP_HOST:-}" ]; then
    printf '%s\n' "$APP_HOST"
    return 0
  fi

  local host iface

  if [ -n "${JETSON_IP:-}" ]; then
    host="$(route -n get "$JETSON_IP" 2>/dev/null | awk '/source:/{print $2; exit}')"
    if [ -n "$host" ]; then
      printf '%s\n' "$host"
      return 0
    fi

    iface="$(route -n get "$JETSON_IP" 2>/dev/null | awk '/interface:/{print $2; exit}')"
    if [ -n "$iface" ]; then
      host="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
      if [ -n "$host" ]; then
        printf '%s\n' "$host"
        return 0
      fi
    fi

    host="$(ip route get "$JETSON_IP" 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="src") {print $(i+1); exit}}')"
    if [ -n "$host" ]; then
      printf '%s\n' "$host"
      return 0
    fi
  fi

  iface="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"
  if [ -n "$iface" ]; then
    host="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
    if [ -n "$host" ]; then
      printf '%s\n' "$host"
      return 0
    fi
  fi

  host="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^127\.' | head -n1 || true)"
  if [ -n "$host" ]; then
    printf '%s\n' "$host"
    return 0
  fi

  return 1
}

detected_host="$(detect_app_host 2>/dev/null || true)"
if [ -z "$detected_host" ]; then
  detected_host="127.0.0.1"
  echo "[dev] Could not detect the Mac/app IP. The app will only be local." >&2
  echo "[dev] Set APP_HOST or run: ../scripts/robot.sh config app-host <mac-ip>" >&2
fi

export APP_HOST="$detected_host"
export APP_PORT
export APP_URL="${APP_URL:-${APP_SCHEME}://${APP_HOST}:${APP_PORT}}"
export VITE_HMR_HOST="${VITE_HMR_HOST:-${APP_HOST}}"
export VITE_PORT

echo "[dev] App:    ${APP_URL}"
echo "[dev] Kiosk:  ${APP_SCHEME}://${APP_HOST}:${APP_PORT}/kiosk?scan=robot"
echo "[dev] Robot:  ${JETSON_IP:-<not configured>}"
echo

exec npx concurrently -c "#93c5fd,#c4b5fd,#fb7185,#fdba74" \
  "php artisan serve --host=0.0.0.0 --port=${APP_PORT}" \
  "php artisan queue:listen --tries=1 --timeout=0" \
  "php artisan pail --timeout=0" \
  "npm run dev -- --host 0.0.0.0 --port ${VITE_PORT}" \
  --names=server,queue,logs,vite --kill-others
