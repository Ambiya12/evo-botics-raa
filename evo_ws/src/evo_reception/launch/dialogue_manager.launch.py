from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("max_retries", default_value="2"),
        DeclareLaunchArgument("inactivity_timeout_sec", default_value="20.0"),
        DeclareLaunchArgument("timer_period_sec", default_value="0.2"),
        DeclareLaunchArgument("intent_topic", default_value="/voice/intent/result"),
        DeclareLaunchArgument("tts_request_topic", default_value="/voice/tts/request"),
        DeclareLaunchArgument("tts_status_topic", default_value="/voice/tts/status"),
        DeclareLaunchArgument(
            "event_topic", default_value="/reception/dialogue/event"
        ),
        DeclareLaunchArgument(
            "state_topic", default_value="/reception/dialogue/state"
        ),
        DeclareLaunchArgument(
            "qr_detections_topic", default_value="/vision/qr/detections"
        ),
        DeclareLaunchArgument(
            "qr_validation_service", default_value="/reception/qr/validate"
        ),
        DeclareLaunchArgument("duplicate_cooldown_sec", default_value="5.0"),
        DeclareLaunchArgument(
            "guide_action_name", default_value="/reception/guide_to_destination"
        ),
        DeclareLaunchArgument(
            "approach_topic", default_value="/vision/people/approach"
        ),
        DeclareLaunchArgument(
            "workflow_status_topic", default_value="/reception/workflow/status"
        ),

        Node(
            package="evo_reception",
            executable="dialogue_manager_node",
            name="dialogue_manager_node",
            parameters=[{
                "max_retries": ParameterValue(
                    LaunchConfiguration("max_retries"), value_type=int
                ),
                "inactivity_timeout_sec": ParameterValue(
                    LaunchConfiguration("inactivity_timeout_sec"), value_type=float
                ),
                "timer_period_sec": ParameterValue(
                    LaunchConfiguration("timer_period_sec"), value_type=float
                ),
                "intent_topic": LaunchConfiguration("intent_topic"),
                "tts_request_topic": LaunchConfiguration("tts_request_topic"),
                "tts_status_topic": LaunchConfiguration("tts_status_topic"),
                "event_topic": LaunchConfiguration("event_topic"),
                "state_topic": LaunchConfiguration("state_topic"),
                "qr_detections_topic": LaunchConfiguration(
                    "qr_detections_topic"
                ),
                "qr_validation_service": LaunchConfiguration(
                    "qr_validation_service"
                ),
                "duplicate_cooldown_sec": ParameterValue(
                    LaunchConfiguration("duplicate_cooldown_sec"), value_type=float
                ),
                "guide_action_name": LaunchConfiguration("guide_action_name"),
                "approach_topic": LaunchConfiguration("approach_topic"),
                "workflow_status_topic": LaunchConfiguration(
                    "workflow_status_topic"
                ),
            }],
            output="screen",
        ),
    ])
