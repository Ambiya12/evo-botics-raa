#!/usr/bin/env bash
set -euo pipefail

JETSON_IP="${JETSON_IP:-10.10.220.251}"
JETSON_USER="${JETSON_USER:-jetson}"
CONTAINER="${CONTAINER:-blissful_goldstine}"
SESSION="${SESSION:-evo-robot}"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
FASTDDS_BUILTIN_TRANSPORTS="${FASTDDS_BUILTIN_TRANSPORTS:-UDPv4}"
CAMERA_TOPIC="${CAMERA_TOPIC:-/camera/color/image_raw}"
DEPTH_TOPIC="${DEPTH_TOPIC:-/camera/depth/image_raw}"
CAMERA_PORT="${CAMERA_PORT:-8080}"
CAMERA_MAX_FPS="${CAMERA_MAX_FPS:-8.0}"
CAMERA_MAX_WIDTH="${CAMERA_MAX_WIDTH:-640}"
CAMERA_JPEG_QUALITY="${CAMERA_JPEG_QUALITY:-60}"
ATTACH="${ATTACH:-1}"

JETSON_TARGET="${JETSON_USER}@${JETSON_IP}"

remote_quote() {
  printf "%s" "$1" | sed "s/'/'\\\\''/g; 1s/^/'/; \$s/\$/'/"
}

remote_env=(
  "CONTAINER=$(remote_quote "$CONTAINER")"
  "SESSION=$(remote_quote "$SESSION")"
  "ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID")"
  "FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS")"
  "CAMERA_TOPIC=$(remote_quote "$CAMERA_TOPIC")"
  "DEPTH_TOPIC=$(remote_quote "$DEPTH_TOPIC")"
  "CAMERA_PORT=$(remote_quote "$CAMERA_PORT")"
  "CAMERA_MAX_FPS=$(remote_quote "$CAMERA_MAX_FPS")"
  "CAMERA_MAX_WIDTH=$(remote_quote "$CAMERA_MAX_WIDTH")"
  "CAMERA_JPEG_QUALITY=$(remote_quote "$CAMERA_JPEG_QUALITY")"
)

echo "[robot-tmux] Preparing ${SESSION} on ${JETSON_TARGET}"

ssh "$JETSON_TARGET" "${remote_env[*]} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "[robot-tmux] tmux is not installed on the Jetson."
  echo "[robot-tmux] Install it once with: sudo apt-get install -y tmux"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[robot-tmux] docker is not available on the Jetson."
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -Fxq "$CONTAINER"; then
  echo "[robot-tmux] Docker container '${CONTAINER}' is not running."
  echo "[robot-tmux] Running containers:"
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
  exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[robot-tmux] Session '${SESSION}' already exists."
  exit 0
fi

ros_setup='
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/evo_ws/install/setup.bash
export ROS_DOMAIN_ID='"$ROS_DOMAIN_ID"'
export FASTDDS_BUILTIN_TRANSPORTS='"$FASTDDS_BUILTIN_TRANSPORTS"'
'

docker_ros_cmd() {
  local ros_cmd="$1"
  local full_cmd="${ros_setup}
${ros_cmd}"

  printf "docker exec -it -e ROS_DOMAIN_ID=%q -e FASTDDS_BUILTIN_TRANSPORTS=%q -e DISPLAY=:0 %q bash -lc %q" \
    "$ROS_DOMAIN_ID" \
    "$FASTDDS_BUILTIN_TRANSPORTS" \
    "$CONTAINER" \
    "$full_cmd"
}

tmux new-session -d -s "$SESSION" -n bringup \
  "$(docker_ros_cmd 'ros2 launch slam_mapping bringup.launch.py')"

tmux new-window -t "$SESSION:" -n camera \
  "$(docker_ros_cmd 'ros2 launch slam_mapping app_camera.launch.py')"

tmux new-window -t "$SESSION:" -n vision \
  "$(docker_ros_cmd "ros2 launch evo_vision vision.launch.py camera_topic:=${CAMERA_TOPIC} depth_topic:=${DEPTH_TOPIC} qr_decoder_backend:=auto")"

tmux new-window -t "$SESSION:" -n web \
  "$(docker_ros_cmd "ros2 launch evo_web web_dashboard.launch.py port:=${CAMERA_PORT} camera_topic:=${CAMERA_TOPIC} camera_max_fps:=${CAMERA_MAX_FPS} camera_max_width:=${CAMERA_MAX_WIDTH} camera_jpeg_quality:=${CAMERA_JPEG_QUALITY}")"

tmux select-window -t "$SESSION:bringup"

echo "[robot-tmux] Started '${SESSION}' with windows: bringup, camera, vision, web"
REMOTE_SCRIPT

if [[ "$ATTACH" == "1" ]]; then
  echo "[robot-tmux] Attaching. Detach with: Ctrl-b then d"
  ssh -t "$JETSON_TARGET" "tmux attach-session -t $(remote_quote "$SESSION")"
else
  echo "[robot-tmux] Attach later with:"
  echo "  ssh ${JETSON_TARGET} -t tmux attach-session -t ${SESSION}"
fi
