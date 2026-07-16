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
        DeclareLaunchArgument("person_model_path", default_value=""),
        DeclareLaunchArgument(
            "people_detections_topic",
            default_value="/vision/people/detections",
        ),
        DeclareLaunchArgument(
            "person_detector_status_topic",
            default_value="/vision/people/detector_status",
        ),
        DeclareLaunchArgument("person_input_size", default_value="640"),
        DeclareLaunchArgument("person_confidence_threshold", default_value="0.55"),
        DeclareLaunchArgument("person_nms_threshold", default_value="0.45"),
        DeclareLaunchArgument("person_max_fps", default_value="5.0"),
        DeclareLaunchArgument("person_depth_sync_tolerance_sec", default_value="0.5"),
        DeclareLaunchArgument("person_depth_timeout_sec", default_value="0.75"),
        DeclareLaunchArgument("person_depth_roi_fraction", default_value="0.35"),
        DeclareLaunchArgument("person_min_depth_m", default_value="0.2"),
        DeclareLaunchArgument("person_max_depth_m", default_value="5.0"),
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
                    "color_topic": camera_topic,
                    "depth_topic": depth_topic,
                    "detections_topic": LaunchConfiguration(
                        "people_detections_topic"
                    ),
                    "status_topic": LaunchConfiguration(
                        "person_detector_status_topic"
                    ),
                    "model_path": LaunchConfiguration("person_model_path"),
                    "input_size": ParameterValue(
                        LaunchConfiguration("person_input_size"),
                        value_type=int,
                    ),
                    "confidence_threshold": ParameterValue(
                        LaunchConfiguration("person_confidence_threshold"),
                        value_type=float,
                    ),
                    "nms_threshold": ParameterValue(
                        LaunchConfiguration("person_nms_threshold"),
                        value_type=float,
                    ),
                    "max_fps": ParameterValue(
                        LaunchConfiguration("person_max_fps"),
                        value_type=float,
                    ),
                    "depth_sync_tolerance_sec": ParameterValue(
                        LaunchConfiguration(
                            "person_depth_sync_tolerance_sec"
                        ),
                        value_type=float,
                    ),
                    "depth_timeout_sec": ParameterValue(
                        LaunchConfiguration("person_depth_timeout_sec"),
                        value_type=float,
                    ),
                    "depth_roi_fraction": ParameterValue(
                        LaunchConfiguration("person_depth_roi_fraction"),
                        value_type=float,
                    ),
                    "min_depth_m": ParameterValue(
                        LaunchConfiguration("person_min_depth_m"),
                        value_type=float,
                    ),
                    "max_depth_m": ParameterValue(
                        LaunchConfiguration("person_max_depth_m"),
                        value_type=float,
                    ),
                    "use_sim_time": use_sim_time,
                }
            ],
            condition=IfCondition(LaunchConfiguration("enable_object_detection")),
            output="screen",
        ),
    ])
