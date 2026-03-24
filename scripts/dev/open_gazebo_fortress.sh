#!/usr/bin/env bash
set -euo pipefail

set +u
source /opt/ros/humble/setup.bash
set -u
export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/home/ubuntu/.Xauthority}"

# Launch Gazebo Sim (Ignition/Fortress) with ROS integration.
ros2 launch ros_gz_sim gz_sim.launch.py
