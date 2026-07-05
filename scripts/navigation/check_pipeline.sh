#!/usr/bin/env bash
set -euo pipefail

profile="${1:-navigation}"
use_velocity_smoother="${USE_VELOCITY_SMOOTHER:-true}"
use_collision_monitor="${USE_COLLISION_MONITOR:-true}"

required_nodes=(
  /cmd_vel_safety_gate
  /cmd_vel_output_relay
)

if [[ "$profile" != "slam_online" ]]; then
  required_nodes+=(/navigation_goal_validator)
fi

if [[ "$profile" != "slam_online" && "$use_velocity_smoother" == "true" ]]; then
  required_nodes+=(/velocity_smoother)
fi

if [[ "$use_collision_monitor" == "true" ]]; then
  required_nodes+=(/collision_monitor)
fi

nodes="$(ros2 node list)"
for node in "${required_nodes[@]}"; do
  if ! grep -Fxq "$node" <<<"$nodes"; then
    echo "ERROR: missing node $node"
    exit 1
  fi
done

publisher_count="$(
  ros2 topic info /cmd_vel --verbose |
    awk '/Publisher count:/ {print $3; exit}'
)"
if [[ "$publisher_count" != "1" ]]; then
  echo "ERROR: expected exactly one /cmd_vel publisher, found ${publisher_count:-unknown}"
  ros2 topic info /cmd_vel --verbose
  exit 1
fi

echo "Navigation pipeline OK for ${profile}: required nodes are active and /cmd_vel has one publisher."
