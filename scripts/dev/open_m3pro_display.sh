#!/usr/bin/env bash
set -euo pipefail

set +u
source /opt/ros/humble/setup.bash
source /workspace/evo_ws/install/setup.bash
set -u
export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/home/ubuntu/.Xauthority}"

# Start robot_state_publisher + joint_state_publisher + RViz for M3 Pro.
ros2 launch evo_bringup display_m3pro.launch.py
