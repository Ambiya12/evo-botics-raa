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

  if [ "$docker_yaml" = "$PACKAGED_MAP_PATH" ]; then
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
    web)     echo "ros2 launch evo_web web_dashboard.launch.py rosbridge:=${ROSBRIDGE} rosbridge_port:=${ROSBRIDGE_PORT} http_port:=${CAMERA_PORT} camera_topic:=${CAMERA_TOPIC} camera_max_fps:=${CAMERA_MAX_FPS} camera_max_width:=${CAMERA_MAX_WIDTH} camera_jpeg_quality:=${CAMERA_JPEG_QUALITY}" ;;
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
    # Start and validate the lightweight web bridge before Nav2. Load Whisper
    # before the person detector so both local ML runtimes do not compete
    # during cold startup on the four-core Jetson Nano.
    demo-navigation) echo "bringup camera web nav voice dialogue vision reception approach reception_nav" ;;
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

wait_for_voice_ready() {
  local container="$1" remote_env
  echo "[voice] waiting for real microphone and Piper backends"
  remote_env="CONTAINER=$(remote_quote "$container") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
RMW_IMPLEMENTATION=$(remote_quote "$RMW_IMPLEMENTATION") \
DOCKER_WS=$(remote_quote "$DOCKER_WS") \
AUDIO_OUTPUT_DEVICE=$(remote_quote "$AUDIO_OUTPUT_DEVICE") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

run_ros() {
  docker exec \
    -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
    -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
    -e RMW_IMPLEMENTATION="$RMW_IMPLEMENTATION" \
    "$CONTAINER" bash -lc "${ROS_SETUP}; $1"
}

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

tts_ready="$(
  run_ros "timeout -k 2s 120s ros2 topic echo /voice/tts/diagnostics std_msgs/msg/String --once --qos-durability transient_local --qos-reliability reliable"
)"
case "$tts_ready" in
  *'"event": "ready"'*'"backend": "piper"'*) ;;
  *) echo "[voice] TTS did not report the real Piper backend: ${tts_ready}" >&2; exit 1 ;;
esac

stt_ready="$(
  run_ros "timeout -k 2s 120s ros2 topic echo /voice/stt/status std_msgs/msg/String --once --qos-durability transient_local --qos-reliability reliable"
)"
case "$stt_ready" in
  *"data: idle"*) ;;
  *) echo "[voice] STT did not open the real microphone: ${stt_ready:-no status}" >&2; exit 1 ;;
esac

echo "[voice] ready: Piper, Faster-Whisper, microphone, PulseAudio, and build revision verified"
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

# --- Cycle de vie des services ----------------------------------------------

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

wait_for_real_reception_navigation_ready() {
  local container="$1" remote_env
  echo "[demo] waiting for Home map, AMCL, E-stop, and real reception navigation"
  echo "[demo] set the reviewed initial pose now if AMCL is not initialized"
  remote_env="CONTAINER=$(remote_quote "$container") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

run_ros() {
  docker exec \
    -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
    -e FASTDDS_BUILTIN_TRANSPORTS="$FASTDDS_BUILTIN_TRANSPORTS" \
    "$CONTAINER" bash -lc "${ROS_SETUP}; $1"
}

allow_real_navigation="$(run_ros "timeout -k 2s 8s ros2 param get /navigation_orchestrator_node allow_real_navigation")"
case "$allow_real_navigation" in
  *"Boolean value is: True"*) ;;
  *) echo "[demo] real navigation authorization is not active: ${allow_real_navigation}" >&2; exit 1 ;;
esac

if ! run_ros "timeout -k 2s 20s ros2 topic echo /map --once --qos-durability transient_local --qos-reliability reliable" >/dev/null; then
  echo "[demo] reviewed map is not publishing." >&2
  exit 1
fi
if ! run_ros "timeout -k 2s 120s ros2 topic echo /amcl_pose --once --qos-durability volatile --qos-reliability reliable" >/dev/null; then
  echo "[demo] AMCL pose is unavailable; set and verify the initial pose." >&2
  exit 1
fi
estop="$(run_ros "timeout -k 2s 20s ros2 topic echo /e_stop_active --once --qos-durability volatile --qos-reliability reliable")"
case "$estop" in
  *"data: false"*) ;;
  *) echo "[demo] E-stop is active or unavailable: ${estop}" >&2; exit 1 ;;
esac
if ! run_ros "timeout -k 2s 10s ros2 action list" | grep -qx "/reception/guide_to_destination"; then
  echo "[demo] reception navigation action is unavailable." >&2
  exit 1
fi

echo "[demo] real reception navigation ready: map, AMCL, E-stop, and action accepted"
REMOTE_SCRIPT
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
  echo "[nav] set the verified initial pose in the dashboard if AMCL has not been initialized"
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
  echo "[stop] evo_${name} stopped"
}
