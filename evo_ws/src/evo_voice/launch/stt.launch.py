from pathlib import Path
import tempfile

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("transcript_topic", default_value="/voice/stt/transcript"),
        DeclareLaunchArgument("status_topic", default_value="/voice/stt/status"),
        DeclareLaunchArgument(
            "diagnostics_topic", default_value="/voice/stt/diagnostics"
        ),
        DeclareLaunchArgument("tts_status_topic", default_value="/voice/tts/status"),
        DeclareLaunchArgument(
            "dialogue_state_topic", default_value="/reception/dialogue/state"
        ),
        DeclareLaunchArgument("model_path", default_value=""),
        DeclareLaunchArgument("device", default_value="cpu"),
        DeclareLaunchArgument("compute_type", default_value="int8"),
        DeclareLaunchArgument("language", default_value="auto"),
        DeclareLaunchArgument("microphone_device", default_value="-1"),
        DeclareLaunchArgument("listen_timeout_sec", default_value="1.0"),
        DeclareLaunchArgument("phrase_time_limit_sec", default_value="10.0"),
        DeclareLaunchArgument("pause_threshold_sec", default_value="0.4"),
        DeclareLaunchArgument("non_speaking_duration_sec", default_value="0.2"),
        DeclareLaunchArgument("vad_rms_threshold", default_value="0.01"),
        DeclareLaunchArgument("minimum_confidence", default_value="0.4"),
        DeclareLaunchArgument(
            "capture_path",
            default_value=str(Path(tempfile.gettempdir()) / "evo_voice_stt.wav"),
        ),
        Node(
            package="evo_voice",
            executable="stt_node",
            name="stt_node",
            parameters=[{
                "transcript_topic": LaunchConfiguration("transcript_topic"),
                "status_topic": LaunchConfiguration("status_topic"),
                "diagnostics_topic": LaunchConfiguration("diagnostics_topic"),
                "tts_status_topic": LaunchConfiguration("tts_status_topic"),
                "dialogue_state_topic": LaunchConfiguration(
                    "dialogue_state_topic"
                ),
                "model_path": LaunchConfiguration("model_path"),
                "device": LaunchConfiguration("device"),
                "compute_type": LaunchConfiguration("compute_type"),
                "language": LaunchConfiguration("language"),
                "microphone_device": ParameterValue(
                    LaunchConfiguration("microphone_device"), value_type=int
                ),
                "listen_timeout_sec": ParameterValue(
                    LaunchConfiguration("listen_timeout_sec"), value_type=float
                ),
                "phrase_time_limit_sec": ParameterValue(
                    LaunchConfiguration("phrase_time_limit_sec"), value_type=float
                ),
                "pause_threshold_sec": ParameterValue(
                    LaunchConfiguration("pause_threshold_sec"), value_type=float
                ),
                "non_speaking_duration_sec": ParameterValue(
                    LaunchConfiguration("non_speaking_duration_sec"),
                    value_type=float,
                ),
                "vad_rms_threshold": ParameterValue(
                    LaunchConfiguration("vad_rms_threshold"), value_type=float
                ),
                "minimum_confidence": ParameterValue(
                    LaunchConfiguration("minimum_confidence"), value_type=float
                ),
                "capture_path": LaunchConfiguration("capture_path"),
            }],
            output="screen",
        ),
    ])
