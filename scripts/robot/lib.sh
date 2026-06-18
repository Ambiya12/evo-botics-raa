#!/usr/bin/env bash
# Fonctions helper partagées (ssh, tmux, docker, services ROS).
# Suppose config.sh déjà sourcé (JETSON_IP, JETSON_USER, CONTAINER, ...).

# --- SSH ---------------------------------------------------------------------

_ssh() { ssh -o ConnectTimeout=8 "${JETSON_USER}@${JETSON_IP}" "$@"; }
_ssh_tty() { ssh -t -o ConnectTimeout=8 "${JETSON_USER}@${JETSON_IP}" "$@"; }

# Échappe une chaîne pour qu'elle survive à un niveau de shell distant (entre quotes
# simples). Repris de scripts/deploy.sh : fiabilise les commandes SSH->docker.
remote_quote() { printf "%s" "$1" | sed "s/'/'\\\\''/g; 1s/^/'/; \$s/\$/'/"; }

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

# Résout le nom du conteneur m3pro : "auto" -> le conteneur qui embarque le workspace
# Yahboom (/root/M3Pro_ws). `docker ps | head -n1` dépend de l'ordre de création et tombe
# sur le mauvais conteneur dès qu'un autre est plus récent (ex. l'agent micro-ROS) -> tous
# les `source` échouent et les launchs meurent. On sonde /root/M3Pro_ws (toujours présent
# dans l'image, contrairement à /root/evo_ws qui DISPARAÎT quand le conteneur est recréé au
# reboot) : la sonde reste fiable même sur un conteneur fraîchement relancé. Fallback : head -n1.
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

# Résout le conteneur de l'agent micro-ROS (bridge série du MCU). Son nom change à chaque
# relance ; on le repère par son image (matche "micro-ros"). Fallback : un conteneur en
# cours qui n'embarque PAS /root/M3Pro_ws (donc pas le m3pro).
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

# --- evo_ws : amorçage / récupération ---------------------------------------

# Copie evo_ws DU HOST Jetson (/home/jetson/evo_ws, persistant aux reboots) VERS le
# conteneur. Utilisé quand le conteneur a été recréé à neuf et a perdu /root/evo_ws.
seed_evo_ws_from_host() {
  local container="$1"
  if ! _ssh "test -d ${HOST_WS}/src"; then
    echo "[evo_ws] introuvable sur le host (${HOST_WS}/src) — utilise './robot.sh setup --push'." >&2
    return 1
  fi
  echo "[evo_ws] amorçage depuis le host : ${HOST_WS} -> ${container}:${DOCKER_WS}"
  _ssh "docker exec ${container} mkdir -p ${DOCKER_WS} && docker cp ${HOST_WS}/. ${container}:${DOCKER_WS}"
}

# Garantit que /root/evo_ws/src existe dans le conteneur, dans l'ordre de préférence :
#   1. déjà présent dans le conteneur  -> pull (le robot fait foi, comportement historique)
#   2. présent sur le host             -> seed_evo_ws_from_host
#   3. nulle part                      -> erreur (renvoie vers setup --push)
ensure_evo_ws() {
  local container="$1"
  if _ssh "docker exec ${container} test -d ${DOCKER_WS}/src"; then
    cmd_pull
  elif _ssh "test -d ${HOST_WS}/src"; then
    seed_evo_ws_from_host "$container"
  else
    echo "[evo_ws] absent du conteneur ET du host — déploie ton local : './robot.sh setup --push'." >&2
    return 1
  fi
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
    vision)  echo "ros2 launch evo_vision vision.launch.py camera_topic:=${CAMERA_TOPIC} depth_topic:=${DEPTH_TOPIC} qr_decoder_backend:=auto" ;;
    web)     echo "ros2 launch evo_web web_dashboard.launch.py rosbridge:=${ROSBRIDGE} port:=${CAMERA_PORT} camera_topic:=${CAMERA_TOPIC} camera_max_fps:=${CAMERA_MAX_FPS} camera_max_width:=${CAMERA_MAX_WIDTH} camera_jpeg_quality:=${CAMERA_JPEG_QUALITY}" ;;
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
    web)     echo "web_dashboard.launch.py" ;;
    slam)    echo "slam_online.launch.py" ;;
    nav)     echo "navigation.launch.py" ;;
    *)       return 1 ;;
  esac
}

ALL_SERVICES="bringup camera vision web slam nav"

# Profils = raccourcis ; un nom inconnu est renvoyé tel quel (service unique).
expand_profile() {
  case "$1" in
    map)      echo "bringup camera slam web"   ;;   # créer une carte (LAUNCH.md §8)
    navigate) echo "bringup camera nav web"    ;;   # naviguer une carte sauvée (§9)
    base)     echo "bringup camera vision web" ;;   # base + caméra + vision + web
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
    echo "[start] evo_${name} déjà actif — ignoré"
    return 0
  fi
  if ! cmd="$(service_cmd "$name")"; then
    echo "[start] service inconnu : ${name}" >&2
    return 1
  fi
  # nav : refuser de démarrer si la carte n'existe pas dans le conteneur.
  if [ "$name" = "nav" ] && ! _ssh "docker exec ${container} test -f ${MAP_PATH}"; then
    echo "[start] carte introuvable dans Docker : ${MAP_PATH} — crée-la d'abord (start map)" >&2
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
  echo "[stop] evo_${name} arrêté"
}
