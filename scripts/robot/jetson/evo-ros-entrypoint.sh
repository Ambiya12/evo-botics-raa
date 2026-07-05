#!/usr/bin/env bash
set -euo pipefail

echo "EVO ROS container ready; legacy joystick autostart is disabled"

trap 'exit 0' TERM INT

while true; do
  sleep 3600 &
  wait "$!"
done
