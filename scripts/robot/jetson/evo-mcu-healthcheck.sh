#!/usr/bin/env bash
set -euo pipefail

container="${EVO_ROS_CONTAINER:-evo-ros}"
agent_container="${MICRO_ROS_AGENT_CONTAINER:-evo-micro-ros-agent}"
service="${MICRO_ROS_SERVICE:-evo-micro-ros-agent.service}"
serial_device="${MICRO_ROS_SERIAL_DEVICE:-/dev/myserial}"
probe_topic="${MCU_PROBE_TOPIC:-/battery}"

if [ ! -e "$serial_device" ]; then
  echo "[mcu-health] serial device missing: ${serial_device}" >&2
  exit 1
fi

if [ "$(systemctl is-active "$service" 2>/dev/null || true)" != "active" ]; then
  echo "[mcu-health] systemd service is not active: ${service}" >&2
  systemctl status "$service" --no-pager -l 2>&1 || true
  exit 1
fi

if [ "$(docker inspect -f '{{.State.Running}}' "$agent_container" 2>/dev/null)" != "true" ]; then
  echo "[mcu-health] agent container is not running: ${agent_container}" >&2
  exit 1
fi

if [ "$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null)" != "true" ]; then
  echo "[mcu-health] ${container} is not running" >&2
  exit 1
fi

session_ready=false
for _ in $(seq 1 20); do
  logs="$(docker logs "$agent_container" 2>&1 || true)"
  if grep -qE 'session established|create_client.*OK|Root\.session' <<<"$logs"; then
    session_ready=true
    break
  fi
  sleep 1
done
if [ "$session_ready" = false ]; then
  echo "[mcu-health] no XRCE session marker in the agent log; checking the ROS message directly" >&2
fi

if ! docker exec \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}" \
  -e FASTDDS_BUILTIN_TRANSPORTS="${FASTDDS_BUILTIN_TRANSPORTS:-UDPv4}" \
  "$container" \
  bash -lc "source /opt/ros/humble/setup.bash &&
    timeout -k 1s 30s ros2 topic echo '${probe_topic}' --once \
      --qos-reliability best_effort >/dev/null"; then
  echo "[mcu-health] no ${probe_topic} message received" >&2
  echo "[mcu-health] recent agent log:" >&2
  docker logs --tail 20 "$agent_container" 2>&1 >&2 || true
  echo "[mcu-health] ${probe_topic} endpoint:" >&2
  docker exec \
    -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}" \
    -e FASTDDS_BUILTIN_TRANSPORTS="${FASTDDS_BUILTIN_TRANSPORTS:-UDPv4}" \
    "$container" \
    bash -lc "source /opt/ros/humble/setup.bash &&
      ros2 topic info '${probe_topic}' -v" 2>&1 >&2 || true
  if [ "$session_ready" = true ]; then
    echo "[mcu-health] XRCE is connected, but the MCU firmware is not streaming ${probe_topic}" >&2
  fi
  exit 1
fi

echo "[mcu-health] serial, service, XRCE bridge, and ${probe_topic} message are healthy"
