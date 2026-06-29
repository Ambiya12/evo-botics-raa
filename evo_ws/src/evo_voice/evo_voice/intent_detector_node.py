from __future__ import annotations

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from evo_reception_interfaces.msg import IntentResult, Transcript
import rclpy
from rclpy.node import Node

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
        self.result_publisher = self.create_publisher(
            IntentResult, result_topic, 10
        )
        self.create_subscription(
            Transcript, transcript_topic, self.on_transcript, 10
        )
        self.get_logger().info(
            f"Intent detector ready: transcript={transcript_topic} "
            f"result={result_topic}"
        )

    def on_transcript(self, transcript: Transcript) -> None:
        match = self.detector.detect(transcript.text)
        result = IntentResult()
        result.header = transcript.header
        result.intent = match.intent
        result.confidence = match.confidence
        result.source_transcript = match.source_transcript
        self.result_publisher.publish(result)


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
