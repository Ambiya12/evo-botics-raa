#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/ops/compose/compose.simulation.yml"

echo "[sprint0] Root: $ROOT_DIR"
mkdir -p "$ROOT_DIR/evo_ws/src" "$ROOT_DIR/bags" "$ROOT_DIR/maps" "$ROOT_DIR/logs"

echo "[sprint0] Building and starting simulation container..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "[sprint0] Scaffolding ROS2 packages (idempotent)..."
docker compose -f "$COMPOSE_FILE" exec -T vnc-gui bash -lc '
set -euo pipefail
source /opt/ros/humble/setup.bash
cd /workspace/evo_ws/src

create_pkg_if_missing() {
  local pkg="$1"
  shift
  if [[ -d "$pkg" ]]; then
    echo "[skip] $pkg already exists"
  else
    echo "[create] $pkg"
    ros2 pkg create "$pkg" "$@"
  fi
}

create_pkg_if_missing evo_vision --build-type ament_python --dependencies rclpy sensor_msgs std_msgs cv_bridge
create_pkg_if_missing evo_voice --build-type ament_python --dependencies rclpy std_msgs
create_pkg_if_missing evo_navigation --build-type ament_python --dependencies rclpy geometry_msgs nav2_msgs action_msgs sensor_msgs tf2_ros
create_pkg_if_missing evo_backend --build-type ament_python --dependencies rclpy std_msgs
create_pkg_if_missing evo_interfaces --build-type ament_cmake
create_pkg_if_missing evo_bringup --build-type ament_cmake --dependencies nav2_bringup slam_toolbox gazebo_ros
'

echo "[sprint0] Building workspace..."
docker compose -f "$COMPOSE_FILE" exec -T vnc-gui bash -lc '
source /opt/ros/humble/setup.bash
cd /workspace/evo_ws
colcon build --symlink-install
'

echo "[sprint0] Done. Open desktop at http://localhost:6080"
