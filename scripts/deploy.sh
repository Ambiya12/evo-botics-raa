#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JETSON_IP="${JETSON_IP:-}"
JETSON_USER="${JETSON_USER:-evobotics}"
JETSON_WS="${JETSON_WS:-/home/${JETSON_USER}/evo_ws}"

if [[ -z "$JETSON_IP" ]]; then
  echo "Set JETSON_IP before running. Example: JETSON_IP=192.168.1.50 ./scripts/deploy.sh"
  exit 1
fi

echo "[deploy] Syncing workspace to ${JETSON_USER}@${JETSON_IP}:${JETSON_WS}"
rsync -avz --delete \
  --exclude='build/' --exclude='install/' --exclude='log/' --exclude='__pycache__/' \
  "$ROOT_DIR/evo_ws/src/" "${JETSON_USER}@${JETSON_IP}:${JETSON_WS}/src/"

echo "[deploy] Building on Jetson"
ssh "${JETSON_USER}@${JETSON_IP}" \
  "source /opt/ros/humble/setup.bash && cd ${JETSON_WS} && colcon build --symlink-install"

echo "[deploy] Completed"
