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

_ssh() {
  require_jetson_ip || return 1
  ssh -o ConnectTimeout=8 "${JETSON_USER}@${JETSON_IP}" "$@"
}

_ssh_tty() {
  require_jetson_ip || return 1
  ssh -t -o ConnectTimeout=8 "${JETSON_USER}@${JETSON_IP}" "$@"
}

remote_quote() { printf "%s" "$1" | sed "s/'/'\\\\''/g; 1s/^/'/; \$s/\$/'/"; }

_ros_prelude() {
  printf '%s' \
"source /opt/ros/humble/setup.bash; \
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true; \
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true; \
source /root/evo_ws/install/setup.bash; \
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID}; \
export FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS}"
}

# --- Docker container --------------------------------------------------------

# Resolve the m3pro container. `auto` picks the running container that contains
# the Yahboom workspace (/root/M3Pro_ws), then falls back to the first container.
resolve_container() {
  if [ "${CONTAINER}" != "auto" ]; then
    printf '%s\n' "${CONTAINER}"
    return
  fi
  _ssh 'c=""; for n in $(docker ps --format "{{.Names}}"); do
      if docker exec "$n" test -d /root/M3Pro_ws 2>/dev/null; then c="$n"; break; fi
    done
    [ -n "$c" ] && printf "%s\n" "$c" || docker ps --format "{{.Names}}" | head -n1'
}

# Resolve the micro-ROS agent container. Its name changes when restarted, so the
# image name is preferred, then any running container that is not the m3pro one.
resolve_agent_container() {
  if [ "${AGENT_CONTAINER}" != "auto" ]; then
    printf '%s\n' "${AGENT_CONTAINER}"
    return
  fi
  _ssh 'a="$(docker ps --format "{{.Names}} {{.Image}}" | awk "/micro-?ros/ {print \$1; exit}")"
    if [ -z "$a" ]; then
      for n in $(docker ps --format "{{.Names}}"); do
        docker exec "$n" test -d /root/M3Pro_ws 2>/dev/null || { a="$n"; break; }
      done
    fi
    printf "%s\n" "$a"'
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
  echo "[evo_ws] seeding from host: ${HOST_WS} -> ${container}:${DOCKER_WS}"
  _ssh "docker exec ${container} mkdir -p ${DOCKER_WS} && docker cp ${HOST_WS}/. ${container}:${DOCKER_WS}"
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

  echo "[maps] ${docker_yaml} is missing in Docker. Syncing from ${HOST_MAP_DIR}."
  sync_map_from_host "$container" "$docker_yaml"
}

# --- MCU micro-ROS : santé / réveil -----------------------------------------

# Vrai (0) si la carte (MCU) publie : on sonde le flux du topic témoin sur domaine 30.
# `ros2 topic hz` n'imprime "average rate" que si des messages arrivent réellement —
# distingue donc un endpoint vivant d'un topic fantôme (publisher déclaré mais muet).
mcu_is_alive() {
  local container="$1"
  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc '
    source /opt/ros/humble/setup.bash 2>/dev/null
    timeout 6 ros2 topic hz ${MCU_PROBE_TOPIC} 2>/dev/null | grep -q \"average rate\"'"
}

# Attend que le MCU se remette à publier (poll toutes les 2 s, ~20 s max). Renvoie 0 dès
# que le flux est détecté, 1 sinon. Pas de sleep fixe aveugle : on s'arrête à la condition.
wait_for_mcu() {
  local container="$1" i
  for i in $(seq 1 10); do
    if mcu_is_alive "$container"; then return 0; fi
    sleep 2
  done
  return 1
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

qr_decoder_available() {
  local container="$1" probe
  probe='python3 -c "from pyzbar.pyzbar import decode; print(\"pyzbar/zbar ok\")"'
  _ssh "docker exec ${container} bash -lc $(remote_quote "$probe")"
}

install_qr_decoder_in_docker() {
  local container="$1"
  local remote_env
  remote_env="CONTAINER=$(remote_quote "$container")"

  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

docker exec -i -u 0 "$CONTAINER" bash -s <<'CONTAINER_SCRIPT'
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
if ! apt-get install -y --no-install-recommends libzbar0 python3-pyzbar; then
  apt-get install -y --no-install-recommends libzbar0 python3-pip
  python3 -m pip install --break-system-packages pyzbar || python3 -m pip install pyzbar
fi

python3 -c "from pyzbar.pyzbar import decode; print('pyzbar/zbar ok')"
CONTAINER_SCRIPT
REMOTE_SCRIPT
}

ensure_qr_decoder_in_docker() {
  local container="$1"
  if qr_decoder_available "$container" >/dev/null 2>&1; then
    echo "[kiosk] QR decoder ready in Docker (${container})"
    return 0
  fi

  echo "[kiosk] installing QR decoder in Docker (${container}): libzbar0 + python3-pyzbar"
  install_qr_decoder_in_docker "$container"
  echo "[kiosk] QR decoder ready"
}

require_foxglove_bridge() {
  local container="$1"
  if ! _ssh "docker exec ${container} bash -lc 'source /opt/ros/humble/setup.bash && ros2 pkg prefix foxglove_bridge >/dev/null 2>&1'"; then
    cat >&2 <<EOF
foxglove_bridge is not installed inside Docker.

Install once:
  ssh ${JETSON_USER}@${JETSON_IP}
  docker exec -it ${container} bash -lc 'apt-get update && apt-get install -y ros-humble-foxglove-bridge'
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
  "${ROS_SETUP}; timeout 12 ros2 topic echo /map --once \
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
    vision)  echo "ros2 launch evo_vision vision.launch.py camera_topic:=${CAMERA_TOPIC} depth_topic:=${DEPTH_TOPIC} qr_decoder_backend:=auto" ;;
    reception)
      local validation_url
      validation_url="$(resolve_reception_validation_url)" || return 1
      echo "ros2 launch evo_reception reception.launch.py mock_mode:=false validation_url:=${validation_url}"
      ;;
    stationary_nav) echo "ros2 launch evo_navigation stationary_orchestrator.launch.py" ;;
    web)     echo "ros2 launch evo_web web_dashboard.launch.py rosbridge:=${ROSBRIDGE} http_port:=${CAMERA_PORT} camera_topic:=${CAMERA_TOPIC} camera_max_fps:=${CAMERA_MAX_FPS} camera_max_width:=${CAMERA_MAX_WIDTH} camera_jpeg_quality:=${CAMERA_JPEG_QUALITY}" ;;
    slam)    echo "ros2 launch evo_navigation slam_online.launch.py rviz:=false" ;;
    nav)     echo "ros2 launch evo_navigation navigation.launch.py map:=${MAP_PATH} rviz:=false" ;;
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
    stationary_nav) echo "stationary_orchestrator.launch.py" ;;
    web)     echo "web_dashboard.launch.py" ;;
    slam)    echo "slam_online.launch.py" ;;
    nav)     echo "navigation.launch.py" ;;
    *)       return 1 ;;
  esac
}

ALL_SERVICES="bringup camera vision reception stationary_nav web slam nav"

# Profils = raccourcis ; un nom inconnu est renvoyé tel quel (service unique).
expand_profile() {
  case "$1" in
    map)      echo "bringup camera slam web"   ;;   # créer une carte (LAUNCH.md §8)
    navigate) echo "bringup camera nav web"    ;;   # naviguer une carte sauvée (§9)
    base)     echo "bringup camera vision web" ;;   # base + caméra + vision + web
    reception) echo "bringup camera vision reception web" ;;
    stationary) echo "stationary_nav" ;;
    kiosk)    echo "bringup camera vision reception web" ;;
    launch|robot) echo "bringup camera nav vision reception web" ;;
    all)      echo "${ALL_SERVICES}"           ;;
    *)        echo "$1"                         ;;
  esac
}

# --- Cycle de vie des services ----------------------------------------------

# start_service <nom> <conteneur>
# Lance le service dans une session tmux DÉTACHÉE sur le Jetson. Le quoting passe par
# remote_quote (env) + printf %q (commande docker) côté distant : robuste face aux args
# ROS (`:=`), aux espaces et au sourcing multi-ligne — fini les quotes imbriquées.
start_service() {
  local name="$1" container="$2" cmd remote_env
  if _ssh "tmux has-session -t evo_${name} 2>/dev/null"; then
    echo "[start] evo_${name} already running"
    return 0
  fi
  if ! cmd="$(service_cmd "$name")"; then
    echo "[start] unknown service: ${name}" >&2
    return 1
  fi
  # nav: pull the saved map into the current container when Docker was recreated.
  if [ "$name" = "nav" ]; then
    ensure_map_in_docker "$container" "$MAP_PATH" || return 1
  fi
  if [ "$name" = "nav" ] && ! _ssh "docker exec ${container} test -f ${MAP_PATH}"; then
    echo "[start] map not found in Docker: ${MAP_PATH}" >&2
    echo "Save or sync it first with: ./scripts/sync_maps.sh ${DEFAULT_MAP_NAME}" >&2
    return 1
  fi
  echo "[start] evo_${name} : ${cmd}"
  remote_env="CONTAINER=$(remote_quote "$container") \
SESSION=$(remote_quote "evo_${name}") \
ROS_DOMAIN_ID=$(remote_quote "$ROS_DOMAIN_ID") \
FASTDDS_BUILTIN_TRANSPORTS=$(remote_quote "$FASTDDS_BUILTIN_TRANSPORTS") \
ROS_SETUP=$(remote_quote "$(_ros_prelude)") \
ROS_CMD=$(remote_quote "$cmd")"
  _ssh "${remote_env} bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail
full_cmd="${ROS_SETUP}; ${ROS_CMD}"
docker_cmd=$(printf 'docker exec -it -e ROS_DOMAIN_ID=%q -e FASTDDS_BUILTIN_TRANSPORTS=%q -e DISPLAY=:0 %q bash -lc %q' \
  "$ROS_DOMAIN_ID" "$FASTDDS_BUILTIN_TRANSPORTS" "$CONTAINER" "$full_cmd")
tmux new-session -d -s "$SESSION" "$docker_cmd"
REMOTE_SCRIPT
}

# stop_service <nom> <conteneur> : tue la session tmux ET tout le groupe de
# process du launch (launch + ses nœuds enfants partagent le même PGID).
# Tuer le ros2 launch seul laisse ses nœuds orphelins dans ce conteneur, d'où
# le kill par groupe (kill -- -PGID), en SIGTERM puis SIGKILL.
stop_service() {
  local name="$1" container="$2" pat safe
  _ssh "tmux kill-session -t evo_${name} 2>/dev/null || true"
  if pat="$(service_pattern "$name")"; then
    # Astuce crochets : "[b]ringup..." matche le vrai process mais PAS la ligne de
    # commande de pgrep elle-même -> évite l'auto-match du shell.
    safe="[${pat:0:1}]${pat:1}"
    # Script générique : motif passé en argument ($1), tue les groupes trouvés.
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
  echo "[stop] evo_${name} stopped"
}
