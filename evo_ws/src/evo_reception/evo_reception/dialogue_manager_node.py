from __future__ import annotations

import time

from evo_reception_interfaces.msg import IntentResult
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from evo_reception.dialogue_manager import (
    DialogueEvent,
    DialogueManager,
    DialogueState,
    Transition,
)


class DialogueManagerNode(Node):
    """ROS adapter for the hardware-free reception state machine."""

    def __init__(self) -> None:
        super().__init__("dialogue_manager_node")
        max_retries = int(self.declare_parameter("max_retries", 2).value)
        self.inactivity_timeout_sec = float(
            self.declare_parameter("inactivity_timeout_sec", 20.0).value
        )
        timer_period_sec = float(
            self.declare_parameter("timer_period_sec", 0.2).value
        )
        if max_retries < 0:
            raise ValueError("'max_retries' must be non-negative")
        if self.inactivity_timeout_sec <= 0.0:
            raise ValueError("'inactivity_timeout_sec' must be greater than zero")
        if timer_period_sec <= 0.0:
            raise ValueError("'timer_period_sec' must be greater than zero")

        intent_topic = str(
            self.declare_parameter("intent_topic", "/voice/intent/result").value
        )
        tts_request_topic = str(
            self.declare_parameter("tts_request_topic", "/voice/tts/request").value
        )
        tts_status_topic = str(
            self.declare_parameter("tts_status_topic", "/voice/tts/status").value
        )
        event_topic = str(
            self.declare_parameter(
                "event_topic", "/reception/dialogue/event"
            ).value
        )
        state_topic = str(
            self.declare_parameter(
                "state_topic", "/reception/dialogue/state"
            ).value
        )

        self.manager = DialogueManager(max_retries=max_retries)
        self.deadline: float | None = None
        self.tts_request_publisher = self.create_publisher(
            String, tts_request_topic, 10
        )
        state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.state_publisher = self.create_publisher(String, state_topic, state_qos)
        self.create_subscription(
            IntentResult, intent_topic, self.on_intent, 10
        )
        self.create_subscription(
            String, tts_status_topic, self.on_tts_status, state_qos
        )
        self.create_subscription(String, event_topic, self.on_external_event, 10)
        self.create_timer(timer_period_sec, self.on_timer)
        self.publish_state()
        self.get_logger().info(
            f"Dialogue manager ready: intent={intent_topic} event={event_topic} "
            f"state={state_topic}"
        )

    def on_intent(self, message: IntentResult) -> None:
        self.apply(self.manager.handle_intent(message.intent))

    def on_tts_status(self, message: String) -> None:
        status = message.data.strip().lower()
        if status == "speaking":
            self.deadline = None
        elif status == "completed":
            self.apply(self.manager.handle_event(DialogueEvent.TTS_COMPLETED))
        elif status == "failed":
            self.apply(self.manager.handle_event(DialogueEvent.TTS_FAILED))

    def on_external_event(self, message: String) -> None:
        try:
            event = DialogueEvent(message.data.strip().lower())
        except ValueError:
            self.get_logger().warning(
                f"Ignoring unknown dialogue event: {message.data}"
            )
            return
        if event in {
            DialogueEvent.TTS_COMPLETED,
            DialogueEvent.TTS_FAILED,
            DialogueEvent.INACTIVITY_TIMEOUT,
        }:
            self.get_logger().warning(
                f"Ignoring internally owned dialogue event: {event.value}"
            )
            return
        self.apply(self.manager.handle_event(event))

    def on_timer(self) -> None:
        if self.deadline is None or time.monotonic() < self.deadline:
            return
        self.deadline = None
        self.apply(
            self.manager.handle_event(DialogueEvent.INACTIVITY_TIMEOUT)
        )

    def apply(self, transition: Transition) -> None:
        if not transition.accepted:
            self.get_logger().debug(
                f"Ignored invalid transition from {transition.current.value}"
            )
            return
        if transition.changed:
            self.publish_state()
        for phrase in transition.speech:
            self.tts_request_publisher.publish(String(data=f"phrase:{phrase}"))
        self.refresh_deadline(transition)

    def refresh_deadline(self, transition: Transition) -> None:
        if transition.speech:
            self.deadline = None
        elif self.manager.state in {
            DialogueState.WAITING_FOR_INTENT,
            DialogueState.WAITING_FOR_QR,
        }:
            self.deadline = time.monotonic() + self.inactivity_timeout_sec
        else:
            self.deadline = None

    def publish_state(self) -> None:
        self.state_publisher.publish(String(data=self.manager.state.value))


def main(args=None) -> None:
    rclpy.init(args=args)
    node: DialogueManagerNode | None = None
    try:
        node = DialogueManagerNode()
        rclpy.spin(node)
    except ValueError as exc:
        rclpy.logging.get_logger("dialogue_manager_node").fatal(str(exc))
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
