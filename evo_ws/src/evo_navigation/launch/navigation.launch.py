"""
Launch Nav2 autonomous navigation with a pre-built map.

Prerequisites:
  - Yahboom bringup must already be running (lidar + odometry + cmd_vel)
  - A map must have been saved previously with slam_toolbox

NOTE: We rely on the Yahboom bringup's robot_state_publisher for TF.
Do not launch a second one — the microcontroller clock offset causes conflicts.

Usage:
  ros2 launch evo_navigation navigation.launch.py map:=/path/to/map.yaml
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    nav_share = FindPackageShare("evo_navigation")
    nav2_bringup_share = FindPackageShare("nav2_bringup")

    rviz_path = PathJoinSubstitution([nav_share, "rviz", "nav2_view.rviz"])
    nav2_params = PathJoinSubstitution([nav_share, "config", "nav2_params.yaml"])

    return LaunchDescription([
        DeclareLaunchArgument("map", description="Full path to the map YAML file"),
        DeclareLaunchArgument("rviz", default_value="true"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),

        # --- Final command gate / latched emergency stop ---
        Node(
            package="evo_navigation",
            executable="cmd_vel_safety_gate",
            name="cmd_vel_safety_gate",
            parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
            output="screen",
        ),

        # --- Nav2 bringup (AMCL + planners + controllers + behaviors) ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([nav2_bringup_share, "launch", "bringup_launch.py"])
            ),
            launch_arguments={
                "map": LaunchConfiguration("map"),
                "params_file": nav2_params,
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "autostart": "true",
            }.items(),
        ),

        # --- RViz ---
        Node(
            package="rviz2",
            executable="rviz2",
            arguments=["-d", rviz_path],
            condition=IfCondition(LaunchConfiguration("rviz")),
            output="screen",
        ),
    ])
