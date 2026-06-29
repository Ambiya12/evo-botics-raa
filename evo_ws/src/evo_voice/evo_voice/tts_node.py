from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from evo_voice.phrases import PhraseBook, PhraseConfigurationError
from evo_voice.tts_queue import (
    MockSpeechPlayer,
    PiperSpeechPlayer,
    QueuedTts,
    SpeakRequest,
)


class TtsConfigurationError(ValueError):
    """Raised when the TTS node cannot start with its configured backend."""


class TtsNode(Node):
    def __init__(self) -> None:
        super().__init__("tts_node")

        request_topic = str(
            self.declare_parameter("request_topic", "/voice/tts/request").value
        )
        status_topic = str(
            self.declare_parameter("status_topic", "/voice/tts/status").value
        )
        self.mock_audio = bool(self.declare_parameter("mock_audio", True).value)
        model_path = _path(self.declare_parameter("piper_model_path", "").value)
        phrase_config_path = _path(
            self.declare_parameter(
                "phrase_config_path",
                str(
                    Path(get_package_share_directory("evo_voice"))
                    / "config"
                    / "reception_phrases.yaml"
                ),
            ).value
        )
        output_path = _path(
            self.declare_parameter(
                "output_path",
                str(Path(tempfile.gettempdir()) / "evo_voice_tts.wav"),
            ).value
        )
        piper_executable = str(
            self.declare_parameter("piper_executable", "piper").value
        ).strip()
        audio_player_executable = str(
            self.declare_parameter("audio_player_executable", "mpv").value
        ).strip()

        self.phrase_book = PhraseBook.from_yaml(phrase_config_path)
        player = self._create_player(
            model_path,
            output_path,
            piper_executable,
            audio_player_executable,
        )

        status_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.status_publisher = self.create_publisher(String, status_topic, status_qos)
        self.tts_queue = QueuedTts(player, self.publish_status)
        self.create_subscription(String, request_topic, self.on_speak_request, 10)
        self.get_logger().info(
            f"Queued TTS ready: request={request_topic} status={status_topic} "
            f"mock_audio={self.mock_audio}"
        )

    def _create_player(
        self,
        model_path: Path,
        output_path: Path,
        piper_executable: str,
        audio_player_executable: str,
    ):
        if self.mock_audio:
            return MockSpeechPlayer()

        errors: list[str] = []
        if model_path == Path():
            errors.append("'piper_model_path' is required when mock_audio is false")
        elif not model_path.is_file():
            errors.append(f"'piper_model_path' does not exist: {model_path}")
        if not output_path.name:
            errors.append("'output_path' must name a file")
        elif not output_path.parent.is_dir():
            errors.append(f"'output_path' parent does not exist: {output_path.parent}")
        for parameter, executable in (
            ("piper_executable", piper_executable),
            ("audio_player_executable", audio_player_executable),
        ):
            if not executable:
                errors.append(f"'{parameter}' must not be empty")
            elif shutil.which(executable) is None:
                errors.append(f"executable configured by '{parameter}' was not found")
        if errors:
            raise TtsConfigurationError(
                "Invalid evo_voice TTS configuration: " + "; ".join(errors)
            )

        return PiperSpeechPlayer(
            model_path=model_path,
            output_path=output_path,
            piper_executable=piper_executable,
            audio_player_executable=audio_player_executable,
        )

    def on_speak_request(self, message: String) -> None:
        try:
            text = self.phrase_book.resolve_request(message.data)
            self.tts_queue.enqueue(SpeakRequest(text=text))
        except ValueError as exc:
            self.get_logger().error(str(exc))

    def publish_status(self, status: str) -> None:
        self.status_publisher.publish(String(data=status))

    def destroy_node(self) -> bool:
        self.tts_queue.shutdown()
        return super().destroy_node()


def _path(value: object) -> Path:
    text = str(value).strip()
    return Path(text).expanduser() if text else Path()


def main(args=None) -> None:
    rclpy.init(args=args)
    node: TtsNode | None = None
    try:
        node = TtsNode()
        rclpy.spin(node)
    except (PhraseConfigurationError, TtsConfigurationError) as exc:
        rclpy.logging.get_logger("tts_node").fatal(str(exc))
        raise SystemExit(2) from exc
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
