#!/usr/bin/env bash
set -euo pipefail

OUTPUT="${1:-navigation-$(date +%Y%m%d-%H%M%S)}"

ros2 bag record -o "$OUTPUT" \
  /map \
  /map_metadata \
  /global_costmap/costmap \
  /global_costmap/costmap_updates \
  /local_costmap/costmap \
  /local_costmap/costmap_updates \
  /plan \
  /local_plan \
  /scan_multi \
  /vision/obstacles/points \
  /tf \
  /tf_static \
  /odom \
  /amcl_pose \
  /cmd_vel_nav_raw \
  /cmd_vel_nav \
  /cmd_vel_teleop \
  /cmd_vel_selected \
  /cmd_vel_safe \
  /cmd_vel \
  /evo/control_mode \
  /evo/control_mode_state \
  /evo/navigation/goal_request \
  /evo/navigation/goal_status \
  /goal_pose_validated \
  /collision_monitor_state \
  /diagnostics \
  /navigate_to_pose/_action/status \
  /navigate_to_pose/_action/feedback
