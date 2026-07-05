"""
Launch the web monitoring dashboard.

Starts:
  - rosbridge_websocket (WebSocket bridge on rosbridge_port) — skip with rosbridge:=false
  - web_server_node (HTTP server on port 8080 by default)

Then open http://<jetson-ip>:8080 in any browser. The dashboard connects to
the rosbridge at `ws://<same-host>:9090`.

Usage:
  ros2 launch evo_web web_dashboard.launch.py
  ros2 launch evo_web web_dashboard.launch.py http_port:=8080 rosbridge_port:=9090
  ros2 launch evo_web web_dashboard.launch.py rosbridge:=false    # if another launch already runs rosbridge
"""
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    rosbridge_share = FindPackageShare("rosbridge_server")

    arm_relay = Node(
        package="evo_web",
        executable="arm_command_relay_node",
        name="arm_command_relay",
        parameters=[{
            "input_topic": "/evo/arm/command",
            "output_topic": "/arm6_joints",
        }],
        output="screen",
    )

    web_server = Node(
        package="evo_web",
        executable="web_server_node",
        name="web_server_node",
        parameters=[{
            # Do not call this launch argument "port". The included rosbridge
            # launch also declares "port", and ROS 2 Humble includes can
            # overwrite the parent launch configuration with their value.
            "port": ParameterValue(LaunchConfiguration("http_port"), value_type=int),
            "camera_topic": LaunchConfiguration("camera_topic"),
            "max_fps": ParameterValue(LaunchConfiguration("camera_max_fps"), value_type=float),
            "max_width": ParameterValue(LaunchConfiguration("camera_max_width"), value_type=int),
            "jpeg_quality": ParameterValue(LaunchConfiguration("camera_jpeg_quality"), value_type=int),
        }],
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument("http_port", default_value="8080",
                              description="HTTP port for the dashboard"),
        DeclareLaunchArgument("camera_topic", default_value="/camera/color/image_raw"),
        DeclareLaunchArgument("camera_max_fps", default_value="8.0",
                              description="Maximum JPEG encode rate for the HTTP camera stream"),
        DeclareLaunchArgument("camera_max_width", default_value="640",
                              description="Maximum HTTP camera stream width; 0 keeps native width"),
        DeclareLaunchArgument("camera_jpeg_quality", default_value="60",
                              description="JPEG quality for the HTTP camera stream"),
        DeclareLaunchArgument("rosbridge_port", default_value="9090",
                              description="WebSocket port for rosbridge"),
        DeclareLaunchArgument("rosbridge", default_value="true",
                              description="Start rosbridge_websocket (skip if another launch already runs it)"),

        # --- rosbridge WebSocket server ---
        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(
                PathJoinSubstitution([rosbridge_share, "launch", "rosbridge_websocket_launch.xml"])
            ),
            launch_arguments={
                "port": LaunchConfiguration("rosbridge_port"),
                "address": "0.0.0.0",
            }.items(),
            condition=IfCondition(LaunchConfiguration("rosbridge")),
        ),

        # rosbridge alone is not a functional dashboard. Shut the complete
        # launch down if either required bridge exits, so the browser cannot
        # remain "connected" while camera or arm traffic is unavailable.
        RegisterEventHandler(
            OnProcessExit(
                target_action=arm_relay,
                on_exit=[EmitEvent(event=Shutdown(
                    reason="Required arm command relay exited",
                ))],
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=web_server,
                on_exit=[EmitEvent(event=Shutdown(
                    reason="Required camera HTTP server exited",
                ))],
            )
        ),

        # Native QoS boundary for browser arm commands. The micro-ROS firmware
        # consumes /arm6_joints with volatile durability.
        arm_relay,

        # --- Web file server + camera snapshot/MJPEG ---
        web_server,
    ])
