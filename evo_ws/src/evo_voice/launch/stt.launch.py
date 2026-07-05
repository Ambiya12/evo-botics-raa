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
        DeclareLaunchArgument("tts_status_topic", default_value="/voice/tts/status"),
        DeclareLaunchArgument(
            "mock_audio_topic", default_value="/voice/stt/mock_audio_path"
        ),
        DeclareLaunchArgument("mock_audio", default_value="true"),
        DeclareLaunchArgument("model_path", default_value=""),
        DeclareLaunchArgument("device", default_value="cpu"),
        DeclareLaunchArgument("compute_type", default_value="int8"),
        DeclareLaunchArgument("language", default_value="auto"),
        DeclareLaunchArgument("microphone_device", default_value="-1"),
        DeclareLaunchArgument("listen_timeout_sec", default_value="1.0"),
        DeclareLaunchArgument("phrase_time_limit_sec", default_value="10.0"),
        DeclareLaunchArgument("vad_rms_threshold", default_value="0.01"),
        DeclareLaunchArgument("minimum_confidence", default_value="0.4"),
        DeclareLaunchArgument(
            "capture_path",
            default_value=str(Path(tempfile.gettempdir()) / "evo_voice_stt.wav"),
        ),
        DeclareLaunchArgument(
            "mock_transcript_text", default_value="This is a mock transcript."
        ),
        DeclareLaunchArgument("mock_language", default_value="en"),
        DeclareLaunchArgument("mock_confidence", default_value="0.95"),
        DeclareLaunchArgument("mock_transcription_failure", default_value="false"),

        Node(
            package="evo_voice",
            executable="stt_node",
            name="stt_node",
            parameters=[{
                "transcript_topic": LaunchConfiguration("transcript_topic"),
                "tts_status_topic": LaunchConfiguration("tts_status_topic"),
                "mock_audio_topic": LaunchConfiguration("mock_audio_topic"),
                "mock_audio": ParameterValue(
                    LaunchConfiguration("mock_audio"), value_type=bool
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
                "vad_rms_threshold": ParameterValue(
                    LaunchConfiguration("vad_rms_threshold"), value_type=float
                ),
                "minimum_confidence": ParameterValue(
                    LaunchConfiguration("minimum_confidence"), value_type=float
                ),
                "capture_path": LaunchConfiguration("capture_path"),
                "mock_transcript_text": LaunchConfiguration("mock_transcript_text"),
                "mock_language": LaunchConfiguration("mock_language"),
                "mock_confidence": ParameterValue(
                    LaunchConfiguration("mock_confidence"), value_type=float
                ),
                "mock_transcription_failure": ParameterValue(
                    LaunchConfiguration("mock_transcription_failure"), value_type=bool
                ),
            }],
            output="screen",
        ),
    ])
