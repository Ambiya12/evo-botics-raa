#!/usr/bin/env bash
# Create, inspect, and save a ROS 2 occupancy map with Foxglove.
#
# Run from the repository root:
#   ./scripts/dev/foxglove_map.sh start
#   ./scripts/dev/foxglove_map.sh save my_map
#   ./scripts/dev/foxglove_map.sh stop
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ROBOT_DIR="${REPO_ROOT}/scripts/robot"
ROBOT_SCRIPT="${ROBOT_DIR}/robot.sh"

. "${ROBOT_DIR}/config.sh"
. "${ROBOT_DIR}/lib.sh"

FOXGLOVE_PORT="${FOXGLOVE_PORT:-8765}"
FOXGLOVE_SESSION="${FOXGLOVE_SESSION:-evo_foxglove}"
DOCKER_MAP_DIR="${DOCKER_MAP_DIR:-/root/maps}"
HOST_MAP_DIR="${HOST_MAP_DIR:-/home/${JETSON_USER}/maps}"

usage() {
  cat <<EOF
Usage: ./scripts/dev/foxglove_map.sh <command> [map-name]

Commands:
  start             Start bringup, camera, SLAM, web, and Foxglove Bridge
  save [map-name]   Save /map in Docker and copy it to the persistent Jetson host
  status            Show mapping sessions, required topics, and Foxglove port
  stop              Stop the mapping stack and Foxglove Bridge
  help              Show this help

Examples:
  ./scripts/dev/foxglove_map.sh start
  ./scripts/dev/foxglove_map.sh save ground_floor
  ./scripts/dev/foxglove_map.sh stop

Foxglove URL: ws://${JETSON_IP}:${FOXGLOVE_PORT}
EOF
}

require_container() {
  local container
  container="$(resolve_container)"
  if [[ -z "$container" ]]; then
    echo "[foxglove-map] No robot Docker container is running on ${JETSON_USER}@${JETSON_IP}." >&2
    echo "[foxglove-map] Check with: ssh ${JETSON_USER}@${JETSON_IP} 'docker ps'" >&2
    exit 1
  fi
  printf '%s\n' "$container"
}

require_foxglove_bridge() {
  local container="$1"
  if ! _ssh "docker exec ${container} bash -lc 'source /opt/ros/humble/setup.bash && ros2 pkg prefix foxglove_bridge >/dev/null 2>&1'"; then
    cat >&2 <<EOF
[foxglove-map] foxglove_bridge is not installed inside Docker.

Install it once:
  ssh ${JETSON_USER}@${JETSON_IP}
  docker exec -it ${container} bash -lc '
    apt-get update &&
    apt-get install -y ros-humble-foxglove-bridge
  '

Then run:
  ./scripts/dev/foxglove_map.sh start
EOF
    exit 1
  fi
}

start_foxglove_bridge() {
  local container="$1"
  if _ssh "tmux has-session -t ${FOXGLOVE_SESSION} 2>/dev/null"; then
    echo "[foxglove-map] ${FOXGLOVE_SESSION} is already running."
    return
  fi

  local ros_cmd docker_cmd
  ros_cmd="$(_ros_prelude); ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=${FOXGLOVE_PORT} address:=0.0.0.0"
  docker_cmd="$(printf 'docker exec -it -e ROS_DOMAIN_ID=%q -e FASTDDS_BUILTIN_TRANSPORTS=%q %q bash -lc %q' \
    "$ROS_DOMAIN_ID" "$FASTDDS_BUILTIN_TRANSPORTS" "$container" "$ros_cmd")"

  _ssh "tmux new-session -d -s ${FOXGLOVE_SESSION} $(remote_quote "$docker_cmd")"
  echo "[foxglove-map] Foxglove Bridge started at ws://${JETSON_IP}:${FOXGLOVE_PORT}"
}

cmd_start() {
  ensure_tmux
  local container
  container="$(require_container)"
  require_foxglove_bridge "$container"

  # Foxglove uses its native bridge on 8765. The admin dashboard independently
  # uses rosbridge on 9090, so both bridges intentionally run together.
  ROSBRIDGE=true "$ROBOT_SCRIPT" start map
  start_foxglove_bridge "$container"

  cat <<EOF

Mapping is ready.

1. Open Foxglove and connect with "Foxglove WebSocket":
   ws://${JETSON_IP}:${FOXGLOVE_PORT}
2. Add a 3D panel, set the display frame to "map", and enable /map and /scan_multi.
3. Or open the admin dashboard and connect its ROS port to:
   ws://${JETSON_IP}:9090
4. Drive with either interface, then save:
   ./scripts/dev/foxglove_map.sh save my_map

Inspect the stack:
  ./scripts/dev/foxglove_map.sh status
EOF
}

validate_map_name() {
  local map_name="$1"
  if [[ ! "$map_name" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; then
    echo "[foxglove-map] Invalid map name '${map_name}'." >&2
    echo "[foxglove-map] Use letters, numbers, underscores, or hyphens; do not include a path or extension." >&2
    exit 1
  fi
}

cmd_save() {
  local map_name="${1:-map_$(date +%Y%m%d_%H%M%S)}"
  validate_map_name "$map_name"

  local container
  container="$(require_container)"

  local remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
MAP_NAME=$(remote_quote "$map_name") \
DOCKER_MAP_DIR=$(remote_quote "$DOCKER_MAP_DIR") \
HOST_MAP_DIR=$(remote_quote "$HOST_MAP_DIR") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"

  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

docker_yaml="${DOCKER_MAP_DIR}/${MAP_NAME}.yaml"
docker_image="${DOCKER_MAP_DIR}/${MAP_NAME}.pgm"
host_yaml="${HOST_MAP_DIR}/${MAP_NAME}.yaml"
host_image="${HOST_MAP_DIR}/${MAP_NAME}.pgm"

if docker exec "$CONTAINER" test -e "$docker_yaml" || \
   docker exec "$CONTAINER" test -e "$docker_image" || \
   test -e "$host_yaml" || test -e "$host_image"; then
  echo "[foxglove-map] Refusing to overwrite the existing map '${MAP_NAME}'." >&2
  echo "[foxglove-map] Choose a new name." >&2
  exit 1
fi

if ! docker exec \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  "$CONTAINER" bash -lc \
  "${ROS_SETUP}; timeout 12 ros2 topic echo /map --once \
    --qos-durability transient_local \
    --qos-reliability reliable >/dev/null"; then
  echo "[foxglove-map] No /map message received. Is SLAM running and has the lidar produced a map?" >&2
  exit 1
fi

docker exec "$CONTAINER" mkdir -p "$DOCKER_MAP_DIR"
docker exec \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  "$CONTAINER" bash -lc \
  "${ROS_SETUP}; ros2 run nav2_map_server map_saver_cli -f '${DOCKER_MAP_DIR}/${MAP_NAME}'"

docker exec "$CONTAINER" test -s "$docker_yaml"
docker exec "$CONTAINER" test -s "$docker_image"

mkdir -p "$HOST_MAP_DIR"
docker cp "${CONTAINER}:${docker_yaml}" "$host_yaml"
docker cp "${CONTAINER}:${docker_image}" "$host_image"

echo "[foxglove-map] Saved in Docker:"
echo "  ${docker_yaml}"
echo "  ${docker_image}"
echo "[foxglove-map] Persistent backup on the Jetson host:"
echo "  ${host_yaml}"
echo "  ${host_image}"
REMOTE_SCRIPT

  echo
  echo "Navigate with this map later:"
  echo "  MAP_PATH=${DOCKER_MAP_DIR}/${map_name}.yaml ./scripts/robot/robot.sh start navigate"
}

cmd_status() {
  local container
  container="$(require_container)"

  echo "Target: ${JETSON_USER}@${JETSON_IP} (container: ${container})"
  echo "Foxglove: ws://${JETSON_IP}:${FOXGLOVE_PORT}"
  echo "Admin rosbridge: ws://${JETSON_IP}:9090"
  echo
  echo "Sessions:"
  _ssh "tmux ls 2>/dev/null | grep -E '^evo_(bringup|camera|slam|web|foxglove):' || echo '(mapping stack is not running)'"
  echo
  echo "ROS topics:"
  _ssh "docker exec ${container} bash -lc '$(_ros_prelude); ros2 topic list 2>/dev/null | grep -E \"^/(map|scan_multi|odom|tf|tf_static|cmd_vel_teleop)$\" || true'"
  echo
  echo "SLAM scan processing:"
  if _ssh "tmux capture-pane -p -S -80 -t evo_slam 2>/dev/null | grep -q 'queue is full'"; then
    echo "  ERROR: slam_toolbox is dropping scans because its TF queue is full."
    echo "  Deploy the current evo_navigation config and restart SLAM."
  else
    echo "  No recent TF queue overflow detected."
  fi
  echo
  if nc -z -w 3 "$JETSON_IP" "$FOXGLOVE_PORT" 2>/dev/null; then
    echo "Port ${FOXGLOVE_PORT} (Foxglove): open"
  else
    echo "Port ${FOXGLOVE_PORT} (Foxglove): closed or unreachable"
  fi
  if nc -z -w 3 "$JETSON_IP" 9090 2>/dev/null; then
    echo "Port 9090 (admin rosbridge): open"
  else
    echo "Port 9090 (admin rosbridge): closed or unreachable"
  fi
}

cmd_stop() {
  local container
  container="$(require_container)"
  _ssh "tmux kill-session -t ${FOXGLOVE_SESSION} 2>/dev/null || true"
  _ssh "docker exec ${container} bash -lc 'pkill -TERM -f \"[f]oxglove_bridge\" 2>/dev/null || true'"
  "$ROBOT_SCRIPT" stop map
  echo "[foxglove-map] Mapping stack stopped."
}

case "${1:-start}" in
  start)  cmd_start ;;
  save)   shift; cmd_save "${1:-}" ;;
  status) cmd_status ;;
  stop)   cmd_stop ;;
  help|-h|--help) usage ;;
  *)
    echo "[foxglove-map] Unknown command: $1" >&2
    usage >&2
    exit 1
    ;;
esac
