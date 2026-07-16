from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import tempfile
import time

from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from evo_voice._utils import coerce_path
from evo_voice.phrases import PhraseBook, PhraseConfigurationError
from evo_voice.tts_queue import (
    PiperSpeechPlayer,
    QueuedTts,
    SpeakRequest,
    SpeechProcessError,
)


@dataclass(frozen=True)
class TtsConfig:
    model_path: Path
    output_path: Path
    cache_directory: Path
    piper_executable: str
    audio_player_executable: str
    audio_output_device: str
    synthesis_timeout_sec: float
    playback_timeout_sec: float

    def validate(self) -> None:
        errors: list[str] = []
        if self.model_path == Path():
            errors.append("'piper_model_path' is required")
        elif not self.model_path.is_file():
            errors.append(f"'piper_model_path' does not exist: {self.model_path}")
        if not self.output_path.name:
            errors.append("'output_path' must name a file")
        elif not self.output_path.parent.is_dir():
            errors.append(f"'output_path' parent does not exist: {self.output_path.parent}")
        if not self.cache_directory.name:
            errors.append("'cache_directory' must name a directory")
        if self.synthesis_timeout_sec <= 0.0:
            errors.append("'synthesis_timeout_sec' must be greater than zero")
        if self.playback_timeout_sec <= 0.0:
            errors.append("'playback_timeout_sec' must be greater than zero")
        for parameter, executable in (
            ("piper_executable", self.piper_executable),
            ("audio_player_executable", self.audio_player_executable),
        ):
            if not executable:
                errors.append(f"'{parameter}' must not be empty")
            elif shutil.which(executable) is None:
                errors.append(f"executable configured by '{parameter}' was not found")
        if errors:
            raise TtsConfigurationError(
                "Invalid evo_voice TTS configuration: " + "; ".join(errors)
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
        diagnostics_topic = str(
            self.declare_parameter(
                "diagnostics_topic", "/voice/tts/diagnostics"
            ).value
        )
        config = TtsConfig(
            model_path=coerce_path(self.declare_parameter("piper_model_path", "").value),
            output_path=coerce_path(
                self.declare_parameter(
                    "output_path",
                    str(Path(tempfile.gettempdir()) / "evo_voice_tts.wav"),
                ).value
            ),
            cache_directory=coerce_path(
                self.declare_parameter(
                    "cache_directory",
                    str(Path(tempfile.gettempdir()) / "evo_voice_tts_cache"),
                ).value
            ),
            piper_executable=str(self.declare_parameter("piper_executable", "piper").value).strip(),
            audio_player_executable=str(self.declare_parameter("audio_player_executable", "mpv").value).strip(),
            audio_output_device=str(self.declare_parameter("audio_output_device", "").value).strip(),
            synthesis_timeout_sec=float(self.declare_parameter("synthesis_timeout_sec", 30.0).value),
            playback_timeout_sec=float(self.declare_parameter("playback_timeout_sec", 30.0).value),
        )
        config.validate()

        phrase_config_path = coerce_path(
            self.declare_parameter(
                "phrase_config_path",
                str(
                    Path(get_package_share_directory("evo_voice"))
                    / "config"
                    / "reception_phrases.yaml"
                ),
            ).value
        )
        self.phrase_book = PhraseBook.from_yaml(phrase_config_path)
        self.audio_output_device = config.audio_output_device
        self.request_counter = 0

        player = PiperSpeechPlayer(
            model_path=config.model_path,
            output_path=config.output_path,
            piper_executable=config.piper_executable,
            audio_player_executable=config.audio_player_executable,
            audio_output_device=config.audio_output_device,
            cache_directory=config.cache_directory,
            prewarm_texts=(self.phrase_book.resolve_request("phrase:greeting"),),
            synthesis_timeout_sec=config.synthesis_timeout_sec,
            playback_timeout_sec=config.playback_timeout_sec,
            latency_callback=self.log_latency,
        )

        status_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.status_publisher = self.create_publisher(String, status_topic, status_qos)
        self.diagnostics_publisher = self.create_publisher(
            String, diagnostics_topic, status_qos
        )
        self.tts_queue = QueuedTts(
            player,
            self.publish_status,
            self.on_playback_error,
        )
        self.create_subscription(String, request_topic, self.on_speak_request, 10)
        self.publish_diagnostic(
            "ready",
            backend="piper",
            audio_output_device=config.audio_output_device or "system-default",
        )
        self.get_logger().info(
            f"Queued TTS ready: request={request_topic} status={status_topic} "
            f"audio_output_device={config.audio_output_device or '<system-default>'}"
        )

    def on_speak_request(self, message: String) -> None:
        try:
            text = self.phrase_book.resolve_request(message.data)
            self.request_counter += 1
            request_id = f"tts-{self.request_counter}"
            self.tts_queue.enqueue(
                SpeakRequest(text=text, request_id=request_id)
            )
            self.get_logger().info(
                f"Queued TTS request: request_id={request_id} "
                f"characters={len(text)}"
            )
        except ValueError as exc:
            self.get_logger().error(str(exc))

    def publish_status(self, status: str) -> None:
        self.status_publisher.publish(String(data=status))
        self.get_logger().info(f"TTS status={status}")

    def log_latency(self, phase: str, duration: float) -> None:
        self.get_logger().info(f"TTS latency: {phase}={duration:.3f}")
        if hasattr(self, "diagnostics_publisher"):
            self.publish_diagnostic(
                "latency",
                phase=phase,
                duration_sec=duration,
            )

    def on_playback_error(
        self,
        request: SpeakRequest,
        error: Exception,
    ) -> None:
        details: dict[str, object] = {
            "request_id": request.request_id,
            "audio_output_device": (
                self.audio_output_device or "system-default"
            ),
            "error": str(error),
        }
        if isinstance(error, SpeechProcessError):
            details.update(
                phase=error.phase,
                command=list(error.command),
                timeout_sec=error.timeout_sec,
                return_code=error.return_code,
            )
        self.get_logger().error(
            f"TTS request failed: request_id={request.request_id} "
            f"error={error}"
        )
        self.publish_diagnostic("playback_failed", **details)

    def publish_diagnostic(self, event: str, **details: object) -> None:
        self.diagnostics_publisher.publish(
            String(
                data=json.dumps(
                    {"event": event, "timestamp": time.time(), **details},
                    ensure_ascii=False,
                )
            )
        )

    def destroy_node(self) -> bool:
        self.tts_queue.shutdown()
        return super().destroy_node()


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
