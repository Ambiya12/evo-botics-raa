from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_config = PathJoinSubstitution(
        [FindPackageShare("evo_voice"), "config", "reception_intents.yaml"]
    )

    return LaunchDescription([
        DeclareLaunchArgument("transcript_topic", default_value="/voice/stt/transcript"),
        DeclareLaunchArgument("result_topic", default_value="/voice/intent/result"),
        DeclareLaunchArgument(
            "dialogue_state_topic", default_value="/reception/dialogue/state"
        ),
        DeclareLaunchArgument(
            "diagnostics_topic", default_value="/voice/intent/diagnostics"
        ),
        DeclareLaunchArgument("intent_config_path", default_value=default_config),

        Node(
            package="evo_voice",
            executable="intent_detector_node",
            name="intent_detector_node",
            parameters=[{
                "transcript_topic": LaunchConfiguration("transcript_topic"),
                "result_topic": LaunchConfiguration("result_topic"),
                "dialogue_state_topic": LaunchConfiguration(
                    "dialogue_state_topic"
                ),
                "diagnostics_topic": LaunchConfiguration("diagnostics_topic"),
                "intent_config_path": LaunchConfiguration("intent_config_path"),
            }],
            output="screen",
        ),
    ])
