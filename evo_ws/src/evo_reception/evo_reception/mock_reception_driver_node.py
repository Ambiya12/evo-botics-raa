from __future__ import annotations

import json
import time

from evo_reception_interfaces.msg import PersonDetection, Transcript
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


class MockReceptionDriverNode(Node):
    """Single-run laptop driver for person, STT, and QR input boundaries."""

    def __init__(self) -> None:
        super().__init__("mock_reception_driver_node")
        self.transcript_text = str(
            self.declare_parameter(
                "transcript_text", "I have a reservation"
            ).value
        )
        self.qr_payload = str(
            self.declare_parameter("qr_payload", "mock-signed-payload").value
        )
        self.detection_frames = int(
            self.declare_parameter("detection_frames", 3).value
        )
        self.stage_delay_sec = float(
            self.declare_parameter("stage_delay_sec", 0.5).value
        )
        if self.detection_frames < 1:
            raise ValueError("'detection_frames' must be at least 1")
        if self.stage_delay_sec < 0.0:
            raise ValueError("'stage_delay_sec' must be non-negative")

        state_topic = str(
            self.declare_parameter(
                "state_topic", "/reception/dialogue/state"
            ).value
        )
        detection_topic = str(
            self.declare_parameter(
                "detection_topic", "/vision/people/detections"
            ).value
        )
        transcript_topic = str(
            self.declare_parameter(
                "transcript_topic", "/voice/stt/transcript"
            ).value
        )
        qr_topic = str(
            self.declare_parameter(
                "qr_topic", "/vision/qr/detections"
            ).value
        )

        self.detection_publisher = self.create_publisher(
            PersonDetection, detection_topic, 10
        )
        self.transcript_publisher = self.create_publisher(
            Transcript, transcript_topic, 10
        )
        self.qr_publisher = self.create_publisher(String, qr_topic, 10)
        state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(String, state_topic, self.on_state, state_qos)
        self.create_timer(0.1, self.on_timer)

        self.state = "UNKNOWN"
        self.state_entered_at = time.monotonic()
        self.started = False
        self.completed = False
        self.frames_published = 0
        self.transcript_published = False
        self.qr_published = False
        self.get_logger().info("End-to-end mock reception driver ready")

    def on_state(self, message: String) -> None:
        new_state = message.data.strip().upper()
        previous = self.state
        if new_state != self.state:
            self.state = new_state
            self.state_entered_at = time.monotonic()
        if not self.started and previous == "IDLE" and new_state != "IDLE":
            self.started = True
        if self.started and previous != "IDLE" and new_state == "IDLE":
            self.completed = True

    def on_timer(self) -> None:
        if self.completed:
            return
        elapsed = time.monotonic() - self.state_entered_at

        if self.state == "IDLE" and not self.started:
            self.publish_detection()
            self.frames_published = (
                self.frames_published + 1
            ) % self.detection_frames
            return

        if elapsed < self.stage_delay_sec:
            return
        if self.state == "WAITING_FOR_INTENT" and not self.transcript_published:
            transcript = Transcript()
            transcript.header.stamp = self.get_clock().now().to_msg()
            transcript.text = self.transcript_text
            transcript.language = "en"
            transcript.confidence = 1.0
            self.transcript_publisher.publish(transcript)
            self.transcript_published = True
        elif self.state == "WAITING_FOR_QR" and not self.qr_published:
            event = {
                "decoded_text": self.qr_payload,
                "decoder_backend": "mock",
                "is_json": False,
            }
            self.qr_publisher.publish(
                String(data=json.dumps(event, separators=(",", ":")))
            )
            self.qr_published = True

    def publish_detection(self) -> None:
        detection = PersonDetection()
        detection.header.stamp = self.get_clock().now().to_msg()
        detection.tracking_id = "mock-person"
        detection.confidence = 0.95
        detection.distance_m = 1.5
        detection.normalized_x = 0.5
        detection.normalized_y = 0.5
        self.detection_publisher.publish(detection)


def main(args=None) -> None:
    rclpy.init(args=args)
    node: MockReceptionDriverNode | None = None
    try:
        node = MockReceptionDriverNode()
        rclpy.spin(node)
    except ValueError as exc:
        rclpy.logging.get_logger("mock_reception_driver_node").fatal(str(exc))
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
