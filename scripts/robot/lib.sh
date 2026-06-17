#!/usr/bin/env bash
# Fonctions helper partagées (ssh, tmux, docker, services ROS).
# Suppose config.sh déjà sourcé (JETSON_IP, JETSON_USER, CONTAINER, ...).

# --- SSH ---------------------------------------------------------------------

_ssh() { ssh -o ConnectTimeout=8 "${JETSON_USER}@${JETSON_IP}" "$@"; }
_ssh_tty() { ssh -t -o ConnectTimeout=8 "${JETSON_USER}@${JETSON_IP}" "$@"; }

# Bloc de sourcing ROS commun, sur une seule ligne (facilite l'imbrication de quotes).
_ros_prelude() {
  printf '%s' \
"source /opt/ros/humble/setup.bash; \
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true; \
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true; \
source /root/evo_ws/install/setup.bash; \
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID}; \
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4"
}

# --- Conteneur Docker --------------------------------------------------------

# Résout le nom du conteneur : "auto" -> premier conteneur actif sur le Jetson.
resolve_container() {
  if [ "${CONTAINER}" = "auto" ]; then
    _ssh "docker ps --format '{{.Names}}' | head -n1"
  else
    printf '%s\n' "${CONTAINER}"
  fi
}

ensure_tmux() {
  if ! _ssh "command -v tmux >/dev/null 2>&1"; then
    echo "tmux absent sur le Jetson. Installe-le une fois :" >&2
    echo "  ssh ${JETSON_USER}@${JETSON_IP} 'sudo apt-get install -y tmux'" >&2
    exit 1
  fi
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
    web)     echo "ros2 launch evo_web web_dashboard.launch.py port:=${CAMERA_PORT} camera_topic:=${CAMERA_TOPIC}" ;;
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
    web)     echo "web_dashboard.launch.py" ;;
    slam)    echo "slam_online.launch.py" ;;
    nav)     echo "navigation.launch.py" ;;
    *)       return 1 ;;
  esac
}

ALL_SERVICES="bringup camera web slam nav"

# Profils = raccourcis ; un nom inconnu est renvoyé tel quel (service unique).
expand_profile() {
  case "$1" in
    map)      echo "bringup camera slam web" ;;   # créer une carte (LAUNCH.md §8)
    navigate) echo "bringup camera nav web"  ;;   # naviguer une carte sauvée (§9)
    base)     echo "bringup camera web"      ;;   # base + caméra + web
    all)      echo "${ALL_SERVICES}"         ;;
    *)        echo "$1"                       ;;
  esac
}

# --- Cycle de vie des services ----------------------------------------------

# start_service <nom> <conteneur>
start_service() {
  local name="$1" container="$2" cmd inner docker_cmd remote
  if _ssh "tmux has-session -t evo_${name} 2>/dev/null"; then
    echo "[start] evo_${name} déjà actif — ignoré"
    return 0
  fi
  if ! cmd="$(service_cmd "$name")"; then
    echo "[start] service inconnu : ${name}" >&2
    return 1
  fi
  inner="$(_ros_prelude); ${cmd}"
  # tmux (single quotes) -> docker exec bash -lc (double quotes) -> commande ROS
  docker_cmd="docker exec -it ${container} bash -lc \"${inner}\""
  remote="tmux new-session -d -s evo_${name} '${docker_cmd}'"
  echo "[start] evo_${name} : ${cmd}"
  _ssh "$remote"
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
  echo "[stop] evo_${name} arrêté"
}
