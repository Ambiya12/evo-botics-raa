from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    camera_topic = LaunchConfiguration("camera_topic")
    depth_topic = LaunchConfiguration("depth_topic")
    depth_camera_info_topic = LaunchConfiguration("depth_camera_info_topic")
    use_sim_time = LaunchConfiguration("use_sim_time")

    return LaunchDescription([
        DeclareLaunchArgument("camera_topic", default_value="/camera/color/image_raw"),
        DeclareLaunchArgument("depth_topic", default_value="/camera/depth/image_raw"),
        DeclareLaunchArgument(
            "depth_camera_info_topic",
            default_value="/camera/depth/camera_info",
        ),
        DeclareLaunchArgument("enable_qr", default_value="true"),
        DeclareLaunchArgument("enable_depth_obstacles", default_value="true"),
        DeclareLaunchArgument("enable_object_detection", default_value="false"),
        DeclareLaunchArgument("qr_decoder_backend", default_value="auto"),
        DeclareLaunchArgument(
            "qr_detections_topic", default_value="/vision/qr/detections"
        ),
        DeclareLaunchArgument("qr_status_topic", default_value="/vision/qr/status"),
        DeclareLaunchArgument("qr_cooldown_sec", default_value="2.0"),
        DeclareLaunchArgument("qr_min_scan_interval_sec", default_value="0.25"),
        DeclareLaunchArgument("qr_max_width", default_value="640"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),

        Node(
            package="evo_vision",
            executable="qr_scanner_node",
            name="qr_scanner_node",
            parameters=[
                {
                    "camera_topic": camera_topic,
                    "decoder_backend": LaunchConfiguration("qr_decoder_backend"),
                    "detections_topic": LaunchConfiguration(
                        "qr_detections_topic"
                    ),
                    "status_topic": LaunchConfiguration("qr_status_topic"),
                    "cooldown_sec": ParameterValue(
                        LaunchConfiguration("qr_cooldown_sec"), value_type=float
                    ),
                    "min_scan_interval_sec": ParameterValue(
                        LaunchConfiguration("qr_min_scan_interval_sec"),
                        value_type=float,
                    ),
                    "max_width": ParameterValue(
                        LaunchConfiguration("qr_max_width"), value_type=int
                    ),
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
                    "camera_info_topic": depth_camera_info_topic,
                    "pointcloud_topic": "/vision/obstacles/points",
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
