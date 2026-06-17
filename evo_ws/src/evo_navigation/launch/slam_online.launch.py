"""
Launch SLAM (slam_toolbox online async) for the M3 Pro.

Prerequisites: Yahboom bringup must already be running. The bringup provides:
  - lidar drivers (/scan0, /scan1)
  - ira_laser_tools/laserscan_multi_merger -> /scan_multi (TF-merged 360deg scan)
  - EKF odometry + robot_state_publisher + TF

This launch file starts:
  - slam_toolbox in online_async mode (consumes /scan_multi)
  - cmd_vel_safety_gate for browser teleop (/cmd_vel_teleop -> /cmd_vel)
  - rviz2 (optional)

NOTE: We do NOT launch robot_state_publisher or any scan merger here because
the Yahboom bringup already provides both. Running duplicates causes TF
timestamp conflicts (the microcontroller clock differs from the system clock).

Usage:
  ros2 launch evo_navigation slam_online.launch.py
  ros2 launch evo_navigation slam_online.launch.py rviz:=false
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    nav_share = FindPackageShare("evo_navigation")

    rviz_path = PathJoinSubstitution([nav_share, "rviz", "nav2_view.rviz"])
    slam_params = PathJoinSubstitution([nav_share, "config", "slam_toolbox_params.yaml"])

    return LaunchDescription([
        DeclareLaunchArgument("rviz", default_value="true"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),

        # --- SLAM Toolbox ---
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            parameters=[
                slam_params,
                {"use_sim_time": LaunchConfiguration("use_sim_time")},
            ],
            output="screen",
        ),

        # --- Final command gate / latched emergency stop ---
        Node(
            package="evo_navigation",
            executable="cmd_vel_safety_gate",
            name="cmd_vel_safety_gate",
            parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
            output="screen",
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
