"""Launch the browser teleop command path without SLAM or Nav2."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
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
            package="evo_navigation",
            executable="cmd_vel_output_relay",
            name="cmd_vel_output_relay",
            parameters=[{
                "use_sim_time": use_sim_time,
                "input_cmd_topic": "/cmd_vel_selected",
                "fallback_cmd_topic": "",
                "output_cmd_topic": "/cmd_vel",
            }],
            output="screen",
        ),
    ])
