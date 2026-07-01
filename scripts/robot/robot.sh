#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LAST_PROFILE_FILE="${SCRIPT_DIR}/.last_profile"

. "${SCRIPT_DIR}/config.sh"
. "${SCRIPT_DIR}/lib.sh"

usage() {
  cat <<EOF
Usage: ./scripts/robot.sh <command> [args]

Main commands:
  config ip <ip>              Save the current Jetson IP
  config show                 Show active robot settings
  config app-host <ip>        Save the Mac/app IP reachable from the Jetson
  launch [map-name|path]      Start saved-map navigation plus robot kiosk
  setup                       Push local evo_ws/src to Jetson, copy into Docker, build
  setup-kiosk                 Install QR/kiosk runtime packages in the current Docker container
  recover [mode]              Seed Docker from Jetson cache, start a mode, wake MCU
  sync-maps [map-name|path]   Copy a saved Jetson host map into the current Docker container
  kiosk [url|stop]            Open or close the kiosk page on the Jetson display

Launch modes:
  launch                      saved school map + camera + QR scanner + kiosk screen
  start base                  bringup + camera + vision + web
  start map                   bringup + camera + SLAM + web
  start navigate              use MAP_PATH or default /root/maps/school_map.yaml
  start reception             camera + QR scanner + QR validation bridge + web
  start stationary            apartment-safe mock navigation orchestrator only
  start kiosk                 reception mode plus kiosk browser on the robot screen
  nav [map-name|path.yaml]    launch saved-map navigation
  map foxglove                create a map with Foxglove
  save-map [map-name]         save the current SLAM map

Operations:
  status                      tmux sessions, ROS topics, MCU, ports
  logs <service>              attach service logs, detach with Ctrl-b then d
  stop <service|mode|all>     stop services
  restart [mode]              restart the last mode, or a given mode
  mcu [--force]               wake the micro-ROS base board
  health                      Jetson health snapshot
  safety                      show stationary navigation safety parameters/topics

Services: bringup camera vision reception stationary_nav web slam nav
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
  echo "[deploy] copying Jetson host workspace into Docker (${container})"
  _ssh "docker exec ${container} rm -rf ${DOCKER_WS} && docker exec ${container} mkdir -p ${DOCKER_WS} && docker cp ${HOST_WS}/. ${container}:${DOCKER_WS}"
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

cmd_setup() {
  if [ "${1:-}" = "--push" ]; then
    echo "[setup] --push is now the default workflow"
  elif [ -n "${1:-}" ]; then
    echo "Usage: ./scripts/robot.sh setup" >&2
    exit 1
  fi

  ensure_tmux
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
      echo "Usage: ./scripts/sync_maps.sh [map-name|/root/maps/name.yaml]"
      echo "Default: ${MAP_PATH}"
      return 0
      ;;
  esac

  local map_name docker_map_path container
  docker_map_path="$(resolve_map_path_arg "${1:-}")"
  map_name="$(map_name_from_path "$docker_map_path")"
  container="$(require_container)"

  echo "[sync-maps] syncing ${map_name} into Docker (${container})"
  sync_map_from_host "$container" "$docker_map_path"
}

cmd_setup_kiosk() {
  ensure_tmux
  local container kiosk_url validation_url
  container="$(require_container)"

  ensure_qr_decoder_in_docker "$container"

  kiosk_url="$(resolve_kiosk_url 2>/dev/null || true)"
  validation_url="$(resolve_reception_validation_url 2>/dev/null || true)"

  echo "[setup-kiosk] container=${container}"
  echo "[setup-kiosk] kiosk=${kiosk_url:-<set APP_HOST with ./scripts/robot.sh config app-host <mac-ip>>}"
  echo "[setup-kiosk] validation=${validation_url:-<set APP_HOST with ./scripts/robot.sh config app-host <mac-ip>>}"
  echo "[setup-kiosk] done"
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

  local s
  for s in bringup camera nav vision reception web; do
    start_service "$s" "$container"
  done

  open_kiosk_browser
  echo "launch" > "${LAST_PROFILE_FILE}"
  echo "[launch] saved-map navigation and kiosk started"

  cmd_mcu
  echo
  cmd_status
}

cmd_start() {
  local target="${1:-}"
  local map_arg="${2:-}"
  [ -n "$target" ] || { echo "Usage: ./scripts/robot.sh start <service|base|map|navigate|all>" >&2; exit 1; }

  if [ "$target" = "navigate" ] && [ -n "$map_arg" ]; then
    MAP_PATH="$(resolve_map_path_arg "$map_arg")"
  fi

  ensure_tmux
  local container
  container="$(require_container)"

  local services
  services="$(expand_profile "$target")"
  if [[ " ${services} " == *" vision "* ]]; then
    ensure_qr_decoder_in_docker "$container"
  fi
  if [[ " ${services} " == *" reception "* ]]; then
    resolve_reception_validation_url >/dev/null
  fi
  if [ "$target" = "kiosk" ] || [ "$target" = "robot" ] || [ "$target" = "launch" ]; then
    resolve_kiosk_url >/dev/null
  fi

  local s
  for s in $services; do
    start_service "$s" "$container"
  done

  if [ "$target" = "kiosk" ] || [ "$target" = "robot" ] || [ "$target" = "launch" ]; then
    open_kiosk_browser
  fi

  echo "$target" > "${LAST_PROFILE_FILE}"
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
  elif [ "$target" = "kiosk" ] || [ "$target" = "robot" ] || [ "$target" = "launch" ]; then
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
  if [ -z "$target" ]; then
    target="$(cat "${LAST_PROFILE_FILE}" 2>/dev/null || true)"
    [ -n "$target" ] || { echo "No previous mode. Use: ./scripts/robot.sh restart <mode>" >&2; exit 1; }
  fi
  cmd_stop all
  sleep 2
  cmd_start "$target"
}

cmd_mcu() {
  local force=""
  [ "${1:-}" = "--force" ] && force=1

  local container agent
  container="$(require_container)"
  agent="$(resolve_agent_container)"
  [ -n "$agent" ] || { echo "No active micro-ROS agent container found." >&2; exit 1; }

  echo "[mcu] robot=${container} agent=${agent} topic=${MCU_PROBE_TOPIC}"
  if [ -z "$force" ] && mcu_is_alive "$container"; then
    echo "[mcu] base board is already publishing"
  else
    echo "[mcu] restarting micro-ROS agent"
    _ssh "docker restart ${agent}" >/dev/null
    if ! wait_for_mcu "$container"; then
      echo "[mcu] base board is still silent. Use the physical reset button." >&2
      exit 1
    fi
  fi

  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc '
    source /opt/ros/humble/setup.bash 2>/dev/null
    for t in /odom_raw /imu/data_raw /joint_states; do
      printf \"  %-16s \" \"\$t\"
      timeout 5 ros2 topic hz \$t 2>/dev/null | grep \"average rate\" | head -1 || echo \"silent\"
    done'"
}

cmd_recover() {
  ensure_tmux
  local profile="${1:-}"
  if [ -z "$profile" ]; then
    profile="$(cat "${LAST_PROFILE_FILE}" 2>/dev/null || true)"
    [ -n "$profile" ] || profile="map"
  fi

  local container
  container="$(require_container)"
  echo "[recover] mode=${profile} container=${container}"

  if [[ " $(expand_profile "$profile") " == *" nav "* ]]; then
    ensure_map_in_docker "$container" "$MAP_PATH"
  fi

  ensure_evo_ws_built "$container"

  cmd_start "$profile"
  cmd_mcu
  echo
  cmd_status
}

cmd_map_foxglove() {
  ensure_tmux
  local container
  container="$(require_container)"
  require_foxglove_bridge "$container"

  ROSBRIDGE=true cmd_start map
  start_foxglove_bridge "$container"

  cat <<EOF

Mapping is running.
Foxglove: ws://${JETSON_IP}:${FOXGLOVE_PORT}
Dashboard rosbridge: ws://${JETSON_IP}:9090

When finished:
  ./scripts/robot.sh save-map ground_floor
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
  echo "Dashboard rosbridge: ws://${JETSON_IP}:9090"
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
  case "${1:-foxglove}" in
    foxglove|start) cmd_map_foxglove ;;
    status) cmd_map_status ;;
    stop) cmd_map_stop ;;
    save) shift; cmd_save_map "${1:-}" ;;
    help|-h|--help)
      echo "Usage: ./scripts/robot.sh map foxglove|status|stop|save [map-name]"
      ;;
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
  _port_check 9090 "rosbridge"
}

cmd_safety() {
  local container
  container="$(require_container)"

  echo "Stationary navigation safety:"
  _ssh "docker exec ${container} bash -lc '$(_ros_prelude)
    ros2 param get /navigation_orchestrator_node mock_navigation
    ros2 param get /navigation_orchestrator_node allow_real_navigation
    echo Actions:
    ros2 action list
    echo Navigation-status-topic:
    ros2 topic info /reception/navigation/status
    echo Cmd-vel-topic:
    ros2 topic info /cmd_vel || echo /cmd_vel-not-present_expected-in-stationary-only-mode'"
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
  _ssh_tty "tmux attach -t evo_${name}"
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
      echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
      echo "APP_HOST=${APP_HOST:-${detected_app_host:-<auto unavailable>}}"
      echo "APP_PORT=${APP_PORT}"
      echo "DEFAULT_MAP_NAME=${DEFAULT_MAP_NAME}"
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
  launch)   shift; cmd_launch "$@" ;;
  recover)  shift; cmd_recover "$@" ;;
  setup)    shift; cmd_setup "$@" ;;
  setup-kiosk) shift; cmd_setup_kiosk "$@" ;;
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
  safety)   shift; cmd_safety "$@" ;;
  health)   shift; cmd_health "$@" ;;
  logs)     shift; cmd_logs "$@" ;;
  config)   shift; cmd_config "$@" ;;
  ""|-h|--help|help) usage ;;
  *) echo "Unknown command: $1" >&2; echo; usage; exit 1 ;;
esac
