#!/usr/bin/env bash
# Point d'entrée unique pour piloter le robot m3pro depuis le Mac.
# Chaque service ROS tourne dans une session tmux DÉTACHÉE sur le Jetson :
# il survit à la fermeture du terminal Mac.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LAST_PROFILE_FILE="${SCRIPT_DIR}/.last_profile"

. "${SCRIPT_DIR}/config.sh"
. "${SCRIPT_DIR}/lib.sh"

usage() {
  cat <<EOF
Usage: robot.sh <commande> [args]

  setup                       Déploie evo_ws -> Jetson, copie dans Docker, colcon build
  start   <svc|profil>        Démarre des services en tmux détaché
  stop    <svc|profil|all>    Arrête des services (tmux + process ROS)
  restart [svc|profil]        Stop all + start (sans arg : reprend le dernier profil)
  status                      Sessions tmux + topics ROS + ports
  logs    <svc>               Attache la sortie d'un service (Ctrl-b d pour détacher)
  config  ip|container|user|show [valeur]

Services : bringup camera web slam nav
Profils  : map (carte) | navigate (nav) | base | all

Exemples :
  ./robot.sh setup
  ./robot.sh start map
  ./robot.sh config ip 10.10.220.132
  ./robot.sh restart
  ./robot.sh stop all
EOF
}

# --- Container (résolu une fois par commande) --------------------------------

require_container() {
  local c
  c="$(resolve_container)"
  if [ -z "$c" ]; then
    echo "Aucun conteneur Docker actif sur le Jetson (${JETSON_USER}@${JETSON_IP})." >&2
    echo "Vérifie : ssh ${JETSON_USER}@${JETSON_IP} 'docker ps'" >&2
    exit 1
  fi
  printf '%s' "$c"
}

# --- Commandes ---------------------------------------------------------------

cmd_setup() {
  ensure_tmux
  local container; container="$(require_container)"
  echo "[setup] déploiement evo_ws -> ${JETSON_USER}@${JETSON_IP}:${HOST_WS}"
  JETSON_IP="${JETSON_IP}" JETSON_USER="${JETSON_USER}" JETSON_WS="${HOST_WS}" \
    "${REPO_ROOT}/scripts/deploy.sh"
  echo "[setup] copie host -> Docker (${container}) + colcon build"
  _ssh "docker exec ${container} rm -rf ${DOCKER_WS}; docker cp ${HOST_WS} ${container}:${DOCKER_WS}"
  local build; build="$(_ros_prelude); cd ${DOCKER_WS} && colcon build --symlink-install"
  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 ${container} bash -lc \"${build}\""
  echo "[setup] terminé"
}

cmd_start() {
  local target="${1:-}"
  [ -n "$target" ] || { echo "usage: robot.sh start <svc|map|navigate|base|all>" >&2; exit 1; }
  ensure_tmux
  local container; container="$(require_container)"
  local s
  for s in $(expand_profile "$target"); do
    start_service "$s" "$container"
  done
  echo "$target" > "${LAST_PROFILE_FILE}"
  echo "[start] profil '${target}' lancé. Logs : ./robot.sh logs <svc> | État : ./robot.sh status"
}

cmd_stop() {
  local target="${1:-}"
  [ -n "$target" ] || { echo "usage: robot.sh stop <svc|profil|all>" >&2; exit 1; }
  local container; container="$(require_container)"
  local services s
  if [ "$target" = "all" ]; then services="${ALL_SERVICES}"; else services="$(expand_profile "$target")"; fi
  for s in $services; do
    stop_service "$s" "$container"
  done
}

cmd_restart() {
  local target="${1:-}"
  if [ -z "$target" ]; then
    target="$(cat "${LAST_PROFILE_FILE}" 2>/dev/null || true)"
    [ -n "$target" ] || { echo "Aucun profil mémorisé. Usage: robot.sh restart <svc|profil>" >&2; exit 1; }
    echo "[restart] reprise du dernier profil : ${target}"
  fi
  cmd_stop all
  sleep 2
  cmd_start "$target"
}

cmd_status() {
  local container; container="$(resolve_container)"
  echo "== Cible =="
  echo "jetson    : ${JETSON_USER}@${JETSON_IP}"
  echo "container : ${container:-<aucun>}"
  echo
  echo "== Sessions tmux =="
  _ssh "tmux ls 2>/dev/null | grep '^evo_' || echo '(aucune session evo_*)'"
  [ -n "$container" ] || return 0
  echo
  echo "== Topics ROS =="
  _ssh "docker exec ${container} bash -lc '$(_ros_prelude); ros2 topic list 2>/dev/null | grep -E \"/scan|/odom|/cmd_vel|/camera/color/image_raw\" || echo \"(aucun topic clé)\"'"
  echo
  echo "== Ports (accessibilité depuis ce poste) =="
  # On teste depuis le Mac : c'est l'accès réel qui compte pour le dashboard, et
  # le `ss` du conteneur est aveugle ici (réseau host + ss limité).
  _port_check "${CAMERA_PORT}" "caméra/web"
  _port_check 9090 "rosbridge"
}

# _port_check <port> <label> : joignable depuis le Mac ?
_port_check() {
  local port="$1" label="$2"
  if nc -z -w 3 "${JETSON_IP}" "${port}" 2>/dev/null; then
    echo "  ${port} (${label}) : OUVERT"
  else
    echo "  ${port} (${label}) : fermé/injoignable"
  fi
}

cmd_logs() {
  local name="${1:-}"
  [ -n "$name" ] || { echo "usage: robot.sh logs <svc>" >&2; exit 1; }
  echo "Attache evo_${name} (Ctrl-b puis d pour détacher sans tuer le service)"
  _ssh_tty "tmux attach -t evo_${name}"
}

_set_local() {
  local key="$1" val="${2:-}" lf="${SCRIPT_DIR}/config.local.sh"
  [ -n "$val" ] || { echo "valeur manquante pour ${key}" >&2; exit 1; }
  touch "$lf"
  grep -v "${key}:=" "$lf" > "${lf}.tmp" 2>/dev/null || true
  echo ": \"\${${key}:=${val}}\"" >> "${lf}.tmp"
  mv "${lf}.tmp" "$lf"
  echo "[config] ${key}=${val} (écrit dans config.local.sh)"
}

cmd_config() {
  case "${1:-}" in
    show)
      echo "JETSON_IP=${JETSON_IP}"
      echo "JETSON_USER=${JETSON_USER}"
      echo "CONTAINER=${CONTAINER}"
      echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
      echo "CAMERA_PORT=${CAMERA_PORT}"
      echo "MAP_PATH=${MAP_PATH}"
      ;;
    ip)        _set_local JETSON_IP "${2:-}" ;;
    container) _set_local CONTAINER "${2:-}" ;;
    user)      _set_local JETSON_USER "${2:-}" ;;
    *) echo "usage: robot.sh config ip|container|user|show [valeur]" >&2; exit 1 ;;
  esac
}

# --- Dispatch ----------------------------------------------------------------

case "${1:-}" in
  setup)            shift; cmd_setup "$@" ;;
  start)            shift; cmd_start "$@" ;;
  stop)             shift; cmd_stop "$@" ;;
  restart)          shift; cmd_restart "$@" ;;
  status)           shift; cmd_status "$@" ;;
  logs)             shift; cmd_logs "$@" ;;
  config)           shift; cmd_config "$@" ;;
  ""|-h|--help|help) usage ;;
  *) echo "commande inconnue : $1" >&2; echo; usage; exit 1 ;;
esac
