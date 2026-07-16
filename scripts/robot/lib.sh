#!/usr/bin/env bash
# Shared helpers for SSH, Docker, tmux, and ROS services.

# --- SSH ---------------------------------------------------------------------

require_jetson_ip() {
  if [ -z "${JETSON_IP:-}" ]; then
    echo "Robot IP is not configured." >&2
    echo "Run: ./scripts/robot.sh config ip <jetson-ip>" >&2
    return 1
  fi
}

ssh_control_path() {
  # Keep this deliberately short: macOS limits Unix-domain socket paths.
  printf '/tmp/evo-ssh-%s-%s' \
    "$JETSON_USER" "${JETSON_IP//./-}"
}

_ssh() {
  local control_path
  require_jetson_ip || return 1
  control_path="$(ssh_control_path)"
  ssh \
    -o ConnectTimeout=8 \
    -o ConnectionAttempts=2 \
    -o ControlMaster=auto \
    -o "ControlPersist=${SSH_CONTROL_PERSIST_SEC}" \
    -o "ControlPath=${control_path}" \
    -o "ServerAliveInterval=${SSH_SERVER_ALIVE_INTERVAL_SEC}" \
    -o "ServerAliveCountMax=${SSH_SERVER_ALIVE_COUNT_MAX}" \
    "${JETSON_USER}@${JETSON_IP}" "$@"
}

_ssh_tty() {
  local control_path
  require_jetson_ip || return 1
  control_path="$(ssh_control_path)"
  ssh -t \
    -o ConnectTimeout=8 \
    -o ConnectionAttempts=2 \
    -o ControlMaster=auto \
    -o "ControlPersist=${SSH_CONTROL_PERSIST_SEC}" \
    -o "ControlPath=${control_path}" \
    -o "ServerAliveInterval=${SSH_SERVER_ALIVE_INTERVAL_SEC}" \
    -o "ServerAliveCountMax=${SSH_SERVER_ALIVE_COUNT_MAX}" \
    "${JETSON_USER}@${JETSON_IP}" "$@"
}

ensure_ssh_connection() {
  local control_path
  control_path="$(ssh_control_path)"
  echo "[ssh] establishing persistent connection to ${JETSON_USER}@${JETSON_IP}"
  if ! _ssh "true"; then
    echo "[ssh] Jetson is unreachable; no robot services were started." >&2
    return 1
  fi
  echo "[ssh] ready: multiplexed control connection ${control_path}"
}

# Preserve the difference between a normal remote false result and a broken
# SSH transport. Optional probes (for example tmux has-session) may legitimately
# return 1, but must never interpret SSH's 255 as "service not running".
_ssh_test() {
  local status
  _ssh "$@"
  status=$?
  if [ "$status" -eq 255 ]; then
    echo "[ssh] lost connection to ${JETSON_USER}@${JETSON_IP}; aborting startup" >&2
    return 2
  fi
  return "$status"
}

remote_quote() { printf "%s" "$1" | sed "s/'/'\\\\''/g; 1s/^/'/; \$s/\$/'/"; }

_ros_prelude() {
  printf '%s' \
"source /opt/ros/humble/setup.bash; \
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true; \
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true; \
source /root/evo_ws/install/setup.bash 2>/dev/null || true; \
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID}; \
export FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS}; \
export RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}"
}

# --- Docker container --------------------------------------------------------

resolve_container() {
  if _ssh "docker inspect -f '{{.State.Running}}' $(remote_quote "$CONTAINER") 2>/dev/null" |
      grep -qx true; then
    printf '%s\n' "$CONTAINER"
  fi
}

# --- evo_ws deployment cache -------------------------------------------------

# Copy the Jetson host-side deployment cache into Docker. The Mac remains the
# source of truth; the Jetson host copy is only the latest pushed cache.
seed_evo_ws_from_host() {
  local container="$1"
  if ! _ssh "test -d ${HOST_WS}/src"; then
    echo "[evo_ws] missing on Jetson host: ${HOST_WS}/src" >&2
    echo "Run from your Mac: ./scripts/robot.sh setup" >&2
    return 1
  fi
  echo "[evo_ws] seeding source from host: ${HOST_WS}/src -> ${container}:${DOCKER_WS}/src"
  _ssh "docker exec ${container} rm -rf ${DOCKER_WS}/src &&
    docker exec ${container} mkdir -p ${DOCKER_WS}/src &&
    docker cp ${HOST_WS}/src/. ${container}:${DOCKER_WS}/src"
}

# Ensure Docker has the latest workspace that was pushed from the Mac to the
# Jetson host cache. This never copies code from Docker back to the Mac.
ensure_evo_ws() {
  local container="$1"
  if _ssh "test -d ${HOST_WS}/src"; then
    seed_evo_ws_from_host "$container"
  else
    echo "[evo_ws] missing on the Jetson host deployment cache: ${HOST_WS}/src" >&2
    echo "Run from your Mac: ./scripts/robot.sh setup" >&2
    return 1
  fi
}

# --- Saved maps --------------------------------------------------------------

map_name_from_path() {
  local map_path="${1:-}"
  local name="${map_path##*/}"
  name="${name%.yaml}"
  name="${name%.pgm}"
  printf '%s\n' "${name}"
}

sync_map_from_host() {
  local container="$1" docker_yaml="$2"
  local map_name docker_image
  map_name="$(map_name_from_path "$docker_yaml")"
  docker_image="${docker_yaml%.yaml}.pgm"

  local remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
MAP_NAME=$(remote_quote "$map_name") \
HOST_MAP_DIR=$(remote_quote "$HOST_MAP_DIR") \
DOCKER_YAML=$(remote_quote "$docker_yaml") \
DOCKER_IMAGE=$(remote_quote "$docker_image")"

  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

host_yaml="${HOST_MAP_DIR}/${MAP_NAME}.yaml"
host_image="${HOST_MAP_DIR}/${MAP_NAME}.pgm"
docker_dir="$(dirname "$DOCKER_YAML")"

if [ ! -f "$host_yaml" ] || [ ! -f "$host_image" ]; then
  echo "[maps] missing saved map on Jetson host: ${MAP_NAME}" >&2
  echo "[maps] expected: ${host_yaml} and ${host_image}" >&2
  exit 1
fi

docker exec "$CONTAINER" mkdir -p "$docker_dir"
docker cp "$host_yaml" "${CONTAINER}:${DOCKER_YAML}"
docker cp "$host_image" "${CONTAINER}:${DOCKER_IMAGE}"

echo "[maps] synced ${MAP_NAME}"
echo "  Host:   ${host_yaml}"
echo "  Docker: ${DOCKER_YAML}"
REMOTE_SCRIPT
}

ensure_map_in_docker() {
  local container="$1" docker_yaml="$2"
  if _ssh "docker exec ${container} test -f $(remote_quote "$docker_yaml")"; then
    return 0
  fi

  if [ "$docker_yaml" = "$PACKAGED_MAP_PATH" ] || \
     [[ "$docker_yaml" == "${DOCKER_WS}/src/evo_navigation/maps/"*.yaml ]]; then
    echo "[maps] repository map is missing in Docker: ${docker_yaml}" >&2
    echo "[maps] run ./scripts/robot.sh setup to deploy the repository map" >&2
    return 1
  fi

  echo "[maps] ${docker_yaml} is missing in Docker. Syncing from ${HOST_MAP_DIR}."
  sync_map_from_host "$container" "$docker_yaml"
}

# --- MCU micro-ROS : santé / réveil -----------------------------------------

# Return success only after receiving a real MCU message. Topic discovery alone
# is insufficient because a publisher can remain visible while producing no data.
mcu_is_alive() {
  local container="$1"
  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc '
    source /opt/ros/humble/setup.bash 2>/dev/null
    timeout -k 1s 10s ros2 topic echo ${MCU_PROBE_TOPIC} --once \
      --qos-reliability best_effort >/dev/null 2>&1'" 2>/dev/null
}

# Use one continuous subscriber so DDS discovery is paid only once. Repeated
# short-lived subscribers can miss a slow publisher after agent recovery.
wait_for_mcu() {
  local container="$1"
  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc '
    source /opt/ros/humble/setup.bash 2>/dev/null
    timeout -k 1s 30s ros2 topic echo ${MCU_PROBE_TOPIC} --once \
      --qos-reliability best_effort >/dev/null 2>&1'" 2>/dev/null
}

wait_for_micro_ros_session() {
  local remote_env
  remote_env="AGENT_CONTAINER=$(remote_quote "$AGENT_CONTAINER")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail
for _ in $(seq 1 20); do
  logs="$(docker logs "$AGENT_CONTAINER" 2>&1 || true)"
  if grep -qE 'session established|create_client.*OK|Root\.session' <<<"$logs"; then
    exit 0
  fi
  sleep 1
done
exit 1
REMOTE_SCRIPT
}

report_mcu_diagnostics() {
  local container="$1" remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
AGENT_CONTAINER=$(remote_quote "$AGENT_CONTAINER") \
MICRO_ROS_SERVICE=$(remote_quote "$MICRO_ROS_SERVICE") \
MICRO_ROS_SERIAL_DEVICE=$(remote_quote "$MICRO_ROS_SERIAL_DEVICE") \
MCU_PROBE_TOPIC=$(remote_quote "$MCU_PROBE_TOPIC") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set +e

echo "[mcu] diagnostic snapshot:"
if test -e "$MICRO_ROS_SERIAL_DEVICE"; then
  echo "  serial device: present"
  ls -l "$MICRO_ROS_SERIAL_DEVICE" | sed 's/^/    /'
else
  echo "  serial device: MISSING (${MICRO_ROS_SERIAL_DEVICE})"
fi

service_state="$(systemctl is-active "$MICRO_ROS_SERVICE" 2>/dev/null || true)"
echo "  systemd service: ${service_state:-unknown}"

agent_running="$(docker inspect -f '{{.State.Running}}' "$AGENT_CONTAINER" 2>/dev/null || true)"
echo "  agent container: ${agent_running:-missing} (${AGENT_CONTAINER})"

echo "  recent agent log:"
docker logs --tail 20 "$AGENT_CONTAINER" 2>&1 | sed 's/^/    /' ||
  echo "    unavailable"

echo "  ROS topic endpoint:"
docker exec \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  "$CONTAINER" bash -lc \
  "source /opt/ros/humble/setup.bash 2>/dev/null; ros2 topic info '$MCU_PROBE_TOPIC' -v 2>&1" |
  sed 's/^/    /' || echo "    unavailable"
REMOTE_SCRIPT
}

restart_micro_ros_service() {
  echo "[mcu] restarting ${MICRO_ROS_SERVICE} through systemd"
  if ! _ssh "sudo -n systemctl restart $(remote_quote "$MICRO_ROS_SERVICE")"; then
    echo "Unable to restart ${MICRO_ROS_SERVICE} non-interactively." >&2
    echo "Run on the Jetson:" >&2
    echo "  sudo systemctl restart ${MICRO_ROS_SERVICE}" >&2
    return 1
  fi
}

disable_legacy_joystick_control() {
  local container="$1"
  echo "[safety] disabling legacy joystick nodes that publish directly to /cmd_vel"
  _ssh "docker exec ${container} bash -lc '
    pkill -TERM -f \"[y]ahboom_joy_M3Pro\" 2>/dev/null || true
    pkill -TERM -f \"[j]oy_node\" 2>/dev/null || true
  '"
}

ensure_tmux() {
  if ! _ssh "command -v tmux >/dev/null 2>&1"; then
    echo "tmux is not installed on the Jetson. Install it once:" >&2
    echo "  ssh ${JETSON_USER}@${JETSON_IP} 'sudo apt-get install -y tmux'" >&2
    exit 1
  fi
}

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

resolve_app_url() {
  local path="$1" override="${2:-}" host
  if [ -n "$override" ]; then
    printf '%s\n' "$override"
    return 0
  fi

  if ! host="$(detect_app_host)" || [ -z "$host" ]; then
    echo "[app] could not detect the Mac/app IP reachable from the Jetson." >&2
    echo "[app] Set it once with: ./scripts/robot.sh config app-host <mac-ip>" >&2
    return 1
  fi

  [[ "$path" == /* ]] || path="/${path}"
  printf '%s://%s:%s%s\n' "$APP_SCHEME" "$host" "$APP_PORT" "$path"
}

resolve_kiosk_url() {
  resolve_app_url "$KIOSK_PATH" "$KIOSK_URL"
}

resolve_reception_validation_url() {
  resolve_app_url "$RECEPTION_VALIDATION_PATH" "$RECEPTION_VALIDATION_URL"
}

open_kiosk_browser() {
  local url="${1:-}"
  [ -n "$url" ] || url="$(resolve_kiosk_url)" || return 1

  local remote_env
  remote_env="KIOSK_URL=$(remote_quote "$url") \
KIOSK_DISPLAY=$(remote_quote "$KIOSK_DISPLAY") \
KIOSK_SESSION=$(remote_quote "$KIOSK_SESSION")"

  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

if tmux has-session -t "$KIOSK_SESSION" 2>/dev/null; then
  tmux kill-session -t "$KIOSK_SESSION" 2>/dev/null || true
fi

browser=""
for candidate in chromium-browser chromium google-chrome firefox; do
  if command -v "$candidate" >/dev/null 2>&1; then
    browser="$candidate"
    break
  fi
done

if [ -z "$browser" ]; then
  if command -v xdg-open >/dev/null 2>&1; then
    browser="xdg-open"
  else
    echo "[kiosk] no browser found on the Jetson host" >&2
    echo "[kiosk] install chromium-browser, chromium, google-chrome, firefox, or xdg-utils" >&2
    exit 1
  fi
fi

case "$browser" in
  chromium-browser|chromium|google-chrome)
    cmd=$(printf 'DISPLAY=%q %q --kiosk --noerrdialogs --disable-infobars --check-for-update-interval=31536000 %q' \
      "$KIOSK_DISPLAY" "$browser" "$KIOSK_URL")
    ;;
  firefox)
    cmd=$(printf 'DISPLAY=%q %q --kiosk %q' "$KIOSK_DISPLAY" "$browser" "$KIOSK_URL")
    ;;
  *)
    cmd=$(printf 'DISPLAY=%q %q %q' "$KIOSK_DISPLAY" "$browser" "$KIOSK_URL")
    ;;
esac

tmux new-session -d -s "$KIOSK_SESSION" "$cmd"
echo "[kiosk] opened ${KIOSK_URL} on display ${KIOSK_DISPLAY} with ${browser}"
REMOTE_SCRIPT
}

stop_kiosk_browser() {
  _ssh "tmux kill-session -t ${KIOSK_SESSION} 2>/dev/null || true"
  echo "[kiosk] stopped"
}

prepare_robot_display() {
  local container="$1" remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
ROBOT_DISPLAY=$(remote_quote "$KIOSK_DISPLAY")"

  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

display_number="${ROBOT_DISPLAY#:}"
display_number="${display_number%%.*}"
x11_socket="/tmp/.X11-unix/X${display_number}"

if [ ! -S "$x11_socket" ]; then
  echo "[rviz] robot display ${ROBOT_DISPLAY} is unavailable: ${x11_socket} does not exist" >&2
  echo "[rviz] set KIOSK_DISPLAY to the active Jetson display in scripts/robot/config.local.sh" >&2
  exit 1
fi

if ! docker exec "$CONTAINER" test -S "$x11_socket"; then
  echo "[rviz] ${x11_socket} is not mounted inside ${CONTAINER}" >&2
  echo "[rviz] recreate the container with: -v /tmp/.X11-unix:/tmp/.X11-unix" >&2
  exit 1
fi

if ! DISPLAY="$ROBOT_DISPLAY" xhost +SI:localuser:root >/dev/null; then
  echo "[rviz] could not authorize the container root user on display ${ROBOT_DISPLAY}" >&2
  echo "[rviz] run this in the Jetson desktop session: xhost +SI:localuser:root" >&2
  exit 1
fi

if ! docker exec "$CONTAINER" bash -lc \
  'source /opt/ros/humble/setup.bash && command -v rviz2 >/dev/null 2>&1'; then
  echo "[rviz] rviz2 is not installed inside ${CONTAINER}" >&2
  echo "[rviz] rebuild and provision the robot image from scripts/robot/image/Dockerfile" >&2
  echo "[rviz] the maintained image installs the required ros-humble-rviz2 package" >&2
  exit 1
fi

echo "[rviz] display ${ROBOT_DISPLAY} is available to ${CONTAINER}"
REMOTE_SCRIPT
}

wait_for_rviz() {
  local container="$1" attempt
  for attempt in $(seq 1 10); do
    if _ssh "docker exec ${container} pgrep -f '[r]viz2' >/dev/null"; then
      echo "[rviz] process is running on display ${KIOSK_DISPLAY}"
      return 0
    fi
    sleep 1
  done

  echo "[rviz] rviz2 did not stay running." >&2
  echo "[rviz] inspect the failure with: ./scripts/robot.sh logs slam" >&2
  return 1
}

qr_decoder_available() {
  local container="$1" probe
  probe='python3 -c "from pyzbar.pyzbar import decode; print(\"pyzbar/zbar ok\")"'
  _ssh "docker exec ${container} bash -lc $(remote_quote "$probe")"
}

ensure_qr_decoder_in_docker() {
  local container="$1"
  if qr_decoder_available "$container" >/dev/null 2>&1; then
    echo "[dependencies] QR decoder ready in ${container}"
    return 0
  fi

  echo "QR decoding dependencies are missing from ${container}." >&2
  echo "Rebuild/provision the EVO robot image; runtime package installation is disabled." >&2
  return 1
}

require_foxglove_bridge() {
  local container="$1"
  if ! _ssh "docker exec ${container} bash -lc 'source /opt/ros/humble/setup.bash && ros2 pkg prefix foxglove_bridge >/dev/null 2>&1'"; then
    cat >&2 <<EOF
foxglove_bridge is not installed inside Docker.

Rebuild/provision the EVO robot image with ros-humble-foxglove-bridge.
EOF
    exit 1
  fi
}

start_foxglove_bridge() {
  local container="$1"
  if _ssh "tmux has-session -t ${FOXGLOVE_SESSION} 2>/dev/null"; then
    echo "[foxglove] already running: ws://${JETSON_IP}:${FOXGLOVE_PORT}"
    return
  fi

  local ros_cmd docker_cmd
  ros_cmd="$(_ros_prelude); ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=${FOXGLOVE_PORT} address:=0.0.0.0"
  docker_cmd="$(printf 'docker exec -it -e ROS_DOMAIN_ID=%q -e FASTDDS_BUILTIN_TRANSPORTS=%q %q bash -lc %q' \
    "$ROS_DOMAIN_ID" "$FASTDDS_BUILTIN_TRANSPORTS" "$container" "$ros_cmd")"

  _ssh "tmux new-session -d -s ${FOXGLOVE_SESSION} $(remote_quote "$docker_cmd")"
  echo "[foxglove] ws://${JETSON_IP}:${FOXGLOVE_PORT}"
}

save_slam_map() {
  local container="$1" map_name="$2"
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
  echo "Map already exists: ${MAP_NAME}" >&2
  exit 1
fi

if ! docker exec \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  "$CONTAINER" bash -lc \
  "${ROS_SETUP}; timeout -k 1s 12s ros2 topic echo /map --once \
    --qos-durability transient_local \
    --qos-reliability reliable >/dev/null"; then
  echo "No /map message received. Is SLAM running?" >&2
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

echo "Saved map:"
echo "  Docker: ${docker_yaml}"
echo "  Host:   ${host_yaml}"
REMOTE_SCRIPT
}

# Snapshot lecture seule de l'état du Jetson (specs + charge + RAM + top process).
# Aucune écriture : sûr même sur une stack ROS lancée par un tiers.
jetson_health() {
  _ssh 'bash -lc "
    echo ===== MODELE / OS =====;
    tr -d \"\0\" < /proc/device-tree/model 2>/dev/null; echo;
    . /etc/os-release 2>/dev/null && echo \"OS: \$PRETTY_NAME\";
    uname -r | sed \"s/^/Kernel: /\";
    echo; echo ===== CPU =====;
    lscpu 2>/dev/null | grep -E \"^Architecture|^Model name|^CPU\(s\)|^CPU max\";
    echo; echo ===== RAM / SWAP =====; free -h;
    echo; echo ===== DISQUE / =====; df -h / 2>/dev/null;
    echo; echo ===== CHARGE / UPTIME =====; uptime;
    echo; echo ===== TOP PROCESSUS =====;
    top -bn1 2>/dev/null | sed -n \"1,3p;7,15p\";
    echo; echo ===== TEMPERATURES =====;
    for z in /sys/devices/virtual/thermal/thermal_zone*; do
      t=\$(cat \$z/temp 2>/dev/null); ty=\$(cat \$z/type 2>/dev/null);
      [ -n \"\$t\" ] && echo \"\$ty: \$((t/1000)) C\";
    done 2>/dev/null;
    echo; echo ===== CONTENEURS DOCKER =====;
    docker ps --format \"table {{.Names}}\t{{.Image}}\t{{.Status}}\" 2>/dev/null;
  "'
}

# --- Définition des services -------------------------------------------------

# Commande ROS lancée pour chaque service.
service_cmd() {
  case "$1" in
    bringup) echo "ros2 launch slam_mapping bringup.launch.py" ;;
    camera)  echo "ros2 launch slam_mapping app_camera.launch.py" ;;
    vision)
      local vision_cmd
      vision_cmd="ros2 launch evo_vision vision.launch.py camera_topic:=${CAMERA_TOPIC} depth_topic:=${DEPTH_TOPIC} qr_decoder_backend:=auto enable_object_detection:=${PERSON_DETECTION_ENABLED}"
      if [ "$PERSON_DETECTION_ENABLED" = "true" ]; then
        vision_cmd="${vision_cmd} person_model_path:=${PERSON_DETECTION_MODEL_PATH} person_confidence_threshold:=${PERSON_DETECTION_CONFIDENCE} person_nms_threshold:=${PERSON_DETECTION_NMS} person_max_fps:=${PERSON_DETECTION_MAX_FPS}"
      fi
      echo "$vision_cmd"
      ;;
    reception)
      local validation_url
      validation_url="$(resolve_reception_validation_url)" || return 1
      echo "ros2 launch evo_reception reception.launch.py validation_url:=${validation_url}"
      ;;
    voice)
      local voice_cmd
      voice_cmd="ros2 launch evo_voice reception_voice.launch.py stt_device:=${STT_DEVICE} stt_compute_type:=${STT_COMPUTE_TYPE} language:=${VOICE_LANGUAGE} microphone_device:=${MICROPHONE_DEVICE} phrase_time_limit_sec:=${STT_PHRASE_TIME_LIMIT_SEC} pause_threshold_sec:=${STT_PAUSE_THRESHOLD_SEC} non_speaking_duration_sec:=${STT_NON_SPEAKING_DURATION_SEC}"
      if [ -n "$PIPER_MODEL_PATH" ]; then
        voice_cmd="${voice_cmd} piper_model_path:=${PIPER_MODEL_PATH}"
      fi
      if [ -n "$STT_MODEL_PATH" ]; then
        voice_cmd="${voice_cmd} stt_model_path:=${STT_MODEL_PATH}"
      fi
      if [ -n "$AUDIO_OUTPUT_DEVICE" ]; then
        voice_cmd="${voice_cmd} audio_output_device:=${AUDIO_OUTPUT_DEVICE}"
      fi
      echo "$voice_cmd"
      ;;
    dialogue)
      echo "ros2 launch evo_reception dialogue_manager.launch.py presence_greeting_fallback_sec:=${PRESENCE_GREETING_FALLBACK_SEC} intent_timeout_sec:=${INTENT_TIMEOUT_SEC} qr_inactivity_timeout_sec:=${QR_INACTIVITY_TIMEOUT_SEC} allowed_destination_ids_csv:=${RECEPTION_ALLOWED_DESTINATION_IDS} automatic_return_enabled:=${AUTOMATIC_RETURN_ENABLED}"
      ;;
    reception_nav)
      echo "ros2 launch evo_navigation orchestrator.launch.py waypoint_config_path:=${RECEPTION_WAYPOINT_CONFIG_PATH} allow_real_navigation:=true navigation_timeout_sec:=${REAL_NAVIGATION_TIMEOUT_SEC} localization_timeout_sec:=${REAL_LOCALIZATION_TIMEOUT_SEC} max_localization_xy_variance:=${REAL_MAX_LOCALIZATION_XY_VARIANCE}"
      ;;
    approach)
      echo "ros2 launch evo_vision human_approach.launch.py min_confidence:=${APPROACH_MIN_CONFIDENCE} min_distance_m:=${APPROACH_MIN_DISTANCE_M} max_distance_m:=${APPROACH_MAX_DISTANCE_M} zone_min_x:=${APPROACH_ZONE_MIN_X} zone_max_x:=${APPROACH_ZONE_MAX_X} zone_min_y:=${APPROACH_ZONE_MIN_Y} zone_max_y:=${APPROACH_ZONE_MAX_Y} debounce_frames:=${APPROACH_DEBOUNCE_FRAMES} cooldown_sec:=${APPROACH_COOLDOWN_SEC} absence_reset_sec:=${APPROACH_ABSENCE_RESET_SEC}"
      ;;
    web)     echo "ros2 launch evo_web web_dashboard.launch.py rosbridge:=${ROSBRIDGE} rosbridge_port:=${ROSBRIDGE_PORT} http_port:=${CAMERA_PORT} camera_topic:=${CAMERA_TOPIC} camera_max_fps:=${CAMERA_MAX_FPS} camera_max_width:=${CAMERA_MAX_WIDTH} camera_jpeg_quality:=${CAMERA_JPEG_QUALITY} arm_input_topic:=${ARM_INPUT_TOPIC} arm_output_topic:=${ARM_OUTPUT_TOPIC}" ;;
    teleop)  echo "ros2 launch evo_navigation teleop.launch.py" ;;
    slam)    echo "ros2 launch evo_navigation slam_online.launch.py rviz:=${SLAM_RVIZ:-false} use_collision_monitor:=${SLAM_USE_COLLISION_MONITOR}" ;;
    nav)     echo "ros2 launch evo_navigation navigation.launch.py map:=${MAP_PATH} rviz:=false use_collision_monitor:=${NAV_USE_COLLISION_MONITOR}" ;;
    *)       return 1 ;;
  esac
}

# Motif pkill pour arrêter proprement un service à l'intérieur du conteneur.
service_pattern() {
  case "$1" in
    bringup) echo "bringup.launch.py" ;;
    camera)  echo "app_camera.launch.py" ;;
    vision)  echo "vision.launch.py" ;;
    reception) echo "reception.launch.py" ;;
    voice) echo "reception_voice.launch.py" ;;
    dialogue) echo "dialogue_manager.launch.py" ;;
    reception_nav) echo "orchestrator.launch.py" ;;
    approach) echo "human_approach.launch.py" ;;
    web)     echo "web_dashboard.launch.py" ;;
    teleop)  echo "teleop.launch.py" ;;
    slam)    echo "slam_online.launch.py" ;;
    nav)     echo "navigation.launch.py" ;;
    *)       return 1 ;;
  esac
}

ALL_SERVICES="bringup camera vision reception voice dialogue reception_nav approach web teleop slam nav"

# Profils = raccourcis ; un nom inconnu est renvoyé tel quel (service unique).
expand_profile() {
  case "$1" in
    map)      echo "bringup camera slam web"   ;;
    navigate) echo "bringup camera web nav"    ;;
    base)     echo "bringup camera vision web teleop" ;;   # base + caméra + vision + web
    reception) echo "bringup camera vision reception web teleop" ;;
    camera-qr) echo "camera vision reception web" ;;
    demo) echo "bringup camera nav voice dialogue vision reception approach reception_nav web" ;;
    # cmd_start preloads voice before bringup for this profile. Keep voice in
    # the list so profile cleanup and failure handling still own the service.
    # vision starts early so detection is warm before the operator finishes the
    # AMCL pose; dialogue starts last so it never waits on a missing publisher.
    # approach is intentionally excluded -- it is kept available for a future
    # "approach the visitor" behaviour but is not launched for the greeting demo.
    demo-navigation) echo "bringup voice camera web vision nav reception_nav reception dialogue" ;;
    kiosk)    echo "bringup camera vision reception web teleop" ;;
    launch)   echo "bringup camera nav vision reception web" ;;
    *)        echo "$1"                         ;;
  esac
}

validate_voice_config() {
  local container="$1"
  if [ -z "$PIPER_MODEL_PATH" ] || \
     ! _ssh "docker exec ${container} test -f $(remote_quote "$PIPER_MODEL_PATH")"; then
    echo "[voice] Piper model is missing in ${container}: ${PIPER_MODEL_PATH:-<not configured>}" >&2
    return 1
  fi
  if [ -z "$STT_MODEL_PATH" ] || \
     ! _ssh "docker exec ${container} test -s $(remote_quote "${STT_MODEL_PATH}/model.bin")"; then
    echo "[voice] Faster-Whisper model.bin is missing in ${container}: ${STT_MODEL_PATH:-<not configured>}" >&2
    return 1
  fi
  if [ "$WEBRTC_MIC_ENABLED" = "true" ] && [ "$MICROPHONE_DEVICE" != "-1" ]; then
    echo "[voice] WebRTC capture must use MICROPHONE_DEVICE=-1 (the stable PulseAudio default); numeric PyAudio indices change across restarts." >&2
    return 1
  fi
}

clean_stale_fastdds_shm() {
  local container="$1"
  _ssh "docker exec ${container} bash -lc '
    removed=0
    for lock in /dev/shm/fastrtps_*_el; do
      [ -e \"\$lock\" ] || continue
      if flock -n \"\$lock\" true; then
        segment=\${lock%_el}
        rm -f -- \"\$segment\" \"\$lock\"
        removed=\$((removed + 1))
      fi
    done
    if [ \"\$removed\" -gt 0 ]; then
      echo \"[voice] removed \$removed stale Fast DDS shared-memory segments\"
    fi
    usage=\$(df -P /dev/shm | awk \"NR == 2 {print \\\$5}\")
    case \"\$usage\" in
      9[0-9]%|100%)
        echo \"[voice] /dev/shm remains critically full after safe cleanup: \$usage\" >&2
        exit 1
        ;;
    esac
  '"
}

wait_for_voice_ready() {
  local container="$1" remote_env
  echo "[voice] waiting for real microphone and Piper backends"
  remote_env="CONTAINER=$(remote_quote "$container") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
RMW_IMPLEMENTATION=$(remote_quote "$RMW_IMPLEMENTATION") \
DOCKER_WS=$(remote_quote "$DOCKER_WS") \
AUDIO_OUTPUT_DEVICE=$(remote_quote "$AUDIO_OUTPUT_DEVICE") \
VOICE_STARTUP_TIMEOUT_SEC=$(remote_quote "$VOICE_STARTUP_TIMEOUT_SEC") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail
total_started=$SECONDS

run_ros() {
  local ros_setup="${ROS_SETUP//\'/}"
  docker exec \
    -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
    -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
    -e RMW_IMPLEMENTATION="$RMW_IMPLEMENTATION" \
    "$CONTAINER" bash -lc "${ros_setup}; $1"
}

phase_started=$SECONDS
if ! docker exec "$CONTAINER" test -s "$DOCKER_WS/install/.evo-source-revision"; then
  echo "[voice] missing build revision marker; run ./scripts/robot.sh setup" >&2
  exit 1
fi
current_revision="$(
  docker exec "$CONTAINER" bash -lc \
    "cd '$DOCKER_WS' && find src -type d \\( -name __pycache__ -o -name .pytest_cache \\) -prune -o -type f ! -name '*.pyc' -print0 | sort -z | xargs -0 sha256sum | sha256sum"
)"
built_revision="$(docker exec "$CONTAINER" cat "$DOCKER_WS/install/.evo-source-revision")"
if [ "$current_revision" != "$built_revision" ]; then
  echo "[voice] source differs from the installed workspace; run ./scripts/robot.sh setup" >&2
  exit 1
fi
echo "[voice] build revision verified in $((SECONDS - phase_started))s"

phase_started=$SECONDS
default_sink="$(pactl info | awk -F': ' '/^Default Sink:/{print $2}')"
default_source="$(pactl info | awk -F': ' '/^Default Source:/{print $2}')"
if [ -z "$default_sink" ] || [ -z "$default_source" ]; then
  echo "[voice] PulseAudio default sink/source is unavailable on the Jetson host" >&2
  exit 1
fi
if [[ "$AUDIO_OUTPUT_DEVICE" == pulse/* ]]; then
  requested_sink="${AUDIO_OUTPUT_DEVICE#pulse/}"
  if ! pactl list short sinks | awk -v sink="$requested_sink" '$2 == sink { found=1 } END { exit !found }'; then
    echo "[voice] configured PulseAudio sink is unavailable: ${requested_sink}" >&2
    exit 1
  fi
fi
audio_devices="$(docker exec "$CONTAINER" mpv --no-config --audio-device=help 2>&1)"
if [ -n "$AUDIO_OUTPUT_DEVICE" ] && ! grep -Fq "'${AUDIO_OUTPUT_DEVICE}'" <<<"$audio_devices"; then
  echo "[voice] mpv cannot see configured audio device: ${AUDIO_OUTPUT_DEVICE}" >&2
  exit 1
fi
if ! grep -q "'pulse/" <<<"$audio_devices"; then
  echo "[voice] container mpv cannot reach the host PulseAudio server" >&2
  exit 1
fi
echo "[voice] PulseAudio and mpv verified in $((SECONDS - phase_started))s"

phase_started=$SECONDS
if ! run_ros \
  "timeout -k 2s $((VOICE_STARTUP_TIMEOUT_SEC + 5))s ${DOCKER_WS}/install/evo_voice/lib/evo_voice/voice_readiness_checker --ros-args -p timeout_sec:=${VOICE_STARTUP_TIMEOUT_SEC}.0"; then
  echo "[voice] readiness failed after ${VOICE_STARTUP_TIMEOUT_SEC}s; inspect ./scripts/robot.sh logs voice" >&2
  exit 1
fi
echo "[voice] speech backends verified in $((SECONDS - phase_started))s"

echo "[voice] ready after $((SECONDS - total_started))s: Piper, Faster-Whisper, microphone, PulseAudio, and build revision verified"
REMOTE_SCRIPT
}

ensure_webrtc_microphone() {
  [ "$WEBRTC_MIC_ENABLED" = "true" ] || return 0
  if [ -z "$WEBRTC_MIC_SOURCE_MASTER" ] || \
     [ -z "$WEBRTC_MIC_SOURCE_NAME" ]; then
    echo "[voice] WebRTC microphone source names must be configured." >&2
    return 1
  fi

  local master source_name source_volume
  master="$(remote_quote "$WEBRTC_MIC_SOURCE_MASTER")"
  source_name="$(remote_quote "$WEBRTC_MIC_SOURCE_NAME")"
  source_volume="$(remote_quote "$WEBRTC_MIC_SOURCE_VOLUME")"
  _ssh "MASTER=${master} SOURCE_NAME=${source_name} SOURCE_VOLUME=${source_volume} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

if ! pactl list short sources | awk -v source="$MASTER" '$2 == source { found=1 } END { exit !found }'; then
  echo "[voice] PulseAudio source is missing: ${MASTER}" >&2
  exit 1
fi

pactl set-source-volume "$MASTER" "$SOURCE_VOLUME"
if ! pactl list short sources | awk -v source="$SOURCE_NAME" '$2 == source { found=1 } END { exit !found }'; then
  pactl load-module module-echo-cancel \
    aec_method=webrtc \
    source_master="$MASTER" \
    source_name="$SOURCE_NAME" >/dev/null
fi
pactl set-default-source "$SOURCE_NAME"

default_source="$(pactl info | awk -F': ' '/Default Source:/{print $2}')"
if [ "$default_source" != "$SOURCE_NAME" ]; then
  echo "[voice] Failed to select WebRTC source: ${SOURCE_NAME}" >&2
  exit 1
fi
echo "[voice] WebRTC microphone ready: ${SOURCE_NAME} (${SOURCE_VOLUME})"
REMOTE_SCRIPT
}

validate_person_detection_config() {
  local container="$1"
  case "$PERSON_DETECTION_ENABLED" in
    true)
      if [ -z "$PERSON_DETECTION_MODEL_PATH" ] || \
         ! _ssh "docker exec ${container} test -s $(remote_quote "$PERSON_DETECTION_MODEL_PATH")"; then
        echo "[vision] person detector model is missing in ${container}: ${PERSON_DETECTION_MODEL_PATH:-<not configured>}" >&2
        return 1
      fi
      ;;
    false) ;;
    *)
      echo "[vision] PERSON_DETECTION_ENABLED must be true or false" >&2
      return 1
      ;;
  esac
}

camera_topic_sample() {
  local container="$1" topic="$2" timeout="${3:-5}" remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
TOPIC=$(remote_quote "$topic") \
TIMEOUT_SEC=$(remote_quote "$timeout") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
RMW_IMPLEMENTATION=$(remote_quote "$RMW_IMPLEMENTATION") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

probe_timeout=$(( ${TIMEOUT_SEC%.*} + 3 ))
timeout -k 1s "${probe_timeout}s" docker exec -i \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  -e RMW_IMPLEMENTATION="$RMW_IMPLEMENTATION" \
  -e TOPIC="$TOPIC" \
  -e TIMEOUT_SEC="$TIMEOUT_SEC" \
  "$CONTAINER" bash -lc "${ROS_SETUP}; python3 -" <<'PY'
import os
import sys
import time

import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

topic = os.environ["TOPIC"]
timeout = float(os.environ["TIMEOUT_SEC"])
received = False

rclpy.init()
node = rclpy.create_node("robot_camera_readiness_probe")
qos = QoSProfile(depth=1)
qos.reliability = ReliabilityPolicy.BEST_EFFORT
qos.durability = DurabilityPolicy.VOLATILE

def on_image(_msg):
    global received
    received = True

node.create_subscription(Image, topic, on_image, qos)
deadline = time.monotonic() + timeout
try:
    while rclpy.ok() and not received and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()

sys.exit(0 if received else 1)
PY
REMOTE_SCRIPT
}

report_camera_failure() {
  local container="$1" reason="$2" remote_env
  echo "[camera] startup failed: ${reason}" >&2
  remote_env="CONTAINER=$(remote_quote "$container") \
SERVICE_LOG_DIR=$(remote_quote "$SERVICE_LOG_DIR")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT' >&2 || true
set +e
log_file="${SERVICE_LOG_DIR}/evo_camera.log"

echo "[camera] topic snapshot:"
docker exec "$CONTAINER" bash -lc \
  'source /opt/ros/humble/setup.bash 2>/dev/null; ros2 topic list 2>/dev/null | grep -E "^/camera/(color|depth)/" || true' |
  sed 's/^/  /'

if [ -f "$log_file" ]; then
  if grep -qE 'Current found device\(s\): \(0\)|No Device found|queryDevice :No Device found' "$log_file"; then
    echo "[camera] Orbbec device was not detected. Check USB/power/cable and restart the camera stack."
  fi
  echo "[camera] end of evo_camera.log:"
  tail -n 80 "$log_file" | sed 's/^/  /'
else
  echo "[camera] no captured camera log at ${log_file}"
fi
REMOTE_SCRIPT
}

wait_for_camera_ready() {
  local container="$1" deadline color_ready=false depth_ready=false
  echo "[camera] waiting for color/depth image topics"

  if ! [[ "$CAMERA_STARTUP_TIMEOUT_SEC" =~ ^[1-9][0-9]*$ ]]; then
    echo "[camera] CAMERA_STARTUP_TIMEOUT_SEC must be a positive integer" >&2
    return 1
  fi

  deadline=$((SECONDS + CAMERA_STARTUP_TIMEOUT_SEC))
  while (( SECONDS < deadline )); do
    if [ "$color_ready" != true ] && camera_topic_sample "$container" "$CAMERA_TOPIC" 4 >/dev/null 2>&1; then
      color_ready=true
      echo "[camera] color topic ready: ${CAMERA_TOPIC}"
    fi
    if [ "$PERSON_DETECTION_ENABLED" != "true" ]; then
      depth_ready=true
    elif [ "$depth_ready" != true ] && camera_topic_sample "$container" "$DEPTH_TOPIC" 4 >/dev/null 2>&1; then
      depth_ready=true
      echo "[camera] depth topic ready: ${DEPTH_TOPIC}"
    fi

    if [ "$color_ready" = true ] && [ "$depth_ready" = true ]; then
      echo "[camera] ready: required image topics are publishing"
      return 0
    fi
    sleep 1
  done

  local reason="missing required camera topics"
  if [ "$color_ready" != true ] && [ "$depth_ready" != true ]; then
    reason="missing color topic ${CAMERA_TOPIC} and depth topic ${DEPTH_TOPIC}"
  elif [ "$color_ready" != true ]; then
    reason="missing color topic ${CAMERA_TOPIC}"
  elif [ "$depth_ready" != true ]; then
    reason="missing depth topic ${DEPTH_TOPIC}"
  fi
  report_camera_failure "$container" "$reason"
  return 1
}

person_detector_status_snapshot() {
  local container="$1" timeout="${2:-8}" remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
TIMEOUT_SEC=$(remote_quote "$timeout") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
RMW_IMPLEMENTATION=$(remote_quote "$RMW_IMPLEMENTATION") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

probe_timeout=$(( ${TIMEOUT_SEC%.*} + 3 ))
timeout -k 1s "${probe_timeout}s" docker exec -i \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  -e RMW_IMPLEMENTATION="$RMW_IMPLEMENTATION" \
  -e TIMEOUT_SEC="$TIMEOUT_SEC" \
  "$CONTAINER" bash -lc "${ROS_SETUP}; python3 -" <<'PY'
import json
import os
import sys
import time

import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

timeout = float(os.environ["TIMEOUT_SEC"])
healthy_states = {"ready", "active", "detecting"}
last_status = "status topic missing"
done = False
ok = False

def describe(data):
    payload = json.loads(data)
    state = str(payload.get("state", ""))
    message = str(payload.get("message", ""))
    return state, f"state={state or '<missing>'} message={message}"

def on_status(msg):
    global done, last_status, ok
    try:
        state, status = describe(msg.data)
    except Exception as exc:
        last_status = f"invalid_status_json={exc}"
        return
    last_status = status
    if state in healthy_states:
        ok = True
        done = True

rclpy.init()
node = rclpy.create_node("robot_person_detector_status_probe")
qos = QoSProfile(depth=1)
qos.reliability = ReliabilityPolicy.RELIABLE
qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
node.create_subscription(String, "/vision/people/detector_status", on_status, qos)

deadline = time.monotonic() + timeout
try:
    while rclpy.ok() and not done and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()

print(last_status)
sys.exit(0 if ok else 1)
PY
REMOTE_SCRIPT
}

person_detection_sample() {
  local container="$1" timeout="${2:-3}" remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
TIMEOUT_SEC=$(remote_quote "$timeout") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
RMW_IMPLEMENTATION=$(remote_quote "$RMW_IMPLEMENTATION") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail
docker exec \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  -e RMW_IMPLEMENTATION="$RMW_IMPLEMENTATION" \
  "$CONTAINER" bash -lc \
  "${ROS_SETUP}; timeout -k 1s ${TIMEOUT_SEC}s ros2 topic echo --once /vision/people/detections --field tracking_id 2>/dev/null"
REMOTE_SCRIPT
}

wait_for_person_detection_ready() {
  local container="$1" status detection
  if [ "$PERSON_DETECTION_ENABLED" != "true" ]; then
    echo "[vision] person detection is disabled; skipping readiness check"
    return 0
  fi

  echo "[vision] waiting for person detector status"
  if status="$(person_detector_status_snapshot "$container" "${PERSON_DETECTION_TIMEOUT_SEC:-30}")"; then
    detection="$(person_detection_sample "$container" 2 2>/dev/null || true)"
    if [ -n "$detection" ]; then
      echo "[vision] person detector ready: ${status}; detection_seen=true"
    else
      echo "[vision] person detector ready: ${status}; detection_seen=false"
    fi
    return 0
  fi

  echo "[vision] person detector did not report a healthy status within ${PERSON_DETECTION_TIMEOUT_SEC:-30}s" >&2
  echo "[vision] last detector status: ${status:-<none>}" >&2
  echo "[vision] camera/depth topics were checked before vision startup; inspect current state with ./scripts/robot.sh doctor" >&2
  echo "[vision] inspect: ./scripts/robot.sh logs --tail vision" >&2
  return 1
}

# --- Doctor -------------------------------------------------------------------

run_doctor() {
  local container="$1" failed=0 line

  _doctor_pass() { printf '  %-45s PASS\n' "$1"; }
  _doctor_fail() { printf '  %-45s FAIL  %s\n' "$1" "$2"; failed=1; }

  echo "doctor — reception robot readiness"
  echo

  # 1. SSH reachability
  if _ssh true 2>/dev/null; then
    _doctor_pass "SSH reachable (${JETSON_USER}@${JETSON_IP})"
  else
    _doctor_fail "SSH reachable" "${JETSON_USER}@${JETSON_IP} — unreachable"
    echo
    echo "doctor stopped: the Jetson is not reachable."
    return 1
  fi

  # 2. Container running
  if [ -n "$container" ]; then
    _doctor_pass "evo-ros container (${container})"
  else
    _doctor_fail "evo-ros container" "not running or not found"
    echo
    echo "doctor stopped: the evo-ros Docker container must be running."
    return 1
  fi

  # 3. MCU alive
  if mcu_is_alive "$container"; then
    _doctor_pass "MCU publishing ${MCU_PROBE_TOPIC}"
  else
    _doctor_fail "MCU publishing ${MCU_PROBE_TOPIC}" "silent; run ./scripts/robot.sh mcu"
  fi

  # 4. Person detection model
  if [ "$PERSON_DETECTION_ENABLED" = "true" ]; then
    if [ -n "$PERSON_DETECTION_MODEL_PATH" ] && \
       _ssh "docker exec ${container} test -s $(remote_quote "$PERSON_DETECTION_MODEL_PATH")"; then
      _doctor_pass "detector model present"
    else
      _doctor_fail "detector model present" "${PERSON_DETECTION_MODEL_PATH:-<not configured>}"
    fi
  else
    _doctor_pass "detector model (PERSON_DETECTION_ENABLED=false)"
  fi

  # 5. Camera image streams
  local camera_color_ok=false camera_depth_ok=false
  if camera_topic_sample "$container" "$CAMERA_TOPIC" 5 >/dev/null 2>&1; then
    camera_color_ok=true
    _doctor_pass "camera color topic (${CAMERA_TOPIC})"
  else
    _doctor_fail "camera color topic" "${CAMERA_TOPIC} is not publishing"
  fi

  if [ "$PERSON_DETECTION_ENABLED" != "true" ]; then
    camera_depth_ok=true
    _doctor_pass "camera depth topic (not required)"
  elif camera_topic_sample "$container" "$DEPTH_TOPIC" 5 >/dev/null 2>&1; then
    camera_depth_ok=true
    _doctor_pass "camera depth topic (${DEPTH_TOPIC})"
  else
    _doctor_fail "camera depth topic" "${DEPTH_TOPIC} is not publishing"
  fi

  # 6. Person detector status or an actual detection.
  if [ "$PERSON_DETECTION_ENABLED" = "true" ]; then
    local detector_status detection
    if [ "$camera_color_ok" != true ] || [ "$camera_depth_ok" != true ]; then
      _doctor_fail "person detector ready" "camera topics are not ready"
    elif detector_status="$(person_detector_status_snapshot "$container" 8 2>/dev/null)"; then
      detection="$(person_detection_sample "$container" 2 2>/dev/null || true)"
      if [ -n "$detection" ]; then
        _doctor_pass "person detector ready (${detector_status}; detection_seen=true)"
      else
        _doctor_pass "person detector ready (${detector_status}; detection_seen=false)"
      fi
    else
      _doctor_fail "person detector ready" "${detector_status:-status topic missing}"
    fi
  else
    _doctor_pass "person detector (disabled)"
  fi

  # 7. AMCL pose
  local amcl_snapshot
  if amcl_snapshot="$(amcl_readiness_snapshot "$container" 5 2>/dev/null)"; then
    _doctor_pass "AMCL localized (${amcl_snapshot})"
  else
    _doctor_fail "AMCL localized" "${amcl_snapshot:-pose missing} (limit ${REAL_MAX_LOCALIZATION_XY_VARIANCE})"
  fi

  # 8. pyzbar QR decoder
  if _ssh "docker exec ${container} python3 -c 'from pyzbar.pyzbar import decode; print(\"ok\")' 2>/dev/null" | grep -q ok; then
    _doctor_pass "pyzbar QR decoder"
  else
    _doctor_fail "pyzbar QR decoder" "import failed; rebuild the evo-ros image"
  fi

  # 9. Voice PulseAudio and model files
  local sink source
  sink="$(_ssh 'pactl info 2>/dev/null | awk -F": " "/Default Sink:/{print \$2}"' 2>/dev/null || true)"
  source="$(_ssh 'pactl info 2>/dev/null | awk -F": " "/Default Source:/{print \$2}"' 2>/dev/null || true)"
  if [ -n "$sink" ] && [ -n "$source" ]; then
    _doctor_pass "PulseAudio sink/source"
  else
    _doctor_fail "PulseAudio sink/source" "default sink or source is missing"
  fi

  if [ -n "$PIPER_MODEL_PATH" ] && \
     _ssh "docker exec ${container} test -f $(remote_quote "$PIPER_MODEL_PATH")"; then
    _doctor_pass "Piper model (${PIPER_MODEL_PATH##*/})"
  else
    _doctor_fail "Piper model" "${PIPER_MODEL_PATH:-<not configured>}"
  fi

  if [ -n "$STT_MODEL_PATH" ] && \
     _ssh "docker exec ${container} test -s $(remote_quote "${STT_MODEL_PATH}/model.bin")"; then
    _doctor_pass "STT model (${STT_MODEL_PATH##*/})"
  else
    _doctor_fail "STT model" "${STT_MODEL_PATH:-<not configured>}/model.bin"
  fi

  # 10. Laravel reachable
  local validation_url
  if validation_url="$(resolve_reception_validation_url 2>/dev/null)"; then
    if curl --silent --output /dev/null --connect-timeout 3 --max-time 5 "$validation_url" 2>/dev/null; then
      _doctor_pass "Laravel validation endpoint"
    else
      _doctor_fail "Laravel validation endpoint" "${validation_url} — unreachable"
    fi
  else
    _doctor_fail "Laravel validation endpoint" "URL could not be resolved"
  fi

  echo
  if [ "$failed" -eq 0 ]; then
    echo "doctor: all checks passed — the robot is ready for the reception demo."
  else
    echo "doctor: one or more checks failed — see FAIL lines above."
  fi
  return "$failed"
}

require_web_port_available() {
  local container="$1" remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
CAMERA_PORT=$(remote_quote "$CAMERA_PORT")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

if docker exec "$CONTAINER" python3 -c '
import socket
import sys

sock = socket.socket()
try:
    # Match ReusableThreadingHTTPServer. A recently closed HTTP connection can
    # leave the address in TCP teardown state even though no process is
    # listening; SO_REUSEADDR permits the safe restart that the real server
    # itself supports while still rejecting an active listener.
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", int(sys.argv[1])))
finally:
    sock.close()
' "$CAMERA_PORT"; then
  exit 0
fi

echo "[web] port ${CAMERA_PORT} is already in use; refusing a partial dashboard launch." >&2
echo "[web] current listener:" >&2
ss -ltnp 2>/dev/null | grep -E ":${CAMERA_PORT}[[:space:]]" >&2 ||
  docker exec "$CONTAINER" ss -ltnp 2>/dev/null |
    grep -E ":${CAMERA_PORT}[[:space:]]" >&2 ||
  echo "  listener ownership unavailable" >&2
echo "[web] stop the owning service or configure a different CAMERA_PORT." >&2
exit 1
REMOTE_SCRIPT
}

# start_service <nom> <conteneur>
# Lance le service dans une session tmux DÉTACHÉE sur le Jetson. Le quoting passe par
# remote_quote (env) + printf %q (commande docker) côté distant : robuste face aux args
# ROS (`:=`), aux espaces et au sourcing multi-ligne — fini les quotes imbriquées.
start_service() {
  local name="$1" container="$2" cmd remote_env probe_status
  if [ "$name" = "teleop" ] && \
     _ssh_test "tmux has-session -t evo_nav 2>/dev/null || tmux has-session -t evo_slam 2>/dev/null"; then
    echo "[start] teleop velocity pipeline is already provided by the active Nav2/SLAM service"
    return 0
  elif probe_status=$?; [ "$probe_status" -eq 2 ]; then
    return 1
  fi
  if { [ "$name" = "nav" ] || [ "$name" = "slam" ]; } && \
     _ssh_test "tmux has-session -t evo_teleop 2>/dev/null"; then
    echo "[start] replacing the standalone teleop pipeline with ${name}"
    stop_service teleop "$container"
  elif probe_status=$?; [ "$probe_status" -eq 2 ]; then
    return 1
  fi
  if _ssh_test "tmux has-session -t evo_${name} 2>/dev/null"; then
    echo "[start] evo_${name} already running"
    return 0
  elif probe_status=$?; [ "$probe_status" -eq 2 ]; then
    return 1
  fi
  if [ "$name" = "web" ]; then
    require_web_port_available "$container" || return 1
  fi
  if ! cmd="$(service_cmd "$name")"; then
    echo "[start] unknown service: ${name}" >&2
    return 1
  fi
  # Verify the repository map, or sync an explicitly selected Jetson-host map.
  if [ "$name" = "nav" ]; then
    ensure_map_in_docker "$container" "$MAP_PATH" || return 1
  fi
  echo "[start] evo_${name} : ${cmd}"
  remote_env="CONTAINER=$(remote_quote "$container") \
SESSION=$(remote_quote "evo_${name}") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
RMW_IMPLEMENTATION=$(remote_quote "$RMW_IMPLEMENTATION") \
ROBOT_DISPLAY=$(remote_quote "$KIOSK_DISPLAY") \
SERVICE_LOG_DIR=$(remote_quote "$SERVICE_LOG_DIR") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)") \
ROS_CMD=$(remote_quote "$cmd")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail
full_cmd="${ROS_SETUP}; ${ROS_CMD}"
mkdir -p "$SERVICE_LOG_DIR"
log_file="${SERVICE_LOG_DIR}/${SESSION}.log"
docker_cmd=$(printf 'docker exec -i -e ROS_DOMAIN_ID=%q -e FASTDDS_BUILTIN_TRANSPORTS=%q -e RMW_IMPLEMENTATION=%q -e RCUTILS_LOGGING_BUFFERED_STREAM=0 -e DISPLAY=%q %q bash -lc %q' \
  "$ROS_DOMAIN_ID" "$FASTDDS_BUILTIN_TRANSPORTS" "$RMW_IMPLEMENTATION" "$ROBOT_DISPLAY" "$CONTAINER" "$full_cmd")
tmux_cmd=$(printf '%s > %q 2>&1' "$docker_cmd" "$log_file")
tmux new-session -d -s "$SESSION" "$tmux_cmd"

# A detached tmux session can disappear immediately when ros2 launch fails.
# Preserve and report that error instead of claiming that the service started.
sleep 2
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[start] ${SESSION} exited during startup." >&2
  echo "[start] captured log: ${log_file}" >&2
  if [ -s "$log_file" ]; then
    tail -n 80 "$log_file" >&2
  else
    echo "[start] no output was captured" >&2
  fi
  exit 1
fi
echo "[start] persistent log: ${log_file}"
REMOTE_SCRIPT
}

# Read the reception waypoint from the configured YAML and publish it as the
# AMCL initial pose so the operator never needs to use the dashboard's
# "2D Pose Estimate" tool.  The waypoint must contain a `reception` entry with
# x, y, and yaw in the map frame.
publish_initial_pose_from_reception() {
  local container="$1"
  local show_hint="${2:-false}"

  if [ "${INITIAL_POSE_AUTO_ENABLED:-true}" != "true" ]; then
    if [ "$show_hint" = "true" ]; then
      echo "[nav] auto initial pose is disabled (INITIAL_POSE_AUTO_ENABLED=false)"
      echo "[nav] set the verified initial pose in the dashboard before the AMCL readiness check"
    fi
    return 0
  fi

  if [ -z "${RECEPTION_WAYPOINT_CONFIG_PATH:-}" ]; then
    echo "[pose] no reception waypoint configured; skipping auto initial pose" >&2
    return 0
  fi

  local remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
RECEPTION_WAYPOINT_CONFIG_PATH=$(remote_quote "$RECEPTION_WAYPOINT_CONFIG_PATH")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

if ! docker exec "$CONTAINER" test -f "$RECEPTION_WAYPOINT_CONFIG_PATH"; then
  echo "[pose] reception waypoint file is missing in container: ${RECEPTION_WAYPOINT_CONFIG_PATH}" >&2
  exit 1
fi

pose_json="$(docker exec -i "$CONTAINER" python3 - "$RECEPTION_WAYPOINT_CONFIG_PATH" <<'PY'
import json
import math
import sys

import yaml

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    data = yaml.safe_load(handle) or {}

frame_id = str(data.get("frame_id", ""))
if frame_id != "map":
    raise SystemExit(f"waypoint file must use frame_id=map, got {frame_id!r}")

waypoints = data.get("waypoints")
if not isinstance(waypoints, dict) or "reception" not in waypoints:
    raise SystemExit("waypoint file must define waypoints.reception")

reception = waypoints["reception"]
x = float(reception["x"])
y = float(reception["y"])
yaw = float(reception["yaw"])
if not all(math.isfinite(value) for value in (x, y, yaw)):
    raise SystemExit("reception waypoint x/y/yaw must be finite numbers")

qz = math.sin(yaw / 2.0)
qw = math.cos(yaw / 2.0)
message = {
    "header": {"stamp": {"sec": 0, "nanosec": 0}, "frame_id": "map"},
    "pose": {
        "pose": {
            "position": {"x": x, "y": y, "z": 0.0},
            "orientation": {"x": 0.0, "y": 0.0, "z": qz, "w": qw},
        },
        "covariance": [
            0.05, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.05, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.05,
        ],
    },
}
print(f"[pose] parsed reception waypoint: frame_id=map x={x:.3f} y={y:.3f} yaw={yaw:.3f}", file=sys.stderr)
print(json.dumps(message, separators=(",", ":")))
PY
)"

echo "[pose] publishing AMCL initial pose from reception waypoint"
printf '%s\n' "$pose_json" | docker exec -i "$CONTAINER" bash -lc '
source /opt/ros/humble/setup.bash
ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped --qos-reliability reliable --qos-durability transient_local -
'
REMOTE_SCRIPT
}

amcl_readiness_snapshot() {
  local container="$1" timeout="${2:-5}" remote_env
  remote_env="CONTAINER=$(remote_quote "$container") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
RMW_IMPLEMENTATION=$(remote_quote "$RMW_IMPLEMENTATION") \
MAX_LOCALIZATION_XY_VARIANCE=$(remote_quote "$REAL_MAX_LOCALIZATION_XY_VARIANCE") \
TIMEOUT_SEC=$(remote_quote "$timeout") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

run_ros() {
  local ros_setup="${ROS_SETUP//\'/}"
  docker exec \
    -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
    -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
    -e RMW_IMPLEMENTATION="$RMW_IMPLEMENTATION" \
    "$CONTAINER" bash -lc "${ros_setup}; $1"
}

parse_amcl_sample() {
  python3 -c '
import math
import sys

import yaml

try:
    data = yaml.safe_load(sys.stdin.read()) or {}
    frame_id = str(data.get("header", {}).get("frame_id", ""))
    covariance = data.get("pose", {}).get("covariance", [])
    if len(covariance) < 8:
        print("pose missing")
        raise SystemExit(1)
    x_var = float(covariance[0])
    y_var = float(covariance[7])
    limit = float(sys.argv[1])
    ok = (
        frame_id == "map"
        and math.isfinite(x_var)
        and math.isfinite(y_var)
        and 0.0 <= x_var <= limit
        and 0.0 <= y_var <= limit
    )
    display_frame = frame_id if frame_id else "<missing>"
    print(f"frame_id={display_frame} x_var={x_var:.6g} y_var={y_var:.6g}")
    raise SystemExit(0 if ok else 1)
except Exception as exc:
    print(f"parse_error={exc}")
    raise SystemExit(2)
' "$MAX_LOCALIZATION_XY_VARIANCE"
}

deadline=$((SECONDS + TIMEOUT_SEC))
last_status="pose missing"
while (( SECONDS < deadline )); do
  set +e
  sample="$(run_ros "timeout -k 1s 4s ros2 topic echo /amcl_pose --once 2>/dev/null" 2>/dev/null)"
  sample_rc=$?
  set -e
  if [ "$sample_rc" -eq 0 ] && [ -n "$sample" ]; then
    set +e
    status="$(printf '%s\n' "$sample" | parse_amcl_sample)"
    rc=$?
    set -e
    last_status="$status"
    if [ "$rc" -eq 0 ]; then
      printf '%s\n' "$status"
      exit 0
    fi
  fi
  sleep 1
done

printf '%s\n' "$last_status"
exit 1
REMOTE_SCRIPT
}

wait_for_amcl_localized() {
  local container="$1" snapshot
  echo "[nav] waiting for AMCL localization from the reception initial pose"

  if [ "${INITIAL_POSE_AUTO_ENABLED:-true}" != "true" ]; then
    publish_initial_pose_from_reception "$container" true
    if snapshot="$(amcl_readiness_snapshot "$container" "$REAL_NAVIGATION_TIMEOUT_SEC")"; then
      echo "[nav] localized: ${snapshot}"
      return 0
    fi
    echo "[nav] AMCL localization failed: ${snapshot}" >&2
    return 1
  fi

  publish_initial_pose_from_reception "$container" || return 1
  if snapshot="$(amcl_readiness_snapshot "$container" 15)"; then
    echo "[nav] localized: ${snapshot}"
    return 0
  fi

  echo "[nav] AMCL not localized yet (${snapshot}); re-publishing the reception initial pose once"
  publish_initial_pose_from_reception "$container" || return 1
  if snapshot="$(amcl_readiness_snapshot "$container" "$REAL_NAVIGATION_TIMEOUT_SEC")"; then
    echo "[nav] localized: ${snapshot}"
    return 0
  fi

  echo "[nav] AMCL localization failed after initial pose retry: ${snapshot}" >&2
  echo "[nav] inspect: ./scripts/robot.sh logs --tail nav" >&2
  return 1
}

wait_for_reception_navigation_ready() {
  local container="$1" remote_env
  echo "[nav] verifying map, localization, E-stop, and real reception navigation"

  if [ "${INITIAL_POSE_AUTO_ENABLED:-true}" != "true" ]; then
    echo "[nav] INITIAL_POSE_AUTO_ENABLED is false — set the initial pose in the dashboard"
  fi

  remote_env="CONTAINER=$(remote_quote "$container") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
RMW_IMPLEMENTATION=$(remote_quote "$RMW_IMPLEMENTATION") \
DOCKER_WS=$(remote_quote "$DOCKER_WS") \
MAX_LOCALIZATION_XY_VARIANCE=$(remote_quote "$REAL_MAX_LOCALIZATION_XY_VARIANCE") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  if _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

if docker exec \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  -e RMW_IMPLEMENTATION="$RMW_IMPLEMENTATION" \
  "$CONTAINER" bash -lc \
  "${ROS_SETUP}; ${DOCKER_WS}/install/evo_navigation/lib/evo_navigation/reception_nav_readiness_checker --timeout-sec 45 --progress-sec 5 --max-localization-xy-variance ${MAX_LOCALIZATION_XY_VARIANCE}"; then
  exit 0
fi

echo "[nav] real reception navigation readiness failed." >&2
if ! tmux has-session -t evo_reception_nav 2>/dev/null; then
  echo "[nav] evo_reception_nav tmux session is not running." >&2
fi
echo "[nav] end of reception navigation log:" >&2
tail -n 80 /home/jetson/evo_logs/evo_reception_nav.log >&2 2>/dev/null || \
  echo "[nav] reception navigation log is unavailable." >&2
exit 1
REMOTE_SCRIPT
  then
    return 0
  fi

  echo "[nav] reception navigation readiness check failed." >&2
  echo "[nav] inspect: ./scripts/robot.sh logs --tail reception_nav" >&2
  return 1
}

# Verify that the web launch did not survive with rosbridge while its required
# camera HTTP child exited (for example after an EADDRINUSE bind failure).
wait_for_web_ready() {
  local container="$1" remote_env
  echo "[web] waiting for dashboard bridge and camera HTTP server"
  remote_env="CONTAINER=$(remote_quote "$container") \
CAMERA_PORT=$(remote_quote "$CAMERA_PORT") \
ROSBRIDGE=$(remote_quote "$ROSBRIDGE") \
ROSBRIDGE_PORT=$(remote_quote "$ROSBRIDGE_PORT") \
WEB_STARTUP_TIMEOUT=$(remote_quote "$WEB_STARTUP_TIMEOUT") \
SERVICE_LOG_DIR=$(remote_quote "$SERVICE_LOG_DIR")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

deadline=$((SECONDS + WEB_STARTUP_TIMEOUT))
http_error="not attempted"
rosbridge_error="not attempted"
while (( SECONDS < deadline )); do
  web_server_ready=false
  arm_relay_ready=false
  http_ready=false
  rosbridge_ready=true

  if docker exec "$CONTAINER" pgrep -f '[w]eb_server_node' >/dev/null 2>&1; then
    web_server_ready=true
  fi
  if docker exec "$CONTAINER" pgrep -f '[a]rm_command_relay_node' >/dev/null 2>&1; then
    arm_relay_ready=true
  fi
  # Use a direct socket instead of urllib. urllib inherits proxy variables
  # from the image and can route even a loopback health check through a proxy,
  # falsely reporting failure while port 8080 is already listening.
  if http_error="$(docker exec "$CONTAINER" python3 -c '
import socket
import sys

with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=2) as sock:
    sock.sendall(
        b"GET /camera/status HTTP/1.0\r\n"
        b"Host: 127.0.0.1\r\n"
        b"Connection: close\r\n\r\n"
    )
    status = sock.recv(128).split(b"\r\n", 1)[0]
    if b" 200 " not in status:
        raise RuntimeError("unexpected HTTP status: {!r}".format(status))
' "$CAMERA_PORT" 2>&1)"; then
    http_ready=true
  fi
  if [ "$ROSBRIDGE" = "true" ]; then
    if rosbridge_error="$(docker exec "$CONTAINER" python3 -c '
import socket
import sys

with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=1):
    pass
' "$ROSBRIDGE_PORT" 2>&1)"; then
      rosbridge_ready=true
    else
      rosbridge_ready=false
    fi
  fi

  if [ "$web_server_ready" = true ] && [ "$arm_relay_ready" = true ] && \
     [ "$http_ready" = true ] && [ "$rosbridge_ready" = true ]; then
    echo "[web] ready: camera HTTP, arm relay, and rosbridge available"
    exit 0
  fi

  if ! tmux has-session -t evo_web 2>/dev/null; then
    echo "[web] startup failed: evo_web exited while readiness was being checked" >&2
    break
  fi
  sleep 1
done

echo "[web] startup failed: required HTTP/ROS nodes did not become ready" >&2
echo "[web] last readiness state:" >&2
echo "  web process: ${web_server_ready}" >&2
echo "  arm relay:   ${arm_relay_ready}" >&2
echo "  HTTP 8080:   ${http_ready} (${http_error:-no error})" >&2
echo "  rosbridge:   ${rosbridge_ready} (${rosbridge_error:-no error})" >&2
echo "[web] process snapshot:" >&2
docker exec "$CONTAINER" bash -lc '
  pids="$(pgrep -d, -f "web_server_node|arm_command_relay_node|rosbridge_websocket|rosapi_node" || true)"
  if [ -n "$pids" ]; then
    ps -o pid=,stat=,etime=,wchan=,cmd= -p "$pids"
  fi
' >&2 || true
echo "[web] listeners on camera and rosbridge ports:" >&2
ss -ltnp 2>/dev/null |
  grep -E ":(${CAMERA_PORT}|${ROSBRIDGE_PORT})[[:space:]]" >&2 ||
  docker exec "$CONTAINER" ss -ltnp 2>/dev/null |
    grep -E ":(${CAMERA_PORT}|${ROSBRIDGE_PORT})[[:space:]]" >&2 ||
  echo "  no listener ownership available" >&2
echo "[web] beginning of captured log:" >&2
sed -n '1,80p' "${SERVICE_LOG_DIR}/evo_web.log" >&2 || true
echo "[web] end of captured log:" >&2
tail -n 80 "${SERVICE_LOG_DIR}/evo_web.log" >&2 || true
echo "[web] inspect: ./scripts/robot.sh logs web" >&2
exit 1
REMOTE_SCRIPT
}

# Verify data and command endpoints rather than treating a running launch
# process as proof that the dashboard can see or control robot hardware.
wait_for_dashboard_hardware_ready() {
  local container="$1" require_camera="$2" require_motion="$3" remote_env
  echo "[dashboard] checking camera, arm, and teleop ROS routes"
  remote_env="CONTAINER=$(remote_quote "$container") \
CAMERA_PORT=$(remote_quote "$CAMERA_PORT") \
REQUIRE_CAMERA=$(remote_quote "$require_camera") \
REQUIRE_MOTION=$(remote_quote "$require_motion") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

topic_count() {
  local topic="$1" kind="$2"
  docker exec \
    -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
    -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
    "$CONTAINER" bash -lc \
    "${ROS_SETUP}; timeout -k 1s 4s ros2 topic info --no-daemon --spin-time 2 ${topic} 2>/dev/null" \
    | awk -v label="$kind count:" '$0 ~ label {print $3}'
}

for attempt in $(seq 1 20); do
  arm_input_subscribers="$(topic_count /evo/arm/command Subscription || true)"
  arm_hardware_subscribers="$(topic_count /arm6_joints Subscription || true)"
  teleop_subscribers="$(topic_count /cmd_vel_teleop Subscription || true)"
  base_subscribers="$(topic_count /cmd_vel Subscription || true)"
  camera_ready=true

  if [ "$REQUIRE_CAMERA" = "true" ]; then
    camera_ready="$(python3 - "$CAMERA_PORT" <<'PY'
import json
import sys
import urllib.request

try:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{sys.argv[1]}/camera/status", timeout=2
    ) as response:
        status = json.load(response)
    print("true" if status.get("available") else "false")
except Exception:
    print("false")
PY
)"
  fi

  motion_ready=true
  if [ "$REQUIRE_MOTION" = "true" ] && {
    [ "${teleop_subscribers:-0}" -lt 1 ] || [ "${base_subscribers:-0}" -lt 1 ]
  }; then
    motion_ready=false
  fi

  if [ "${arm_input_subscribers:-0}" -ge 1 ] && \
     [ "${arm_hardware_subscribers:-0}" -ge 1 ] && \
     [ "$motion_ready" = true ] && [ "$camera_ready" = true ]; then
    echo "[dashboard] ready: camera frames and hardware command subscribers available"
    exit 0
  fi
  sleep 1
done

echo "[dashboard] hardware route is incomplete:" >&2
echo "  /evo/arm/command subscribers: ${arm_input_subscribers:-0} (expected relay)" >&2
echo "  /arm6_joints subscribers:     ${arm_hardware_subscribers:-0} (expected MCU)" >&2
if [ "$REQUIRE_MOTION" = "true" ]; then
  echo "  /cmd_vel_teleop subscribers:  ${teleop_subscribers:-0} (expected safety gate)" >&2
  echo "  /cmd_vel subscribers:         ${base_subscribers:-0} (expected MCU)" >&2
fi
if [ "$REQUIRE_CAMERA" = "true" ]; then
  echo "  camera JPEG available:        ${camera_ready}" >&2
  echo "  camera status: http://<robot-ip>:${CAMERA_PORT}/camera/status" >&2
fi
echo "Inspect: ./scripts/robot.sh logs web" >&2
exit 1
REMOTE_SCRIPT
}

# Wait until the saved-map Nav2 stack is genuinely usable. A running tmux
# session only proves that ros2 launch is alive; lifecycle configuration can
# still have failed while leaving every process present in the ROS graph.
wait_for_navigation_ready() {
  local container="$1" remote_env collision_arg
  echo "[nav] waiting for Nav2 lifecycle nodes and velocity routing"
  collision_arg=""
  if [ "$NAV_USE_COLLISION_MONITOR" = "true" ]; then
    collision_arg="--require-collision-monitor"
  fi
  remote_env="CONTAINER=$(remote_quote "$container") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
COLLISION_ARG=$(remote_quote "$collision_arg") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

if docker exec \
  -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
  "$CONTAINER" bash -lc \
  "${ROS_SETUP}; ros2 run evo_navigation nav_readiness_checker \
    --timeout-sec 115 --progress-sec 10 ${COLLISION_ARG}"; then
  echo "[nav] ready: lifecycle active, map and validator available, single safe /cmd_vel publisher"
  exit 0
fi

echo "[nav] startup failed: Nav2 did not become ready within 115 seconds" >&2
echo "Inspect: ./scripts/robot.sh logs nav" >&2
exit 1
REMOTE_SCRIPT
}

# stop_service <nom> <conteneur> : tue la session tmux ET tout le groupe de
# process du launch (launch + ses nœuds enfants partagent le même PGID).
# Tuer le ros2 launch seul laisse ses nœuds orphelins dans ce conteneur, d'où
# le kill par groupe (kill -- -PGID), en SIGTERM puis SIGKILL.
stop_service() {
  local name="$1" container="$2" pat safe
  if pat="$(service_pattern "$name")"; then
    # Astuce crochets : "[b]ringup..." matche le vrai process mais PAS la ligne de
    # commande de pgrep elle-même -> évite l'auto-match du shell.
    safe="[${pat:0:1}]${pat:1}"
    # Capture and stop the launch process group before removing its tmux owner.
    # Killing tmux first can make the launch parent disappear while leaving a
    # child node alive, so the later pgrep has no PGID left to discover.
    _ssh "docker exec ${container} bash -lc '
      for sig in TERM KILL; do
        for pid in \$(pgrep -f \"\$1\"); do
          pgid=\$(ps -o pgid= -p \"\$pid\" 2>/dev/null | tr -d \" \")
          [ -n \"\$pgid\" ] && kill -\$sig -\"\$pgid\" 2>/dev/null || true
        done
        sleep 1
      done
    ' _ '${safe}'"
  fi
  _ssh "tmux kill-session -t evo_${name} 2>/dev/null || true"

  # Recover from web children orphaned by the old tmux-first shutdown order.
  # These executable names belong exclusively to evo_web; rosbridge is not
  # matched because it may intentionally be shared with another launch.
  if [ "$name" = "web" ]; then
    _ssh "docker exec ${container} bash -lc '
      for sig in TERM KILL; do
        pkill -\$sig -f \"[w]eb_server_node\" 2>/dev/null || true
        pkill -\$sig -f \"[a]rm_command_relay_node\" 2>/dev/null || true
        sleep 1
      done
    '"
  fi
  # Recover vision nodes orphaned by an interrupted launch or by a vanished
  # tmux parent. Stale detector/status publishers make readiness probes lie.
  if [ "$name" = "vision" ]; then
    _ssh "docker exec ${container} bash -lc '
      for sig in TERM KILL; do
        pkill -\$sig -f \"[q]r_scanner_node\" 2>/dev/null || true
        pkill -\$sig -f \"[d]epth_obstacle_scan_node\" 2>/dev/null || true
        pkill -\$sig -f \"[o]bject_detector_node\" 2>/dev/null || true
        sleep 1
      done
    '"
  fi
  # Recover voice nodes and readiness probes orphaned by a failed/aborted
  # docker exec. They are exclusive to the evo_voice service, and leaving
  # them alive makes every subsequent model startup slower.
  if [ "$name" = "voice" ]; then
    _ssh "docker exec ${container} bash -lc '
      for sig in TERM KILL; do
        pkill -\$sig -f \"[t]ts_node\" 2>/dev/null || true
        pkill -\$sig -f \"[s]tt_node\" 2>/dev/null || true
        pkill -\$sig -f \"[i]ntent_detector_node\" 2>/dev/null || true
        pkill -\$sig -f \"[v]oice_readiness_checker\" 2>/dev/null || true
        sleep 1
      done
    '"
  fi
  echo "[stop] evo_${name} stopped"
}
