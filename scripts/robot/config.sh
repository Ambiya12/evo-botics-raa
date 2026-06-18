#!/usr/bin/env bash
# Configuration partagée des scripts de démarrage robot.
# Précédence : variable d'environnement > config.local.sh > valeurs par défaut ci-dessous.
#
# Pour surcharger durablement (IP DHCP, conteneur...) : ./robot.sh config ip <ip>
# Pour surcharger ponctuellement : JETSON_IP=10.10.220.132 ./robot.sh status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# config.local.sh est sourcé EN PREMIER : ses `:=` ne s'appliquent que si la
# variable n'est pas déjà fixée par l'environnement -> env > local > défauts.
[ -f "${SCRIPT_DIR}/config.local.sh" ] && . "${SCRIPT_DIR}/config.local.sh"

: "${JETSON_IP:=10.10.220.251}"
: "${JETSON_USER:=jetson}"
: "${CONTAINER:=auto}"          # "auto" = détection du conteneur actif sur le Jetson
: "${ROS_DOMAIN_ID:=30}"
: "${HOST_WS:=/home/${JETSON_USER}/evo_ws}"
: "${DOCKER_WS:=/root/evo_ws}"
: "${CAMERA_PORT:=8080}"
: "${CAMERA_TOPIC:=/camera/color/image_raw}"
: "${DEPTH_TOPIC:=/camera/depth/image_raw}"
: "${MAP_PATH:=/root/maps/admin_map.yaml}"
: "${FASTDDS_BUILTIN_TRANSPORTS:=UDPv4}"
# Réglages du flux caméra HTTP (allègent la charge sur le Jetson Nano)
: "${CAMERA_MAX_FPS:=8.0}"
: "${CAMERA_MAX_WIDTH:=640}"
: "${CAMERA_JPEG_QUALITY:=60}"
: "${ROSBRIDGE:=true}"
# Récupération post-reboot (evo_ws + MCU micro-ROS)
: "${AGENT_CONTAINER:=auto}"      # auto = conteneur dont l'image matche micro-ros
: "${MCU_PROBE_TOPIC:=/odom_raw}" # topic témoin du flux MCU (présent = carte vivante)
