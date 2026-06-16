# Third-Party ROS Packages

This folder contains minimal vendored ROS packages needed by Evo-Botics.

## explore_lite

- Source: `m-explore-ros2`, copied from the teacher reference workspace.
- Upstream project: https://github.com/robo-friends/m-explore-ros2
- License: BSD, preserved in `LICENSE.m-explore-ros2`.
- Purpose: frontier-based autonomous exploration used by `evo_navigation/launch/explore.launch.py`.

Only the packages required for autonomous exploration are kept:

- `explore_lite`
- `explore_lite_msgs`

Unused upstream packages such as `multirobot_map_merge`, development containers,
CI files, broad demo assets, and tests are intentionally excluded.
