from pathlib import Path
import tempfile

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    temporary_directory = Path(tempfile.gettempdir())

    return LaunchDescription([
        DeclareLaunchArgument("model_path", default_value=""),
        DeclareLaunchArgument("device", default_value="cpu"),
        DeclareLaunchArgument("language", default_value="auto"),
        DeclareLaunchArgument("audio_device", default_value="-1"),
        DeclareLaunchArgument("french_voice_path", default_value=""),
        DeclareLaunchArgument("english_voice_path", default_value=""),
        DeclareLaunchArgument(
            "capture_path",
            default_value=str(temporary_directory / "evo_voice_capture.wav"),
        ),
        DeclareLaunchArgument(
            "playback_path",
            default_value=str(temporary_directory / "evo_voice_playback.wav"),
        ),
        DeclareLaunchArgument("mock_audio", default_value="true"),

        Node(
            package="evo_voice",
            executable="translator_node",
            name="translator_node",
            parameters=[{
                "model_path": LaunchConfiguration("model_path"),
                "device": LaunchConfiguration("device"),
                "language": LaunchConfiguration("language"),
                "audio_device": ParameterValue(
                    LaunchConfiguration("audio_device"), value_type=int
                ),
                "french_voice_path": LaunchConfiguration("french_voice_path"),
                "english_voice_path": LaunchConfiguration("english_voice_path"),
                "capture_path": LaunchConfiguration("capture_path"),
                "playback_path": LaunchConfiguration("playback_path"),
                "mock_audio": ParameterValue(
                    LaunchConfiguration("mock_audio"), value_type=bool
                ),
            }],
            output="screen",
        ),
    ])
