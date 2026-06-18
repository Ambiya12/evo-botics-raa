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

  recover [profil]            Récupération post-reboot tout-en-un : evo_ws + stack + MCU + état
  setup [--push]              Met evo_ws à dispo (conteneur > host) + rebuild. --push pour ENVOYER le local
  pull                        Récupère evo_ws/src du conteneur -> Mac (le robot fait foi)
  start   <svc|profil>        Démarre des services en tmux détaché
  stop    <svc|profil|all>    Arrête des services (tmux + process ROS)
  restart [svc|profil]        Stop all + start (sans arg : reprend le dernier profil)
  mcu     [--force]           Réveille la carte (redémarre l'agent micro-ROS si flux figé)
  status                      Sessions tmux + topics ROS + MCU + ports
  health                      Specs + charge CPU/RAM + top process (lecture seule)
  logs    <svc>               Attache la sortie d'un service (Ctrl-b d pour détacher)
  config  ip|container|user|show [valeur]

Services : bringup camera vision web slam nav
Profils  : map (carte) | navigate (nav) | base | all

Exemples :
  ./robot.sh recover map      # après un reboot du Jetson
  ./robot.sh setup
  ./robot.sh start map
  ./robot.sh mcu              # carte muette ? réveille l'agent micro-ROS
  ./robot.sh config ip 10.10.220.132
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

# Récupère evo_ws/src DU CONTENEUR vers le Mac (le robot est la source de vérité).
# tar-stream over ssh : pas de fichier temporaire intermédiaire.
cmd_pull() {
  local container; container="$(require_container)"
  echo "[pull] ${container}:${DOCKER_WS}/src -> ${REPO_ROOT}/evo_ws/src"
  _ssh "docker exec ${container} tar -C ${DOCKER_WS} -cf - src" \
    | tar -C "${REPO_ROOT}/evo_ws" -xf -
  echo "[pull] terminé — evo_ws/src local resynchronisé depuis le robot"
}

# setup par défaut = récupère depuis le robot puis rebuild dans le conteneur.
# Ne pousse PLUS le local (qui peut être périmé) -> pas de rétrogradation accidentelle.
cmd_setup() {
  if [ "${1:-}" = "--push" ]; then
    cmd_setup_push
    return
  fi
  ensure_tmux
  local container; container="$(require_container)"
  echo "[setup] mise à disposition de evo_ws (conteneur > host) + rebuild"
  ensure_evo_ws "$container"
  echo "[setup] colcon build dans Docker (${container})"
  local build; build="$(_ros_prelude); cd ${DOCKER_WS} && colcon build --symlink-install"
  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc \"${build}\""
  echo "[setup] terminé"
}

# setup --push = ancien comportement : ENVOIE le evo_ws local -> Jetson -> Docker + build.
# Gardé pour pousser de vraies modifs locales, mais protégé par une confirmation car le
# local peut écraser une version plus récente du conteneur.
cmd_setup_push() {
  ensure_tmux
  local container; container="$(require_container)"
  echo "⚠️  [setup --push] Va ÉCRASER le code du conteneur (${container}) avec ton evo_ws LOCAL."
  echo "    Si ton local est périmé, tu rétrogrades le robot (perte de evo_vision / params caméra)."
  echo "    Pense à './robot.sh pull' d'abord si tu n'es pas sûr."
  printf "    Continuer ? [y/N] "
  local ans; read -r ans
  case "$ans" in
    y|Y|yes|YES|o|O|oui|OUI) ;;
    *) echo "[setup --push] annulé"; return 1 ;;
  esac
  echo "[setup --push] déploiement evo_ws local -> ${JETSON_USER}@${JETSON_IP}:${HOST_WS}"
  JETSON_IP="${JETSON_IP}" JETSON_USER="${JETSON_USER}" JETSON_WS="${HOST_WS}" \
    "${REPO_ROOT}/scripts/deploy.sh"
  echo "[setup --push] copie host -> Docker (${container}) + colcon build"
  _ssh "docker exec ${container} rm -rf ${DOCKER_WS}; docker cp ${HOST_WS} ${container}:${DOCKER_WS}"
  local build; build="$(_ros_prelude); cd ${DOCKER_WS} && colcon build --symlink-install"
  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc \"${build}\""
  echo "[setup --push] terminé"
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

# Réveille la carte (MCU) si son flux micro-ROS est figé : redémarre l'agent série pour
# forcer une nouvelle session XRCE, puis attend la reprise du flux. `--force` redémarre
# même si la carte semble déjà vivante.
cmd_mcu() {
  local force=""; [ "${1:-}" = "--force" ] && force=1
  local container; container="$(require_container)"
  local agent; agent="$(resolve_agent_container)"
  [ -n "$agent" ] || { echo "Agent micro-ROS introuvable (aucune image micro-ros active)." >&2; exit 1; }
  echo "[mcu] conteneur=${container} agent=${agent} topic=${MCU_PROBE_TOPIC}"
  if [ -z "$force" ] && mcu_is_alive "$container"; then
    echo "[mcu] carte déjà vivante (flux ${MCU_PROBE_TOPIC} détecté) — rien à faire (--force pour relancer)."
  else
    echo "[mcu] MCU muet — redémarrage de l'agent ${agent}"
    _ssh "docker restart ${agent}" >/dev/null
    echo "[mcu] attente de la reprise du flux (poll ~20 s)..."
    if ! wait_for_mcu "$container"; then
      echo "[mcu] ÉCHEC : le MCU reste muet. Reset physique de la carte requis (bouton sur l'expansion board)." >&2
      exit 1
    fi
  fi
  echo "[mcu] OK — fréquences :"
  _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc '
    source /opt/ros/humble/setup.bash 2>/dev/null
    for t in /odom_raw /imu/data_raw /joint_states; do
      printf \"  %-16s \" \"\$t\"
      timeout 5 ros2 topic hz \$t 2>/dev/null | grep \"average rate\" | head -1 || echo \"(muet)\"
    done'"
}

# Orchestrateur de récupération post-reboot : evo_ws -> stack -> MCU -> état.
# Profil = argument, sinon dernier profil mémorisé, sinon 'map'.
cmd_recover() {
  ensure_tmux
  local profile="${1:-}"
  if [ -z "$profile" ]; then
    profile="$(cat "${LAST_PROFILE_FILE}" 2>/dev/null || true)"
    [ -n "$profile" ] || profile="map"
  fi
  local container; container="$(require_container)"
  echo "[recover] profil='${profile}' conteneur='${container}'"
  # 1. evo_ws : (re)mettre les sources + builder seulement si l'install manque.
  if _ssh "docker exec ${container} test -d ${DOCKER_WS}/install"; then
    echo "[recover] evo_ws déjà buildé — build sauté (utilise 'setup' pour forcer)"
  else
    ensure_evo_ws "$container"
    echo "[recover] colcon build dans Docker (${container})"
    local build; build="$(_ros_prelude); cd ${DOCKER_WS} && colcon build --symlink-install"
    _ssh "docker exec -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} -e FASTDDS_BUILTIN_TRANSPORTS=${FASTDDS_BUILTIN_TRANSPORTS} ${container} bash -lc \"${build}\""
  fi
  # 2. stack
  cmd_start "$profile"
  # 3. MCU
  cmd_mcu
  # 4. état final
  echo; cmd_status
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
  echo "== Carte (MCU micro-ROS) =="
  if mcu_is_alive "$container"; then
    echo "  flux ${MCU_PROBE_TOPIC} : OUI (carte vivante)"
  else
    echo "  flux ${MCU_PROBE_TOPIC} : MUET — lance ./robot.sh mcu pour réveiller la carte"
  fi
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

cmd_health() {
  echo "== Santé Jetson (${JETSON_USER}@${JETSON_IP}) =="
  jetson_health
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
  recover)          shift; cmd_recover "$@" ;;
  setup)            shift; cmd_setup "$@" ;;
  pull)             shift; cmd_pull "$@" ;;
  start)            shift; cmd_start "$@" ;;
  stop)             shift; cmd_stop "$@" ;;
  restart)          shift; cmd_restart "$@" ;;
  mcu)              shift; cmd_mcu "$@" ;;
  status)           shift; cmd_status "$@" ;;
  health)           shift; cmd_health "$@" ;;
  logs)             shift; cmd_logs "$@" ;;
  config)           shift; cmd_config "$@" ;;
  ""|-h|--help|help) usage ;;
  *) echo "commande inconnue : $1" >&2; echo; usage; exit 1 ;;
esac
