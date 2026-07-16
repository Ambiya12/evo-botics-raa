from pathlib import Path
import tempfile

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_phrases = PathJoinSubstitution(
        [FindPackageShare("evo_voice"), "config", "reception_phrases.yaml"]
    )

    return LaunchDescription([
        DeclareLaunchArgument("request_topic", default_value="/voice/tts/request"),
        DeclareLaunchArgument("status_topic", default_value="/voice/tts/status"),
        DeclareLaunchArgument(
            "diagnostics_topic", default_value="/voice/tts/diagnostics"
        ),
        DeclareLaunchArgument("piper_model_path", default_value=""),
        DeclareLaunchArgument("phrase_config_path", default_value=default_phrases),
        DeclareLaunchArgument(
            "output_path",
            default_value=str(Path(tempfile.gettempdir()) / "evo_voice_tts.wav"),
        ),
        DeclareLaunchArgument(
            "cache_directory",
            default_value=str(
                Path(tempfile.gettempdir()) / "evo_voice_tts_cache"
            ),
        ),
        DeclareLaunchArgument("piper_executable", default_value="piper"),
        DeclareLaunchArgument("audio_player_executable", default_value="mpv"),
        DeclareLaunchArgument("audio_output_device", default_value=""),
        DeclareLaunchArgument("synthesis_timeout_sec", default_value="30.0"),
        DeclareLaunchArgument("playback_timeout_sec", default_value="30.0"),

        Node(
            package="evo_voice",
            executable="tts_node",
            name="tts_node",
            parameters=[{
                "request_topic": LaunchConfiguration("request_topic"),
                "status_topic": LaunchConfiguration("status_topic"),
                "diagnostics_topic": LaunchConfiguration("diagnostics_topic"),
                "piper_model_path": LaunchConfiguration("piper_model_path"),
                "phrase_config_path": LaunchConfiguration("phrase_config_path"),
                "output_path": LaunchConfiguration("output_path"),
                "cache_directory": LaunchConfiguration("cache_directory"),
                "piper_executable": LaunchConfiguration("piper_executable"),
                "audio_player_executable": LaunchConfiguration(
                    "audio_player_executable"
                ),
                "audio_output_device": LaunchConfiguration(
                    "audio_output_device"
                ),
                "synthesis_timeout_sec": LaunchConfiguration(
                    "synthesis_timeout_sec"
                ),
                "playback_timeout_sec": LaunchConfiguration(
                    "playback_timeout_sec"
                ),
            }],
            output="screen",
        ),
    ])
