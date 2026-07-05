"""Reception voice stack with independent, safe-by-default audio backends."""

from pathlib import Path
import tempfile

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def include_voice_launch(filename: str, arguments: dict):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare("evo_voice"),
                "launch",
                filename,
            ])
        ),
        launch_arguments=arguments.items(),
    )


def generate_launch_description():
    temporary_directory = Path(tempfile.gettempdir())

    return LaunchDescription([
        DeclareLaunchArgument("tts_mock_audio", default_value="true"),
        DeclareLaunchArgument("piper_model_path", default_value=""),
        DeclareLaunchArgument("audio_output_device", default_value=""),
        DeclareLaunchArgument("piper_executable", default_value="piper"),
        DeclareLaunchArgument("audio_player_executable", default_value="mpv"),
        DeclareLaunchArgument(
            "tts_output_path",
            default_value=str(temporary_directory / "evo_voice_tts.wav"),
        ),
        DeclareLaunchArgument("stt_mock_audio", default_value="true"),
        DeclareLaunchArgument("stt_model_path", default_value=""),
        DeclareLaunchArgument("stt_device", default_value="cpu"),
        DeclareLaunchArgument("stt_compute_type", default_value="int8"),
        DeclareLaunchArgument("language", default_value="en"),
        DeclareLaunchArgument("microphone_device", default_value="-1"),
        DeclareLaunchArgument("listen_timeout_sec", default_value="1.0"),
        DeclareLaunchArgument("phrase_time_limit_sec", default_value="10.0"),
        DeclareLaunchArgument("vad_rms_threshold", default_value="0.01"),
        DeclareLaunchArgument("minimum_confidence", default_value="0.4"),
        DeclareLaunchArgument(
            "stt_capture_path",
            default_value=str(temporary_directory / "evo_voice_stt.wav"),
        ),
        include_voice_launch(
            "tts.launch.py",
            {
                "mock_audio": LaunchConfiguration("tts_mock_audio"),
                "piper_model_path": LaunchConfiguration("piper_model_path"),
                "audio_output_device": LaunchConfiguration(
                    "audio_output_device"
                ),
                "piper_executable": LaunchConfiguration("piper_executable"),
                "audio_player_executable": LaunchConfiguration(
                    "audio_player_executable"
                ),
                "output_path": LaunchConfiguration("tts_output_path"),
            },
        ),
        include_voice_launch(
            "stt.launch.py",
            {
                "mock_audio": LaunchConfiguration("stt_mock_audio"),
                "model_path": LaunchConfiguration("stt_model_path"),
                "device": LaunchConfiguration("stt_device"),
                "compute_type": LaunchConfiguration("stt_compute_type"),
                "language": LaunchConfiguration("language"),
                "microphone_device": LaunchConfiguration("microphone_device"),
                "listen_timeout_sec": LaunchConfiguration("listen_timeout_sec"),
                "phrase_time_limit_sec": LaunchConfiguration(
                    "phrase_time_limit_sec"
                ),
                "vad_rms_threshold": LaunchConfiguration("vad_rms_threshold"),
                "minimum_confidence": LaunchConfiguration("minimum_confidence"),
                "capture_path": LaunchConfiguration("stt_capture_path"),
            },
        ),
        include_voice_launch("intent_detector.launch.py", {}),
    ])
