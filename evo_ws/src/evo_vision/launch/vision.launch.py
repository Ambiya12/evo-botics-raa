from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    camera_topic = LaunchConfiguration("camera_topic")
    depth_topic = LaunchConfiguration("depth_topic")
    use_sim_time = LaunchConfiguration("use_sim_time")

    return LaunchDescription([
        DeclareLaunchArgument("camera_topic", default_value="/camera/color/image_raw"),
        DeclareLaunchArgument("depth_topic", default_value="/camera/depth/image_raw"),
        DeclareLaunchArgument("enable_qr", default_value="true"),
        DeclareLaunchArgument("enable_depth_obstacles", default_value="true"),
        DeclareLaunchArgument("enable_object_detection", default_value="false"),
        DeclareLaunchArgument("qr_decoder_backend", default_value="auto"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),

        Node(
            package="evo_vision",
            executable="qr_scanner_node",
            name="qr_scanner_node",
            parameters=[
                {
                    "camera_topic": camera_topic,
                    "decoder_backend": LaunchConfiguration("qr_decoder_backend"),
                    "use_sim_time": use_sim_time,
                }
            ],
            condition=IfCondition(LaunchConfiguration("enable_qr")),
            output="screen",
        ),
        Node(
            package="evo_vision",
            executable="depth_obstacle_scan_node",
            name="depth_obstacle_scan_node",
            parameters=[
                {
                    "depth_topic": depth_topic,
                    "use_sim_time": use_sim_time,
                }
            ],
            condition=IfCondition(LaunchConfiguration("enable_depth_obstacles")),
            output="screen",
        ),
        Node(
            package="evo_vision",
            executable="object_detector_node",
            name="object_detector_node",
            parameters=[
                {
                    "enabled": False,
                    "use_sim_time": use_sim_time,
                }
            ],
            condition=IfCondition(LaunchConfiguration("enable_object_detection")),
            output="screen",
        ),
    ])
