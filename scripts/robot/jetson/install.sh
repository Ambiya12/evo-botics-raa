#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
home_dir="${HOME:-/home/jetson}"
install_user="$(id -un)"
container="${EVO_ROS_CONTAINER:-evo-ros}"
agent_container="${MICRO_ROS_AGENT_CONTAINER:-evo-micro-ros-agent}"
agent_image="${MICRO_ROS_AGENT_IMAGE:-}"
serial_device="${MICRO_ROS_SERIAL_DEVICE:-/dev/myserial}"
serial_baud="${MICRO_ROS_SERIAL_BAUD:-2000000}"
agent_verbosity="${MICRO_ROS_AGENT_VERBOSITY:-4}"
ros_domain_id="${ROS_DOMAIN_ID:-30}"
fastdds_builtin_transports="${FASTDDS_BUILTIN_TRANSPORTS:-UDPv4}"
rmw_implementation="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
microros_disable_shm="${MICROROS_DISABLE_SHM:-1}"
backup_dir="${home_dir}/evo-robot-backup-$(date +%Y%m%d-%H%M%S)"

if ! docker inspect "$container" >/dev/null 2>&1; then
  echo "Missing container: ${container}" >&2
  exit 1
fi

if [ -z "$agent_image" ]; then
  agent_image="$(docker inspect -f '{{.Config.Image}}' "$agent_container" 2>/dev/null || true)"
fi
if [ -z "$agent_image" ]; then
  echo "Cannot determine the micro-ROS agent image." >&2
  echo "Keep the existing ${agent_container} container, or run with:" >&2
  echo "  MICRO_ROS_AGENT_IMAGE=<installed-image> ./install.sh" >&2
  exit 1
fi
if [[ ! "$agent_container" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
  echo "Invalid micro-ROS agent container name: ${agent_container}" >&2
  exit 1
fi
if [[ "$agent_image" =~ [[:space:]] ]]; then
  echo "Invalid micro-ROS agent image: whitespace is not supported" >&2
  exit 1
fi
if [[ "$serial_device" != /* ]] || [[ "$serial_device" =~ [[:space:]] ]]; then
  echo "Invalid micro-ROS serial device: ${serial_device}" >&2
  exit 1
fi
if [[ ! "$serial_baud" =~ ^[0-9]+$ ]]; then
  echo "Invalid micro-ROS serial baud: ${serial_baud}" >&2
  exit 1
fi
if [[ ! "$agent_verbosity" =~ ^[0-6]$ ]]; then
  echo "Invalid micro-ROS agent verbosity: ${agent_verbosity}" >&2
  exit 1
fi
if [[ ! "$ros_domain_id" =~ ^[0-9]+$ ]] ||
   [ "$ros_domain_id" -gt 232 ]; then
  echo "Invalid ROS domain ID: ${ros_domain_id}" >&2
  exit 1
fi
if [[ ! "$fastdds_builtin_transports" =~ ^[A-Za-z0-9_,.-]+$ ]]; then
  echo "Invalid Fast DDS built-in transport setting: ${fastdds_builtin_transports}" >&2
  exit 1
fi
if [[ ! "$rmw_implementation" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "Invalid ROS middleware implementation: ${rmw_implementation}" >&2
  exit 1
fi
if [[ ! "$microros_disable_shm" =~ ^[01]$ ]]; then
  echo "Invalid MICROROS_DISABLE_SHM value: ${microros_disable_shm}" >&2
  exit 1
fi

mkdir -p "$backup_dir"
if [ -e "${home_dir}/evo-ros-start.sh" ]; then
  cp -a "${home_dir}/evo-ros-start.sh" "$backup_dir/"
fi
[ ! -e "${home_dir}/.config/autostart/uros.desktop" ] ||
  cp -a "${home_dir}/.config/autostart/uros.desktop" "$backup_dir/"
[ ! -e "${home_dir}/.config/autostart/start.desktop" ] ||
  cp -a "${home_dir}/.config/autostart/start.desktop" "$backup_dir/"
[ ! -e "${home_dir}/.config/autostart/start.desktop.disabled" ] ||
  cp -a "${home_dir}/.config/autostart/start.desktop.disabled" "$backup_dir/"
docker cp "${container}:/root/joy.sh" "${backup_dir}/joy.sh"
sudo test ! -e /etc/systemd/system/evo-micro-ros-agent.service ||
  sudo cp -a /etc/systemd/system/evo-micro-ros-agent.service "$backup_dir/"
sudo test ! -e /etc/sudoers.d/evo-micro-ros-agent ||
  sudo cp -a /etc/sudoers.d/evo-micro-ros-agent "$backup_dir/"
sudo test ! -e /etc/default/evo-micro-ros-agent ||
  sudo cp -a /etc/default/evo-micro-ros-agent "$backup_dir/"

sudo systemd-analyze verify "${script_dir}/evo-micro-ros-agent.service"

install -m 0755 "${script_dir}/evo-ros-start.sh" "${home_dir}/evo-ros-start.sh"
mkdir -p "${home_dir}/.config/autostart"
install -m 0644 "${script_dir}/evo-ros.desktop" "${home_dir}/.config/autostart/uros.desktop"
docker cp "${script_dir}/evo-ros-entrypoint.sh" "${container}:/root/joy.sh"
docker exec "$container" chmod 0755 /root/joy.sh

sudo install -m 0644 \
  "${script_dir}/evo-micro-ros-agent.service" \
  /etc/systemd/system/evo-micro-ros-agent.service
printf '%s\n' \
  "MICRO_ROS_AGENT_CONTAINER=${agent_container}" \
  "MICRO_ROS_AGENT_IMAGE=${agent_image}" \
  "MICRO_ROS_SERIAL_DEVICE=${serial_device}" \
  "MICRO_ROS_SERIAL_BAUD=${serial_baud}" \
  "MICRO_ROS_AGENT_VERBOSITY=${agent_verbosity}" \
  "ROS_DOMAIN_ID=${ros_domain_id}" \
  "FASTDDS_BUILTIN_TRANSPORTS=${fastdds_builtin_transports}" \
  "RMW_IMPLEMENTATION=${rmw_implementation}" \
  "MICROROS_DISABLE_SHM=${microros_disable_shm}" |
  sudo tee /etc/default/evo-micro-ros-agent >/dev/null
sudo chmod 0644 /etc/default/evo-micro-ros-agent
sudo sh -c "printf '%s\n' \
  '${install_user} ALL=(root) NOPASSWD: /bin/systemctl restart evo-micro-ros-agent.service' \
  > /etc/sudoers.d/evo-micro-ros-agent"
sudo chmod 0440 /etc/sudoers.d/evo-micro-ros-agent
sudo visudo -cf /etc/sudoers.d/evo-micro-ros-agent
sudo systemctl daemon-reload
sudo systemctl enable evo-micro-ros-agent.service

if [ -e "${home_dir}/.config/autostart/start.desktop" ]; then
  mv "${home_dir}/.config/autostart/start.desktop" \
    "${home_dir}/.config/autostart/start.desktop.disabled"
fi

echo "Provisioned stable EVO startup files."
echo "micro-ROS agent image: ${agent_image}"
echo "micro-ROS serial: ${serial_device} @ ${serial_baud}"
echo "micro-ROS DDS: domain ${ros_domain_id}, ${fastdds_builtin_transports}"
echo "micro-ROS middleware: ${rmw_implementation}, disable SHM=${microros_disable_shm}"
echo "Backup: ${backup_dir}"
echo "No container or service was restarted."
