from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "validation_url",
            default_value="http://127.0.0.1:8000/api/reservations/validate",
        ),
        DeclareLaunchArgument("qr_detections_topic", default_value="/vision/qr/detections"),
        DeclareLaunchArgument("status_topic", default_value="/reception/qr/status"),
        DeclareLaunchArgument("request_timeout_sec", default_value="3.0"),
        DeclareLaunchArgument("duplicate_cooldown_sec", default_value="5.0"),
        DeclareLaunchArgument(
            "validation_service", default_value="/reception/qr/validate"
        ),
        DeclareLaunchArgument("enable_legacy_topic_bridge", default_value="false"),
        DeclareLaunchArgument("mock_mode", default_value="false"),
        DeclareLaunchArgument("mock_outcome", default_value="valid"),
        DeclareLaunchArgument("mock_destination_id", default_value="mock-room"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),

        Node(
            package="evo_reception",
            executable="qr_reservation_bridge_node",
            name="qr_reservation_bridge_node",
            parameters=[{
                "validation_url": LaunchConfiguration("validation_url"),
                "qr_detections_topic": LaunchConfiguration("qr_detections_topic"),
                "status_topic": LaunchConfiguration("status_topic"),
                "request_timeout_sec": ParameterValue(
                    LaunchConfiguration("request_timeout_sec"),
                    value_type=float,
                ),
                "duplicate_cooldown_sec": ParameterValue(
                    LaunchConfiguration("duplicate_cooldown_sec"),
                    value_type=float,
                ),
                "validation_service": LaunchConfiguration("validation_service"),
                "enable_legacy_topic_bridge": ParameterValue(
                    LaunchConfiguration("enable_legacy_topic_bridge"),
                    value_type=bool,
                ),
                "mock_mode": ParameterValue(
                    LaunchConfiguration("mock_mode"),
                    value_type=bool,
                ),
                "mock_outcome": LaunchConfiguration("mock_outcome"),
                "mock_destination_id": LaunchConfiguration(
                    "mock_destination_id"
                ),
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }],
            output="screen",
        ),
    ])
