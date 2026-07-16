"""
Launch SLAM (slam_toolbox online async) for the M3 Pro.

Prerequisites: Yahboom bringup must already be running. The bringup provides:
  - lidar drivers (/scan0, /scan1)
  - ira_laser_tools/laserscan_multi_merger -> /scan_multi (TF-merged 360deg scan)
  - EKF odometry + robot_state_publisher + TF

This launch file starts:
  - slam_toolbox in online_async mode (consumes /scan_multi)
  - cmd_vel_safety_gate for browser teleop (/cmd_vel_teleop -> /cmd_vel_selected)
  - optional collision_monitor (/cmd_vel_selected -> /cmd_vel_safe)
  - cmd_vel_output_relay as the only /cmd_vel publisher
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
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    nav_share = FindPackageShare("evo_navigation")

    rviz_path = PathJoinSubstitution([nav_share, "rviz", "nav2_view.rviz"])
    slam_params = PathJoinSubstitution([nav_share, "config", "slam_toolbox_params.yaml"])
    nav2_params = PathJoinSubstitution([nav_share, "config", "nav2_params.yaml"])
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_collision_monitor = LaunchConfiguration("use_collision_monitor")
    relay_input_topic = PythonExpression([
        "'/cmd_vel_safe' if '", use_collision_monitor,
        "'.lower() == 'true' else '/cmd_vel_selected'",
    ])

    return LaunchDescription([
        DeclareLaunchArgument("rviz", default_value="true"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        # A stop polygon blocks every Twist direction when occupied, including
        # the reverse command needed to back away. Keep it opt-in for manual
        # mapping until its scan geometry is validated on the physical robot.
        DeclareLaunchArgument("use_collision_monitor", default_value="false"),

        # --- SLAM Toolbox ---
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            parameters=[
                slam_params,
                {"use_sim_time": use_sim_time},
            ],
            output="screen",
        ),

        # --- Final command gate / latched emergency stop ---
        Node(
            package="evo_navigation",
            executable="cmd_vel_safety_gate",
            name="cmd_vel_safety_gate",
            parameters=[{
                "use_sim_time": use_sim_time,
                "nav_cmd_topic": "/cmd_vel_nav",
                "teleop_cmd_topic": "/cmd_vel_teleop",
                "output_cmd_topic": "/cmd_vel_selected",
            }],
            output="screen",
        ),
        Node(
            package="nav2_collision_monitor",
            executable="collision_monitor",
            name="collision_monitor",
            parameters=[nav2_params, {
                "use_sim_time": use_sim_time,
                "polygons": ["FrontStop"],
            }],
            condition=IfCondition(use_collision_monitor),
            output="screen",
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_safety",
            parameters=[{
                "use_sim_time": use_sim_time,
                "autostart": True,
                "node_names": ["collision_monitor"],
                "bond_timeout": 4.0,
            }],
            condition=IfCondition(use_collision_monitor),
            output="screen",
        ),
        Node(
            package="evo_navigation",
            executable="cmd_vel_output_relay",
            name="cmd_vel_output_relay",
            parameters=[{
                "use_sim_time": use_sim_time,
                "input_cmd_topic": relay_input_topic,
                "fallback_cmd_topic": "",
                "output_cmd_topic": "/cmd_vel",
            }],
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
