#!/usr/bin/env bash
set -euo pipefail

container="${EVO_ROS_CONTAINER:-evo-ros}"

while ! systemctl is-active --quiet docker; do
  sleep 1
done

if ! docker inspect "$container" >/dev/null 2>&1; then
  echo "Missing container: ${container}" >&2
  echo "Provision the EVO robot image/container before enabling desktop startup." >&2
  exit 1
fi

if [ "$(docker inspect -f '{{.State.Running}}' "$container")" = "true" ]; then
  echo "${container} is already running"
  exit 0
fi

docker start "$container"
