#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/bags"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR}/session_${STAMP}"

mkdir -p "$OUT_DIR"

echo "[bag] Recording to ${OUT_FILE}.mcap"
echo "[bag] Press Ctrl+C to stop"

ros2 bag record \
  /camera/color/image_raw \
  /camera/depth/image_raw \
  /laser_1/scan \
  /laser_2/scan \
  /imu/data \
  /odom \
  --storage mcap \
  -o "$OUT_FILE"
