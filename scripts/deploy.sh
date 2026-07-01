#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/evo_ws/src"
JETSON_IP="${JETSON_IP:-}"
JETSON_USER="${JETSON_USER:-jetson}"
JETSON_WS="${JETSON_WS:-/home/${JETSON_USER}/evo_ws}"
JETSON_WS="${JETSON_WS%/}"
JETSON_TARGET="${JETSON_USER}@${JETSON_IP}"

remote_quote() {
  printf "%s" "$1" | sed "s/'/'\\\\''/g; 1s/^/'/; \$s/\$/'/"
}

if [[ -z "$JETSON_IP" ]]; then
  echo "Set JETSON_IP before running. Example: JETSON_IP=192.168.1.50 ./scripts/robot.sh setup"
  exit 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "[deploy] Missing workspace source directory: ${SRC_DIR}"
  exit 1
fi

REMOTE_SRC="${JETSON_WS}/src"
REMOTE_TMP="${JETSON_WS}/.deploy-src-tmp"
REMOTE_SRC_Q="$(remote_quote "$REMOTE_SRC")"
REMOTE_TMP_Q="$(remote_quote "$REMOTE_TMP")"

echo "[deploy] Preparing ${JETSON_TARGET}:${REMOTE_SRC}"
ssh "$JETSON_TARGET" "mkdir -p ${REMOTE_SRC_Q}"

RSYNC_ARGS=(
  -av
  --delete
  --exclude='build/'
  --exclude='install/'
  --exclude='log/'
  --exclude='__pycache__/'
  --exclude='*.pyc'
  --exclude='.DS_Store'
)

if [[ "${RSYNC_COMPRESS:-0}" == "1" ]]; then
  RSYNC_ARGS+=(-z)
fi

sync_with_tar() {
  echo "[deploy] Falling back to tar-over-ssh sync"
  COPYFILE_DISABLE=1 tar \
    --exclude='.DS_Store' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -C "$SRC_DIR" \
    -cf - . \
    | ssh "$JETSON_TARGET" \
      "rm -rf ${REMOTE_TMP_Q} && mkdir -p ${REMOTE_TMP_Q} && tar -C ${REMOTE_TMP_Q} -xf - && rm -rf ${REMOTE_SRC_Q} && mv ${REMOTE_TMP_Q} ${REMOTE_SRC_Q}"
}

echo "[deploy] Syncing local evo_ws/src to ${JETSON_TARGET}:${REMOTE_SRC}"
if ! rsync "${RSYNC_ARGS[@]}" "$SRC_DIR/" "${JETSON_TARGET}:${REMOTE_SRC}/"; then
  echo "[deploy] rsync failed; this can happen with macOS openrsync. Retrying without rsync."
  sync_with_tar
fi

echo "[deploy] Completed host sync. Docker copy/build is handled by ./scripts/robot.sh setup"
