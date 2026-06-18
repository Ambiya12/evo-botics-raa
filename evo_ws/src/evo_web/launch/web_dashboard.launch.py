"""
Launch the web monitoring dashboard.

Starts:
  - rosbridge_websocket (WebSocket bridge on port 9090) — skip with rosbridge:=false
  - web_server_node (HTTP server on port 8080 by default)

Then open http://<jetson-ip>:8080 in any browser. The dashboard connects to
the rosbridge at `ws://<same-host>:9090`.

Usage:
  ros2 launch evo_web web_dashboard.launch.py
  ros2 launch evo_web web_dashboard.launch.py port:=8080
  ros2 launch evo_web web_dashboard.launch.py rosbridge:=false    # if another launch already runs rosbridge
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    rosbridge_share = FindPackageShare("rosbridge_server")

    return LaunchDescription([
        DeclareLaunchArgument("port", default_value="8080",
                              description="HTTP port for the dashboard"),
        DeclareLaunchArgument("camera_topic", default_value="/camera/color/image_raw"),
        DeclareLaunchArgument("camera_max_fps", default_value="8.0",
                              description="Maximum JPEG encode rate for the HTTP camera stream"),
        DeclareLaunchArgument("camera_max_width", default_value="640",
                              description="Maximum HTTP camera stream width; 0 keeps native width"),
        DeclareLaunchArgument("camera_jpeg_quality", default_value="60",
                              description="JPEG quality for the HTTP camera stream"),
        DeclareLaunchArgument("rosbridge", default_value="true",
                              description="Start rosbridge_websocket on :9090 (skip if explore.launch.py already runs it)"),

        # --- rosbridge WebSocket server on port 9090 ---
        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(
                PathJoinSubstitution([rosbridge_share, "launch", "rosbridge_websocket_launch.xml"])
            ),
            launch_arguments={"port": "9090", "address": "0.0.0.0"}.items(),
            condition=IfCondition(LaunchConfiguration("rosbridge")),
        ),

        # --- Web file server + camera snapshot/MJPEG ---
        Node(
            package="evo_web",
            executable="web_server_node",
            name="web_server_node",
            parameters=[{
                "port": ParameterValue(LaunchConfiguration("port"), value_type=int),
                "camera_topic": LaunchConfiguration("camera_topic"),
                "max_fps": ParameterValue(LaunchConfiguration("camera_max_fps"), value_type=float),
                "max_width": ParameterValue(LaunchConfiguration("camera_max_width"), value_type=int),
                "jpeg_quality": ParameterValue(LaunchConfiguration("camera_jpeg_quality"), value_type=int),
            }],
            output="screen",
        ),
    ])
