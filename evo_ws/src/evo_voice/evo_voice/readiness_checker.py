from __future__ import annotations

import json
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


class VoiceReadinessChecker(Node):
    """Wait for both durable real-backend readiness contracts."""

    def __init__(self) -> None:
        super().__init__("voice_readiness_checker")
        self.timeout_sec = float(
            self.declare_parameter("timeout_sec", 45.0).value
        )
        if self.timeout_sec <= 0.0:
            raise ValueError("'timeout_sec' must be greater than zero")
        self.started_at = time.monotonic()
        self.piper_ready = False
        self.stt_ready = False

        diagnostics_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        status_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            String,
            "/voice/tts/diagnostics",
            self.on_tts_diagnostics,
            diagnostics_qos,
        )
        self.create_subscription(
            String,
            "/voice/stt/status",
            self.on_stt_status,
            status_qos,
        )

    @property
    def ready(self) -> bool:
        return self.piper_ready and self.stt_ready

    def on_tts_diagnostics(self, message: String) -> None:
        try:
            payload = json.loads(message.data)
        except (TypeError, ValueError):
            return
        if (
            isinstance(payload, dict)
            and payload.get("event") == "ready"
            and payload.get("backend") == "piper"
        ):
            self.piper_ready = True

    def on_stt_status(self, message: String) -> None:
        if message.data.strip().lower() == "idle":
            self.stt_ready = True

    def wait(self) -> bool:
        deadline = self.started_at + self.timeout_sec
        while rclpy.ok() and not self.ready and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
        return self.ready


def main(args=None) -> None:
    rclpy.init(args=args)
    node: VoiceReadinessChecker | None = None
    exit_code = 1
    try:
        node = VoiceReadinessChecker()
        if node.wait():
            node.get_logger().info(
                "Voice readiness contracts verified after "
                f"{time.monotonic() - node.started_at:.3f}s"
            )
            exit_code = 0
        else:
            missing = []
            if not node.piper_ready:
                missing.append("Piper")
            if not node.stt_ready:
                missing.append("Faster-Whisper/microphone")
            node.get_logger().error(
                "Timed out waiting for: " + ", ".join(missing)
            )
    except ValueError as exc:
        rclpy.logging.get_logger("voice_readiness_checker").fatal(str(exc))
        exit_code = 2
    except ExternalShutdownException:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
