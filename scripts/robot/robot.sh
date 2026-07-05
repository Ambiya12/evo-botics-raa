#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
. "${SCRIPT_DIR}/config.sh"
. "${SCRIPT_DIR}/lib.sh"

usage() {
  cat <<EOF
Usage: ./scripts/robot.sh <command> [args]

Main commands:
  demo [home|school]          Clean-start real-data reception and open kiosk
  config ip <ip>              Save the current Jetson IP
  config show                 Show active robot settings
  config app-host <ip>        Save the Mac/app IP reachable from the Jetson
  launch [map-name|path]      Start saved-map navigation plus robot kiosk
  setup                       Push local evo_ws/src to Jetson and build
  sync-maps [map-name|path]   Copy a saved Jetson host map into the current Docker container
  kiosk [url|stop]            Open or close the kiosk page on the Jetson display

Launch modes:
  demo home                   Home reception; physical Nav2 when DEMO_REAL_NAVIGATION=true
  demo school                 School demo after its waypoint registry is configured
  launch                      saved school map + camera + QR scanner + kiosk screen
  start base                  bringup + camera + vision + web + safe teleop
  start map                   bringup + camera + SLAM + web
  start navigate              use MAP_PATH or the configured default saved map
  start reception             camera + QR scanner + QR validation bridge + web
  start voice                 isolated, unfinished voice stack
  start camera-qr             camera + QR scanner + mocked validation + web
  start stationary-reception  mock backend with forced-mock navigation
  start stationary-reception-real  real backend with forced-mock navigation
  start kiosk                 reception mode plus kiosk browser on the robot screen
  nav [map-name|path.yaml]    launch saved-map navigation
  map rviz                    create a map with RViz on the robot display
  map foxglove                create a map with Foxglove
  save-map [map-name]         save the current SLAM map

Operations:
  status                      tmux sessions, ROS topics, MCU, ports
  logs <service>              attach service logs, detach with Ctrl-b then d
  stop <service|mode|all>     stop services
  restart <mode>              restart an explicit mode
  mcu [--force]               check/recover the systemd-managed micro-ROS agent
  health                      Jetson health snapshot

Services: bringup camera vision reception reception_mock voice dialogue stationary_nav reception_nav approach web teleop slam nav
EOF
}

require_container() {
  local c
  c="$(resolve_container)"
  if [ -z "$c" ]; then
    echo "No active robot Docker container on ${JETSON_USER}@${JETSON_IP}." >&2
    echo "Check: ssh ${JETSON_USER}@${JETSON_IP} 'docker ps'" >&2
    exit 1
  fi
  printf '%s' "$c"
}

resolve_map_path_arg() {
  local map="${1:-}"
  if [ -z "$map" ]; then
    printf '%s\n' "$MAP_PATH"
  elif [[ "$map" == */* ]]; then
    printf '%s\n' "$map"
  else
    map="${map%.yaml}"
    printf '%s/%s.yaml\n' "$DOCKER_MAP_DIR" "$map"
  fi
}

build_evo_ws_in_docker() {
  local container="$1"
  local build
  build="$(_ros_prelude); cd ${DOCKER_WS} && colcon build --symlink-install"
  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc \"${build}\""
}

copy_host_ws_to_docker() {
  local container="$1"
  echo "[deploy] copying Jetson source into Docker (${container})"
  _ssh "docker exec ${container} rm -rf ${DOCKER_WS}/src &&
    docker exec ${container} mkdir -p ${DOCKER_WS}/src &&
    docker cp ${HOST_WS}/src/. ${container}:${DOCKER_WS}/src"
}

ensure_evo_ws_built() {
  local container="$1"
  if _ssh "docker exec ${container} test -d ${DOCKER_WS}/install"; then
    echo "[evo_ws] already built in Docker (${container})"
    return 0
  fi

  ensure_evo_ws "$container"
  echo "[evo_ws] building in Docker (${container})"
  build_evo_ws_in_docker "$container"
}

require_evo_ws_built() {
  local container="$1"
  if ! _ssh "docker exec ${container} test -f ${DOCKER_WS}/install/setup.bash"; then
    echo "[evo_ws] ${DOCKER_WS}/install/setup.bash is missing in ${container}." >&2
    echo "[evo_ws] stop active services, then deploy and build with: ./scripts/robot.sh setup" >&2
    return 1
  fi
}

cmd_setup() {
  if [ -n "${1:-}" ]; then
    echo "Usage: ./scripts/robot.sh setup" >&2
    exit 1
  fi

  local container
  container="$(require_container)"

  echo "[setup] deploying local evo_ws/src -> ${JETSON_USER}@${JETSON_IP}:${HOST_WS}/src"
  JETSON_IP="${JETSON_IP}" JETSON_USER="${JETSON_USER}" JETSON_WS="${HOST_WS}" \
    "${REPO_ROOT}/scripts/deploy.sh"

  copy_host_ws_to_docker "$container"
  ensure_map_in_docker "$container" "$MAP_PATH"

  echo "[setup] building in Docker (${container})"
  build_evo_ws_in_docker "$container"
  echo "[setup] done"
}

cmd_sync_maps() {
  case "${1:-}" in
    help|-h|--help)
      echo "Usage: ./scripts/robot.sh sync-maps <map-name|/root/maps/name.yaml>"
      echo "This command is only for maps saved on the Jetson host."
      return 0
      ;;
    "")
      echo "Usage: ./scripts/robot.sh sync-maps <map-name|/root/maps/name.yaml>" >&2
      echo "The default repository map does not need synchronization." >&2
      return 1
      ;;
  esac

  local map_name docker_map_path container
  docker_map_path="$(resolve_map_path_arg "${1:-}")"
  map_name="$(map_name_from_path "$docker_map_path")"
  container="$(require_container)"

  echo "[sync-maps] syncing ${map_name} into Docker (${container})"
  sync_map_from_host "$container" "$docker_map_path"
}

cmd_launch() {
  case "${1:-}" in
    help|-h|--help)
      echo "Usage: ./scripts/robot.sh launch [map-name|/root/maps/name.yaml]"
      echo "Default map: ${MAP_PATH}"
      return 0
      ;;
  esac
  local map_arg="${1:-}"
  if [ -n "$map_arg" ]; then
    MAP_PATH="$(resolve_map_path_arg "$map_arg")"
  fi

  ensure_tmux
  local container
  container="$(require_container)"

  resolve_reception_validation_url >/dev/null
  resolve_kiosk_url >/dev/null

  ensure_evo_ws_built "$container"
  ensure_map_in_docker "$container" "$MAP_PATH"
  ensure_qr_decoder_in_docker "$container"

  # The base MCU owns odometry and the /cmd_vel subscriber. Wake and verify it
  # immediately after bringup so Nav2 never starts with a broken TF/base chain.
  start_service bringup "$container"
  disable_legacy_joystick_control "$container"
  cmd_mcu

  local s
  for s in camera nav vision reception web; do
    start_service "$s" "$container"
  done
  if ! wait_for_web_ready "$container"; then
    stop_service web "$container"
    return 1
  fi
  wait_for_navigation_ready "$container"
  wait_for_dashboard_hardware_ready "$container" true true

  open_kiosk_browser
  echo "[launch] saved-map navigation and kiosk started"

  echo
  cmd_status
}

ensure_demo_backend() {
  local app_url deadline
  app_url="$(resolve_app_url "/" "")" || return 1

  case "$DEMO_START_LARAVEL" in
    true)
      if [ ! -x "${REPO_ROOT}/reservationApp/vendor/bin/sail" ]; then
        echo "[demo] Laravel Sail is unavailable. Run Composer installation first." >&2
        return 1
      fi
      echo "[demo] starting Laravel services through Sail"
      (
        cd "${REPO_ROOT}/reservationApp"
        ./vendor/bin/sail up -d
      )
      ;;
    false) ;;
    *)
      echo "[demo] DEMO_START_LARAVEL must be true or false" >&2
      return 1
      ;;
  esac

  if ! [[ "$DEMO_BACKEND_START_TIMEOUT_SEC" =~ ^[1-9][0-9]*$ ]]; then
    echo "[demo] DEMO_BACKEND_START_TIMEOUT_SEC must be a positive integer" >&2
    return 1
  fi
  deadline=$((SECONDS + DEMO_BACKEND_START_TIMEOUT_SEC))
  while (( SECONDS < deadline )); do
    if curl --silent --show-error \
      --output /dev/null \
      --connect-timeout 2 \
      --max-time 3 \
      "$app_url"; then
      echo "[demo] Laravel reachable at ${app_url}"
      return 0
    fi
    sleep 1
  done

  echo "[demo] Laravel did not become reachable at ${app_url}" >&2
  return 1
}

cmd_demo() {
  case "${1:-${DEFAULT_DEMO_MAP}}" in
    help|-h|--help)
      echo "Usage: ./scripts/robot.sh demo [home|school]"
      echo "Default demo map: ${DEFAULT_DEMO_MAP}"
      return 0
      ;;
    home)
      RECEPTION_WAYPOINT_CONFIG_PATH="$HOME_RECEPTION_WAYPOINT_CONFIG_PATH"
      MAP_PATH="$HOME_MAP_PATH"
      ;;
    school)
      if [ -z "$SCHOOL_RECEPTION_WAYPOINT_CONFIG_PATH" ]; then
        echo "[demo] School reception coordinates are not configured yet." >&2
        echo "[demo] Set SCHOOL_RECEPTION_WAYPOINT_CONFIG_PATH after measuring Reception, Mante Inc Room, and Bayer Inc Room." >&2
        return 1
      fi
      RECEPTION_WAYPOINT_CONFIG_PATH="$SCHOOL_RECEPTION_WAYPOINT_CONFIG_PATH"
      MAP_PATH="$SCHOOL_MAP_PATH"
      ;;
    *)
      echo "Usage: ./scripts/robot.sh demo [home|school]" >&2
      return 1
      ;;
  esac

  local demo_map="${1:-${DEFAULT_DEMO_MAP}}"
  resolve_reception_validation_url >/dev/null
  resolve_kiosk_url >/dev/null
  ensure_demo_backend

  if [ "$DEMO_CLEAN_START" = "true" ]; then
    echo "[demo] stopping stale services before the ${demo_map} demo"
    cmd_stop all
  elif [ "$DEMO_CLEAN_START" != "false" ]; then
    echo "[demo] DEMO_CLEAN_START must be true or false" >&2
    return 1
  fi

  local demo_profile
  case "$DEMO_REAL_NAVIGATION" in
    true)
      if [ -z "$MAP_PATH" ] || [ -z "$RECEPTION_WAYPOINT_CONFIG_PATH" ]; then
        echo "[demo] real navigation requires explicit map and waypoint paths" >&2
        return 1
      fi
      AUTOMATIC_RETURN_ENABLED="$REAL_AUTOMATIC_RETURN_ENABLED"
      demo_profile=demo-navigation
      ;;
    false)
      AUTOMATIC_RETURN_ENABLED=true
      demo_profile=stationary-reception-real
      ;;
    *)
      echo "[demo] DEMO_REAL_NAVIGATION must be true or false" >&2
      return 1
      ;;
  esac

  if ! cmd_start "$demo_profile"; then
    echo "[demo] service startup failed; stopping the partial demo stack" >&2
    cmd_stop "$demo_profile"
    return 1
  fi
  if [ "$DEMO_REAL_NAVIGATION" = "true" ]; then
    local container
    container="$(require_container)"
    if ! wait_for_real_reception_navigation_ready "$container"; then
      echo "[demo] navigation readiness failed; stopping the partial demo stack" >&2
      cmd_stop "$demo_profile"
      return 1
    fi
  fi
  if ! open_kiosk_browser; then
    echo "[demo] kiosk failed; stopping the partial demo stack" >&2
    cmd_stop "$demo_profile"
    return 1
  fi

  echo "[demo] ${demo_map} reception ready"
  if [ "$DEMO_REAL_NAVIGATION" = "true" ]; then
    echo "[demo] REAL NAVIGATION ACTIVE: verified outbound guidance can move the robot"
    if [ "$REAL_AUTOMATIC_RETURN_ENABLED" = "true" ]; then
      echo "[demo] B5 return enabled: Reception return can also move the robot"
    else
      echo "[demo] B4 mode: automatic Reception return is disabled"
    fi
  else
    echo "[demo] real camera/voice/QR/Laravel; forced simulated guidance and return"
  fi
}

cmd_start() {
  local target="${1:-}"
  local map_arg="${2:-}"
  [ -n "$target" ] || { echo "Usage: ./scripts/robot.sh start <service|base|map|navigate|reception|voice|camera-qr|stationary-reception|stationary-reception-real|kiosk>" >&2; exit 1; }
  case "$target" in
    all|robot)
      echo "Unsupported broad profile: ${target}" >&2
      exit 1
      ;;
  esac

  if [ "$target" = "navigate" ] && [ -n "$map_arg" ]; then
    MAP_PATH="$(resolve_map_path_arg "$map_arg")"
  fi

  ensure_tmux
  local container
  container="$(require_container)"

  local services
  services="$(expand_profile "$target")"
  if [[ " ${services} " == *" vision "* ]]; then
    if ! ensure_qr_decoder_in_docker "$container" || \
       ! validate_person_detection_config "$container"; then
      return 1
    fi
  fi
  if [[ " ${services} " == *" reception "* ]]; then
    if ! resolve_reception_validation_url >/dev/null; then
      return 1
    fi
  fi
  if [[ " ${services} " == *" voice "* ]]; then
    if ! ensure_webrtc_microphone || ! validate_voice_config "$container"; then
      return 1
    fi
  fi
  if [ "$target" = "kiosk" ] || [ "$target" = "launch" ]; then
    if ! resolve_kiosk_url >/dev/null; then
      return 1
    fi
  fi

  # Profiles with robot bringup require a live base before localization, Nav2,
  # or dashboard teleop can be considered ready.
  if [[ " ${services} " == *" bringup "* ]]; then
    if ! start_service bringup "$container" || \
       ! disable_legacy_joystick_control "$container" || \
       ! cmd_mcu; then
      return 1
    fi
  fi

  local s
  for s in $services; do
    [ "$s" = "bringup" ] && continue
    if ! start_service "$s" "$container"; then
      return 1
    fi
    # Validate the lightweight dashboard before starting Nav2's larger set of
    # processes. This prevents startup contention on the Jetson and makes the
    # failing service unambiguous.
    if [ "$s" = "web" ]; then
      if ! wait_for_web_ready "$container"; then
        stop_service web "$container"
        return 1
      fi
    fi
  done
  if [[ " ${services} " == *" nav "* ]]; then
    if ! wait_for_navigation_ready "$container"; then
      return 1
    fi
  fi
  if [[ " ${services} " == *" bringup "* ]] && \
     [[ " ${services} " == *" web "* ]]; then
    local require_motion=false
    if [[ " ${services} " == *" teleop "* ]] || \
       [[ " ${services} " == *" nav "* ]] || \
       [[ " ${services} " == *" slam "* ]]; then
      require_motion=true
    fi
    if ! wait_for_dashboard_hardware_ready "$container" true "$require_motion"; then
      return 1
    fi
  fi
  if [ "$target" = "stationary-reception" ] || \
     [ "$target" = "stationary-reception-real" ]; then
    if ! wait_for_stationary_reception_ready "$container" "$target"; then
      return 1
    fi
  fi

  if [ "$target" = "kiosk" ] || [ "$target" = "launch" ]; then
    open_kiosk_browser
  fi

  echo "[start] ${target} started. Logs: ./scripts/robot.sh logs <service>"
}

cmd_kiosk() {
  case "${1:-open}" in
    open|"")
      open_kiosk_browser
      ;;
    stop|close)
      stop_kiosk_browser
      ;;
    help|-h|--help)
      echo "Usage: ./scripts/robot.sh kiosk [open|stop|url]"
      echo "Default URL: $(resolve_kiosk_url 2>/dev/null || printf '<set APP_HOST first>')"
      ;;
    *)
      open_kiosk_browser "$1"
      ;;
  esac
}

cmd_nav() {
  MAP_PATH="$(resolve_map_path_arg "${1:-}")"
  echo "[nav] using map: ${MAP_PATH}"
  cmd_start navigate
}

cmd_stop() {
  local target="${1:-}"
  [ -n "$target" ] || { echo "Usage: ./scripts/robot.sh stop <service|mode|all>" >&2; exit 1; }

  local container
  container="$(require_container)"

  local services s
  if [ "$target" = "all" ]; then
    services="${ALL_SERVICES}"
    _ssh "tmux kill-session -t ${FOXGLOVE_SESSION} 2>/dev/null || true"
    stop_kiosk_browser
  elif [ "$target" = "kiosk" ] || [ "$target" = "launch" ] || \
       [ "$target" = "demo" ]; then
    services="$(expand_profile "$target")"
    stop_kiosk_browser
  else
    services="$(expand_profile "$target")"
  fi

  for s in $services; do
    stop_service "$s" "$container"
  done
}

cmd_restart() {
  local target="${1:-}"
  [ -n "$target" ] || { echo "Usage: ./scripts/robot.sh restart <mode>" >&2; exit 1; }
  cmd_stop all
  sleep 2
  cmd_start "$target"
}

cmd_mcu() {
  local force=""
  [ "${1:-}" = "--force" ] && force=1

  local container session_established=false
  container="$(require_container)"

  echo "[mcu] robot=${container} service=${MICRO_ROS_SERVICE} topic=${MCU_PROBE_TOPIC}"
  if [ -z "$force" ] && mcu_is_alive "$container"; then
    echo "[mcu] base board is already publishing"
  else
    if ! restart_micro_ros_service; then
      report_mcu_diagnostics "$container"
      exit 1
    fi
    echo "[mcu] waiting for the MCU XRCE session"
    if wait_for_micro_ros_session; then
      session_established=true
      echo "[mcu] MCU XRCE session established"
    else
      echo "[mcu] no XRCE session marker found in the agent log; continuing with the message probe" >&2
    fi
    echo "[mcu] waiting up to 30 seconds for ${MCU_PROBE_TOPIC}"
    if ! wait_for_mcu "$container"; then
      report_mcu_diagnostics "$container"
      if [ "$session_established" = true ]; then
        echo "[mcu] XRCE is connected and ROS publishers exist, but the MCU firmware is not streaming data." >&2
        echo "[mcu] Stop here and use the board's documented physical reset or power-cycle procedure before retrying." >&2
      fi
      echo "[mcu] ${MCU_PROBE_TOPIC} was discovered or expected, but no message was received after service recovery." >&2
      exit 1
    fi
  fi

  echo "[mcu] ready: ${MCU_PROBE_TOPIC} is live"
}

cmd_map_foxglove() {
  ensure_tmux
  local container
  container="$(require_container)"
  require_evo_ws_built "$container"
  require_foxglove_bridge "$container"

  ROSBRIDGE=true cmd_start map
  start_foxglove_bridge "$container"

  cat <<EOF

Mapping is running.
Foxglove: ws://${JETSON_IP}:${FOXGLOVE_PORT}
Dashboard rosbridge: ws://${JETSON_IP}:${ROSBRIDGE_PORT}

When finished:
  ./scripts/robot.sh save-map ground_floor
  ./scripts/robot.sh map stop
EOF
}

cmd_map_rviz() {
  ensure_tmux
  local container
  container="$(require_container)"
  require_evo_ws_built "$container"

  if _ssh "tmux has-session -t evo_slam 2>/dev/null"; then
    echo "[rviz] the SLAM service is already running." >&2
    echo "[rviz] stop it before changing display mode: ./scripts/robot.sh map stop" >&2
    return 1
  fi

  prepare_robot_display "$container"
  SLAM_RVIZ=true cmd_start map
  wait_for_rviz "$container"

  cat <<EOF

Mapping is running with RViz on the robot display.

When finished:
  ./scripts/robot.sh save-map school_v2
  ./scripts/robot.sh map stop
EOF
}

cmd_save_map() {
  local map_name="${1:-map_$(date +%Y%m%d_%H%M%S)}"
  if [[ ! "$map_name" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; then
    echo "Invalid map name: ${map_name}" >&2
    echo "Use letters, numbers, underscores, or hyphens." >&2
    exit 1
  fi

  local container
  container="$(require_container)"
  save_slam_map "$container" "$map_name"

  echo
  echo "Launch it with:"
  echo "  ./scripts/robot.sh nav ${map_name}"
}

cmd_map_status() {
  local container
  container="$(require_container)"

  echo "Robot: ${JETSON_USER}@${JETSON_IP}"
  echo "Container: ${container}"
  echo "Foxglove: ws://${JETSON_IP}:${FOXGLOVE_PORT}"
  echo "Dashboard rosbridge: ws://${JETSON_IP}:${ROSBRIDGE_PORT}"
  echo
  _ssh "tmux ls 2>/dev/null | grep -E '^evo_(bringup|camera|slam|web|foxglove):' || echo 'mapping stack is not running'"
}

cmd_map_stop() {
  local container
  container="$(require_container)"
  _ssh "tmux kill-session -t ${FOXGLOVE_SESSION} 2>/dev/null || true"
  _ssh "docker exec ${container} bash -lc 'pkill -TERM -f \"[f]oxglove_bridge\" 2>/dev/null || true'"
  cmd_stop map
  echo "[map] stopped"
}

cmd_map() {
  case "${1:-}" in
    rviz) cmd_map_rviz ;;
    foxglove|start) cmd_map_foxglove ;;
    status) cmd_map_status ;;
    stop) cmd_map_stop ;;
    save) shift; cmd_save_map "${1:-}" ;;
    help|-h|--help)
      echo "Usage: ./scripts/robot.sh map rviz|foxglove|status|stop|save [map-name]"
      ;;
    "") echo "Usage: ./scripts/robot.sh map rviz|foxglove|status|stop|save [map-name]" >&2; exit 1 ;;
    *) echo "Unknown map command: $1" >&2; exit 1 ;;
  esac
}

cmd_status() {
  local container
  container="$(resolve_container)"

  echo "Robot: ${JETSON_USER}@${JETSON_IP:-<not configured>}"
  echo "Container: ${container:-<none>}"
  echo

  echo "tmux sessions:"
  _ssh "tmux ls 2>/dev/null | grep '^evo_' || echo 'none'"

  echo
  echo "micro-ROS service:"
  _ssh "systemctl is-active ${MICRO_ROS_SERVICE} 2>/dev/null || true"

  [ -n "$container" ] || return 0

  echo
  echo "ROS topics:"
  _ssh "docker exec ${container} bash -lc '$(_ros_prelude); ros2 topic list 2>/dev/null | grep -E \"/scan|/odom|/cmd_vel|/camera/color/image_raw|/vision/qr/detections|/reception/qr/status\" || echo \"none\"'"

  echo
  if mcu_is_alive "$container"; then
    echo "MCU: publishing ${MCU_PROBE_TOPIC}"
  else
    echo "MCU: silent, run ./scripts/robot.sh mcu"
  fi

  echo
  _port_check "${CAMERA_PORT}" "camera/web"
  _port_check "${ROSBRIDGE_PORT}" "rosbridge"
}

_port_check() {
  local port="$1" label="$2"
  if nc -z -w 3 "${JETSON_IP}" "${port}" 2>/dev/null; then
    echo "${port} (${label}): open"
  else
    echo "${port} (${label}): closed"
  fi
}

cmd_health() {
  jetson_health
}

cmd_logs() {
  local name="${1:-}"
  [ -n "$name" ] || { echo "Usage: ./scripts/robot.sh logs <service>" >&2; exit 1; }
  local log_path
  log_path="$(remote_quote "${SERVICE_LOG_DIR}/evo_${name}.log")"
  _ssh_tty "
    if tmux has-session -t evo_${name} 2>/dev/null; then
      tmux attach -t evo_${name}
    elif [ -f ${log_path} ]; then
      echo '[logs] service is not running; showing startup and final output'
      echo '--- startup ---'
      sed -n '1,80p' ${log_path}
      echo '--- final ---'
      tail -n 120 ${log_path}
    else
      echo '[logs] no running session or captured log for evo_${name}' >&2
      exit 1
    fi
  "
}

_set_local() {
  local key="$1" val="${2:-}" lf="${SCRIPT_DIR}/config.local.sh"
  [ -n "$val" ] || { echo "Missing value for ${key}" >&2; exit 1; }
  touch "$lf"
  grep -v "${key}:=" "$lf" > "${lf}.tmp" 2>/dev/null || true
  echo ": \"\${${key}:=${val}}\"" >> "${lf}.tmp"
  mv "${lf}.tmp" "$lf"
  echo "[config] ${key}=${val}"
}

cmd_config() {
  case "${1:-}" in
    show)
      local detected_app_host effective_kiosk_url effective_validation_url
      detected_app_host="$(detect_app_host 2>/dev/null || true)"
      effective_kiosk_url="$(resolve_kiosk_url 2>/dev/null || true)"
      effective_validation_url="$(resolve_reception_validation_url 2>/dev/null || true)"
      echo "JETSON_IP=${JETSON_IP:-<not configured>}"
      echo "JETSON_USER=${JETSON_USER}"
      echo "CONTAINER=${CONTAINER}"
      echo "AGENT_CONTAINER=${AGENT_CONTAINER}"
      echo "MICRO_ROS_SERVICE=${MICRO_ROS_SERVICE}"
      echo "MICRO_ROS_SERIAL_DEVICE=${MICRO_ROS_SERIAL_DEVICE}"
      echo "MCU_PROBE_TOPIC=${MCU_PROBE_TOPIC}"
      echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
      echo "SLAM_USE_COLLISION_MONITOR=${SLAM_USE_COLLISION_MONITOR}"
      echo "NAV_USE_COLLISION_MONITOR=${NAV_USE_COLLISION_MONITOR}"
      echo "APP_HOST=${APP_HOST:-${detected_app_host:-<auto unavailable>}}"
      echo "APP_PORT=${APP_PORT}"
      echo "CAMERA_PORT=${CAMERA_PORT}"
      echo "ROSBRIDGE_PORT=${ROSBRIDGE_PORT}"
      echo "PERSON_DETECTION_ENABLED=${PERSON_DETECTION_ENABLED}"
      echo "PERSON_DETECTION_MODEL_PATH=${PERSON_DETECTION_MODEL_PATH}"
      echo "PERSON_DETECTION_CONFIDENCE=${PERSON_DETECTION_CONFIDENCE}"
      echo "PERSON_DETECTION_NMS=${PERSON_DETECTION_NMS}"
      echo "PERSON_DETECTION_MAX_FPS=${PERSON_DETECTION_MAX_FPS}"
      echo "APPROACH_MIN_CONFIDENCE=${APPROACH_MIN_CONFIDENCE}"
      echo "APPROACH_MIN_DISTANCE_M=${APPROACH_MIN_DISTANCE_M}"
      echo "APPROACH_MAX_DISTANCE_M=${APPROACH_MAX_DISTANCE_M}"
      echo "APPROACH_DEBOUNCE_FRAMES=${APPROACH_DEBOUNCE_FRAMES}"
      echo "APPROACH_COOLDOWN_SEC=${APPROACH_COOLDOWN_SEC}"
      echo "PRESENCE_GREETING_FALLBACK_SEC=${PRESENCE_GREETING_FALLBACK_SEC}"
      echo "INTENT_TIMEOUT_SEC=${INTENT_TIMEOUT_SEC}"
      echo "QR_INACTIVITY_TIMEOUT_SEC=${QR_INACTIVITY_TIMEOUT_SEC}"
      echo "RECEPTION_ALLOWED_DESTINATION_IDS=${RECEPTION_ALLOWED_DESTINATION_IDS}"
      echo "RECEPTION_WAYPOINT_CONFIG_PATH=${RECEPTION_WAYPOINT_CONFIG_PATH:-<Home default>}"
      echo "DEFAULT_DEMO_MAP=${DEFAULT_DEMO_MAP}"
      echo "HOME_RECEPTION_WAYPOINT_CONFIG_PATH=${HOME_RECEPTION_WAYPOINT_CONFIG_PATH:-<packaged Home registry>}"
      echo "SCHOOL_RECEPTION_WAYPOINT_CONFIG_PATH=${SCHOOL_RECEPTION_WAYPOINT_CONFIG_PATH:-<not configured>}"
      echo "DEMO_START_LARAVEL=${DEMO_START_LARAVEL}"
      echo "DEMO_REAL_NAVIGATION=${DEMO_REAL_NAVIGATION}"
      echo "HOME_MAP_PATH=${HOME_MAP_PATH:-<not configured>}"
      echo "SCHOOL_MAP_PATH=${SCHOOL_MAP_PATH:-<not configured>}"
      echo "REAL_NAVIGATION_TIMEOUT_SEC=${REAL_NAVIGATION_TIMEOUT_SEC}"
      echo "REAL_LOCALIZATION_TIMEOUT_SEC=${REAL_LOCALIZATION_TIMEOUT_SEC}"
      echo "REAL_MAX_LOCALIZATION_XY_VARIANCE=${REAL_MAX_LOCALIZATION_XY_VARIANCE}"
      echo "REAL_AUTOMATIC_RETURN_ENABLED=${REAL_AUTOMATIC_RETURN_ENABLED}"
      echo "STT_MODEL_PATH=${STT_MODEL_PATH:-<not configured>}"
      echo "WEBRTC_MIC_ENABLED=${WEBRTC_MIC_ENABLED}"
      echo "WEBRTC_MIC_SOURCE_NAME=${WEBRTC_MIC_SOURCE_NAME}"
      echo "DEFAULT_MAP_NAME=${DEFAULT_MAP_NAME}"
      echo "PACKAGED_MAP_PATH=${PACKAGED_MAP_PATH}"
      echo "MAP_PATH=${MAP_PATH}"
      echo "DOCKER_MAP_DIR=${DOCKER_MAP_DIR}"
      echo "HOST_MAP_DIR=${HOST_MAP_DIR}"
      echo "RECEPTION_VALIDATION_URL=${RECEPTION_VALIDATION_URL:-${effective_validation_url:-<auto unavailable>}}"
      echo "KIOSK_URL=${KIOSK_URL:-${effective_kiosk_url:-<auto unavailable>}}"
      echo "KIOSK_DISPLAY=${KIOSK_DISPLAY}"
      ;;
    ip)        _set_local JETSON_IP "${2:-}" ;;
    app-host)  _set_local APP_HOST "${2:-}" ;;
    app-port)  _set_local APP_PORT "${2:-}" ;;
    container) _set_local CONTAINER "${2:-}" ;;
    user)      _set_local JETSON_USER "${2:-}" ;;
    map)       _set_local MAP_PATH "$(resolve_map_path_arg "${2:-}")" ;;
    *) echo "Usage: ./scripts/robot.sh config ip|app-host|app-port|container|user|map|show [value]" >&2; exit 1 ;;
  esac
}

case "${1:-}" in
  demo)     shift; cmd_demo "$@" ;;
  launch)   shift; cmd_launch "$@" ;;
  setup)    shift; cmd_setup "$@" ;;
  sync-maps) shift; cmd_sync_maps "$@" ;;
  kiosk)    shift; cmd_kiosk "$@" ;;
  start)    shift; cmd_start "$@" ;;
  nav)      shift; cmd_nav "$@" ;;
  map)      shift; cmd_map "$@" ;;
  save-map) shift; cmd_save_map "$@" ;;
  stop)     shift; cmd_stop "$@" ;;
  restart)  shift; cmd_restart "$@" ;;
  mcu)      shift; cmd_mcu "$@" ;;
  status)   shift; cmd_status "$@" ;;
  health)   shift; cmd_health "$@" ;;
  logs)     shift; cmd_logs "$@" ;;
  config)   shift; cmd_config "$@" ;;
  ""|-h|--help|help) usage ;;
  *) echo "Unknown command: $1" >&2; echo; usage; exit 1 ;;
esac
