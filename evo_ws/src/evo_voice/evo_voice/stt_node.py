from __future__ import annotations

from pathlib import Path
from threading import Event, Thread
import tempfile

from evo_reception_interfaces.msg import Transcript
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from evo_voice.stt import (
    CaptureGate,
    FasterWhisperTranscriber,
    MockTranscriber,
    SttPipeline,
    TranscriptionResult,
    WavEnergyVad,
)


class SttConfigurationError(ValueError):
    """Raised when STT cannot start with its configured backend."""


class SttNode(Node):
    def __init__(self) -> None:
        super().__init__("stt_node")

        transcript_topic = str(
            self.declare_parameter("transcript_topic", "/voice/stt/transcript").value
        )
        tts_status_topic = str(
            self.declare_parameter("tts_status_topic", "/voice/tts/status").value
        )
        mock_audio_topic = str(
            self.declare_parameter(
                "mock_audio_topic", "/voice/stt/mock_audio_path"
            ).value
        )
        self.mock_audio = bool(self.declare_parameter("mock_audio", True).value)
        model_path = _path(self.declare_parameter("model_path", "").value)
        device = str(self.declare_parameter("device", "cpu").value).strip()
        compute_type = str(
            self.declare_parameter("compute_type", "int8").value
        ).strip()
        language = str(
            self.declare_parameter("language", "auto").value
        ).strip().lower()
        self.microphone_device = int(
            self.declare_parameter("microphone_device", -1).value
        )
        self.listen_timeout_sec = float(
            self.declare_parameter("listen_timeout_sec", 1.0).value
        )
        self.phrase_time_limit_sec = float(
            self.declare_parameter("phrase_time_limit_sec", 10.0).value
        )
        vad_rms_threshold = float(
            self.declare_parameter("vad_rms_threshold", 0.01).value
        )
        minimum_confidence = float(
            self.declare_parameter("minimum_confidence", 0.4).value
        )
        capture_path = _path(
            self.declare_parameter(
                "capture_path",
                str(Path(tempfile.gettempdir()) / "evo_voice_stt.wav"),
            ).value
        )
        mock_text = str(
            self.declare_parameter(
                "mock_transcript_text", "This is a mock transcript."
            ).value
        )
        mock_language = str(
            self.declare_parameter("mock_language", "en").value
        )
        mock_confidence = float(
            self.declare_parameter("mock_confidence", 0.95).value
        )
        mock_failure = bool(
            self.declare_parameter("mock_transcription_failure", False).value
        )

        self._validate_common(
            language,
            device,
            compute_type,
            capture_path,
            minimum_confidence,
            vad_rms_threshold,
            self.microphone_device,
            self.listen_timeout_sec,
            self.phrase_time_limit_sec,
            mock_confidence,
        )
        self.capture_gate = CaptureGate()
        if self.mock_audio:
            transcriber = MockTranscriber(
                TranscriptionResult(
                    text=mock_text,
                    language=mock_language,
                    confidence=mock_confidence,
                ),
                fail=mock_failure,
            )
        else:
            if model_path == Path() or not model_path.exists():
                raise SttConfigurationError(
                    "'model_path' must reference a local Faster Whisper model "
                    "when mock_audio is false"
                )
            transcriber = FasterWhisperTranscriber(
                model_path=model_path,
                capture_path=capture_path,
                device=device,
                compute_type=compute_type,
                language=language,
            )

        self.pipeline = SttPipeline(
            transcriber=transcriber,
            vad=WavEnergyVad(vad_rms_threshold),
            capture_gate=self.capture_gate,
            minimum_confidence=minimum_confidence,
            error_callback=self.on_transcription_error,
        )
        self.transcript_publisher = self.create_publisher(
            Transcript, transcript_topic, 10
        )
        tts_status_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            String, tts_status_topic, self.on_tts_status, tts_status_qos
        )

        self.stop_event = Event()
        self.capture_thread: Thread | None = None
        if self.mock_audio:
            self.create_subscription(
                String, mock_audio_topic, self.on_mock_audio_path, 10
            )
        else:
            self.capture_thread = Thread(
                target=self.microphone_loop,
                name="evo-stt-microphone",
                daemon=True,
            )
            self.capture_thread.start()

        self.get_logger().info(
            f"STT ready: transcript={transcript_topic} "
            f"tts_status={tts_status_topic} mock_audio={self.mock_audio}"
        )

    @staticmethod
    def _validate_common(
        language: str,
        device: str,
        compute_type: str,
        capture_path: Path,
        minimum_confidence: float,
        vad_rms_threshold: float,
        microphone_device: int,
        listen_timeout_sec: float,
        phrase_time_limit_sec: float,
        mock_confidence: float,
    ) -> None:
        errors: list[str] = []
        if language not in {"auto", "en", "fr"}:
            errors.append("'language' must be one of: auto, en, fr")
        if not device:
            errors.append("'device' must not be empty")
        if not compute_type:
            errors.append("'compute_type' must not be empty")
        if not capture_path.name:
            errors.append("'capture_path' must name a file")
        elif not capture_path.parent.is_dir():
            errors.append(f"'capture_path' parent does not exist: {capture_path.parent}")
        if not 0.0 <= minimum_confidence <= 1.0:
            errors.append("'minimum_confidence' must be between 0.0 and 1.0")
        if not 0.0 <= vad_rms_threshold <= 1.0:
            errors.append("'vad_rms_threshold' must be between 0.0 and 1.0")
        if microphone_device < -1:
            errors.append(
                "'microphone_device' must be -1 or a non-negative device index"
            )
        if listen_timeout_sec <= 0.0:
            errors.append("'listen_timeout_sec' must be greater than zero")
        if phrase_time_limit_sec <= 0.0:
            errors.append("'phrase_time_limit_sec' must be greater than zero")
        if not 0.0 <= mock_confidence <= 1.0:
            errors.append("'mock_confidence' must be between 0.0 and 1.0")
        if errors:
            raise SttConfigurationError(
                "Invalid evo_voice STT configuration: " + "; ".join(errors)
            )

    def on_tts_status(self, message: String) -> None:
        self.capture_gate.update_tts_status(message.data)

    def on_mock_audio_path(self, message: String) -> None:
        path = _path(message.data)
        try:
            wav_data = path.read_bytes()
        except OSError as exc:
            self.get_logger().error(f"Could not read mock audio fixture {path}: {exc}")
            return
        self.process_audio(wav_data)

    def microphone_loop(self) -> None:
        import speech_recognition as sr

        device_index = None if self.microphone_device == -1 else self.microphone_device
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone(device_index=device_index) as source:
                while rclpy.ok() and not self.stop_event.is_set():
                    if self.capture_gate.paused:
                        self.stop_event.wait(0.05)
                        continue
                    try:
                        audio = recognizer.listen(
                            source,
                            timeout=self.listen_timeout_sec,
                            phrase_time_limit=self.phrase_time_limit_sec,
                        )
                    except sr.WaitTimeoutError:
                        continue
                    if self.stop_event.is_set():
                        break
                    if not self.capture_gate.paused:
                        self.process_audio(audio.get_wav_data())
        except Exception as exc:
            self.get_logger().error(f"Microphone capture stopped: {exc}")

    def process_audio(self, wav_data: bytes) -> None:
        captured_at = self.get_clock().now().to_msg()
        result = self.pipeline.process(wav_data)
        if result is None:
            return
        message = Transcript()
        message.header.stamp = captured_at
        message.text = result.text
        message.language = result.language
        message.confidence = (
            float(result.confidence) if result.confidence is not None else -1.0
        )
        self.transcript_publisher.publish(message)

    def on_transcription_error(self, error: Exception) -> None:
        self.get_logger().error(f"Transcription failed: {error}")

    def destroy_node(self) -> bool:
        self.stop_event.set()
        if self.capture_thread is not None:
            self.capture_thread.join(timeout=2.0)
        return super().destroy_node()


def _path(value: object) -> Path:
    text = str(value).strip()
    return Path(text).expanduser() if text else Path()


def main(args=None) -> None:
    rclpy.init(args=args)
    node: SttNode | None = None
    try:
        node = SttNode()
        rclpy.spin(node)
    except SttConfigurationError as exc:
        rclpy.logging.get_logger("stt_node").fatal(str(exc))
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
