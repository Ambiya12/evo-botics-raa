"""
Autonomous map-building-while-exploring launch for the M3 Pro.

Brings up, in order:
  - slam_toolbox (online async, mapping) consuming /scan_multi
  - Nav2 controller / planner / behaviors / bt_navigator / costmaps
  - explore_lite (frontier exploration, "Roomba-style")
  - rosbridge_server on port 8765 for Foxglove Studio

Prerequisites (the Yahboom bringup must already be running):
  ros2 launch M3Pro_navigation base_bringup.launch.py

That provides: /scan0 /scan1 /scan_multi /odom /imu /tf /tf_static + robot_state_publisher.

Usage:
  ros2 launch evo_navigation explore.launch.py
  ros2 launch evo_navigation explore.launch.py rosbridge:=false
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    nav_share = FindPackageShare("evo_navigation")

    slam_params = PathJoinSubstitution([nav_share, "config", "slam_toolbox_params.yaml"])
    nav2_params = PathJoinSubstitution([nav_share, "config", "nav2_params.yaml"])
    explore_params = PathJoinSubstitution([nav_share, "config", "explore_params.yaml"])

    use_sim_time = LaunchConfiguration("use_sim_time")

    nav2_node_names = [
        "controller_server",
        "smoother_server",
        "planner_server",
        "behavior_server",
        "bt_navigator",
    ]

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("rosbridge", default_value="true",
                              description="Start rosbridge_server on :8765 for Foxglove"),

        # --- SLAM (map + map->odom TF) ---
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            parameters=[slam_params, {"use_sim_time": use_sim_time}],
            output="screen",
        ),

        # --- Final command gate / latched emergency stop ---
        Node(
            package="evo_navigation",
            executable="cmd_vel_safety_gate",
            name="cmd_vel_safety_gate",
            parameters=[{"use_sim_time": use_sim_time}],
            output="screen",
        ),

        # --- Nav2 ---
        Node(package="nav2_controller", executable="controller_server",
             name="controller_server", parameters=[nav2_params],
             remappings=[("cmd_vel", "/cmd_vel_nav")], output="screen"),
        Node(package="nav2_smoother", executable="smoother_server",
             name="smoother_server", parameters=[nav2_params], output="screen"),
        Node(package="nav2_planner", executable="planner_server",
             name="planner_server", parameters=[nav2_params], output="screen"),
        Node(package="nav2_behaviors", executable="behavior_server",
             name="behavior_server", parameters=[nav2_params],
             remappings=[("cmd_vel", "/cmd_vel_nav")], output="screen"),
        Node(package="nav2_bt_navigator", executable="bt_navigator",
             name="bt_navigator", parameters=[nav2_params], output="screen"),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_navigation",
            parameters=[{
                "autostart": True,
                "node_names": nav2_node_names,
                "bond_timeout": 4.0,
            }],
            output="screen",
        ),

        # --- Frontier exploration (Roomba-style, max-circumference tuned) ---
        Node(
            package="explore_lite",
            executable="explore",
            name="explore_node",
            parameters=[explore_params, {"use_sim_time": use_sim_time}],
            output="screen",
            remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
        ),

        # --- Rosbridge for Foxglove Studio (ws://<robot>:8765) ---
        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare("rosbridge_server"),
                                      "launch", "rosbridge_websocket_launch.xml"])
            ),
            launch_arguments={"port": "9090", "address": "0.0.0.0"}.items(),
            condition=IfCondition(LaunchConfiguration("rosbridge")),
        ),
    ])
