#!/usr/bin/env bash
# Shared robot script configuration.
# Precedence: environment variable > config.local.sh > defaults below.
#
# Persist the DHCP robot IP with: ./scripts/robot.sh config ip <ip>
# Override once with: JETSON_IP=<ip> ./scripts/robot.sh status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ -f "${SCRIPT_DIR}/config.local.sh" ] && . "${SCRIPT_DIR}/config.local.sh"

: "${JETSON_IP:=}"
: "${JETSON_USER:=jetson}"
: "${CONTAINER:=auto}"
: "${ROS_DOMAIN_ID:=30}"
: "${HOST_WS:=/home/${JETSON_USER}/evo_ws}"
: "${DOCKER_WS:=/root/evo_ws}"
: "${DOCKER_MAP_DIR:=/root/maps}"
: "${HOST_MAP_DIR:=/home/${JETSON_USER}/maps}"
: "${DEFAULT_MAP_NAME:=school_map}"
: "${CAMERA_PORT:=8080}"
: "${CAMERA_TOPIC:=/camera/color/image_raw}"
: "${DEPTH_TOPIC:=/camera/depth/image_raw}"
: "${MAP_PATH:=${DOCKER_MAP_DIR}/${DEFAULT_MAP_NAME}.yaml}"
: "${FASTDDS_BUILTIN_TRANSPORTS:=UDPv4}"
: "${CAMERA_MAX_FPS:=8.0}"
: "${CAMERA_MAX_WIDTH:=640}"
: "${CAMERA_JPEG_QUALITY:=60}"
: "${ROSBRIDGE:=true}"
: "${APP_SCHEME:=http}"
: "${APP_HOST:=}"
: "${APP_PORT:=8000}"
: "${KIOSK_PATH:=/kiosk?scan=robot}"
: "${RECEPTION_VALIDATION_PATH:=/api/reservations/validate}"
: "${RECEPTION_VALIDATION_URL:=}"
: "${KIOSK_URL:=}"
: "${KIOSK_DISPLAY:=:0}"
: "${KIOSK_SESSION:=evo_kiosk}"
: "${FOXGLOVE_PORT:=8765}"
: "${FOXGLOVE_SESSION:=evo_foxglove}"
: "${AGENT_CONTAINER:=auto}"
: "${MCU_PROBE_TOPIC:=/odom_raw}"
