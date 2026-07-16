from __future__ import annotations

from pathlib import Path
import json
import time

from ament_index_python.packages import get_package_share_directory
from evo_reception_interfaces.msg import IntentResult, Transcript
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from evo_voice.intent_detector import IntentConfigurationError, IntentDetector


class IntentDetectorNode(Node):
    """Classifies transcripts without producing workflow side effects."""

    def __init__(self) -> None:
        super().__init__("intent_detector_node")
        transcript_topic = str(
            self.declare_parameter("transcript_topic", "/voice/stt/transcript").value
        )
        result_topic = str(
            self.declare_parameter("result_topic", "/voice/intent/result").value
        )
        dialogue_state_topic = str(
            self.declare_parameter(
                "dialogue_state_topic", "/reception/dialogue/state"
            ).value
        )
        diagnostics_topic = str(
            self.declare_parameter(
                "diagnostics_topic", "/voice/intent/diagnostics"
            ).value
        )
        config_path = Path(
            str(
                self.declare_parameter(
                    "intent_config_path",
                    str(
                        Path(get_package_share_directory("evo_voice"))
                        / "config"
                        / "reception_intents.yaml"
                    ),
                ).value
            )
        ).expanduser()

        self.detector = IntentDetector.from_yaml(config_path)
        self.dialogue_state = "IDLE"
        self.result_publisher = self.create_publisher(
            IntentResult, result_topic, 10
        )
        diagnostics_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.diagnostics_publisher = self.create_publisher(
            String, diagnostics_topic, diagnostics_qos
        )
        self.create_subscription(
            Transcript, transcript_topic, self.on_transcript, 10
        )
        self.create_subscription(
            String,
            dialogue_state_topic,
            self.on_dialogue_state,
            diagnostics_qos,
        )
        self.get_logger().info(
            f"Intent detector ready: transcript={transcript_topic} "
            f"result={result_topic} dialogue_state={dialogue_state_topic}"
        )

    def on_dialogue_state(self, message: String) -> None:
        self.dialogue_state = message.data.strip().upper()
        self.publish_diagnostic(
            "intent_gate_changed",
            dialogue_state=self.dialogue_state,
            allowed_intents=sorted(self.allowed_intents()),
        )

    def allowed_intents(self) -> set[str]:
        if self.dialogue_state == "PRESENCE_ARMED":
            return {"greeting"}
        if self.dialogue_state == "WAITING_FOR_INTENT":
            return {
                "affirmative",
                "negative",
                "reservation",
                "repeat",
                "cancel",
                "unknown",
            }
        if self.dialogue_state == "WAITING_FOR_QR":
            return {"repeat", "cancel"}
        return set()

    def on_transcript(self, transcript: Transcript) -> None:
        allowed = self.allowed_intents()
        if not allowed:
            self.publish_diagnostic(
                "intent_rejected",
                reason="dialogue_disabled",
                dialogue_state=self.dialogue_state,
            )
            return
        detection_started = time.monotonic()
        match = self.detector.detect(transcript.text)
        if match.intent not in allowed:
            self.publish_diagnostic(
                "intent_rejected",
                reason="intent_not_allowed_in_state",
                dialogue_state=self.dialogue_state,
                detected_intent=match.intent,
            )
            return
        result = IntentResult()
        result.header = transcript.header
        result.intent = match.intent
        result.confidence = match.confidence
        result.source_transcript = match.source_transcript
        self.result_publisher.publish(result)
        self.get_logger().info(
            f"Published intent={result.intent} confidence={result.confidence:.2f} "
            f"intent_detection_sec={time.monotonic() - detection_started:.6f}"
        )
        self.publish_diagnostic(
            "intent_published",
            dialogue_state=self.dialogue_state,
            intent=result.intent,
            confidence=result.confidence,
        )

    def publish_diagnostic(self, event: str, **details: object) -> None:
        self.diagnostics_publisher.publish(
            String(
                data=json.dumps(
                    {"event": event, "timestamp": time.time(), **details},
                    ensure_ascii=False,
                )
            )
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node: IntentDetectorNode | None = None
    try:
        node = IntentDetectorNode()
        rclpy.spin(node)
    except IntentConfigurationError as exc:
        rclpy.logging.get_logger("intent_detector_node").fatal(str(exc))
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
