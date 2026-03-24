#!/usr/bin/env bash
set -euo pipefail

set +u
source /opt/ros/humble/setup.bash
source /workspace/evo_ws/install/setup.bash
set -u
export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/home/ubuntu/.Xauthority}"

# Launch Gazebo Sim (Ignition/Fortress) with the Rosmaster M3 Pro already spawned.
ros2 launch evo_bringup gazebo_m3pro.launch.py "$@"
