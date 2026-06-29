from __future__ import annotations

import time

from evo_reception_interfaces.action import GuideToDestination
from evo_reception_interfaces.msg import IntentResult
from evo_reception_interfaces.srv import ValidateQr
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from evo_reception.dialogue_manager import (
    DialogueEvent,
    DialogueManager,
    DialogueState,
    Transition,
)
from evo_reception.qr_integration import (
    QrScanGate,
    QrValidationOutcome,
    ScanDecision,
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
        qr_detections_topic = str(
            self.declare_parameter(
                "qr_detections_topic", "/vision/qr/detections"
            ).value
        )
        qr_validation_service = str(
            self.declare_parameter(
                "qr_validation_service", "/reception/qr/validate"
            ).value
        )
        duplicate_cooldown_sec = float(
            self.declare_parameter("duplicate_cooldown_sec", 5.0).value
        )
        guide_action_name = str(
            self.declare_parameter(
                "guide_action_name", "/reception/guide_to_destination"
            ).value
        )

        self.manager = DialogueManager(max_retries=max_retries)
        self.qr_scan_gate = QrScanGate(duplicate_cooldown_sec)
        self.qr_request_token = 0
        self.navigation_request_token = 0
        self.navigation_goal_handle = None
        self.navigation_send_future = None
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
        self.create_subscription(
            String, qr_detections_topic, self.on_qr_detection, 10
        )
        self.qr_validation_client = self.create_client(
            ValidateQr, qr_validation_service
        )
        self.navigation_client = ActionClient(
            self, GuideToDestination, guide_action_name
        )
        self.create_timer(timer_period_sec, self.on_timer)
        self.publish_state()
        self.get_logger().info(
            f"Dialogue manager ready: intent={intent_topic} event={event_topic} "
            f"state={state_topic}"
        )

    def on_intent(self, message: IntentResult) -> None:
        if message.intent.strip().lower() == "cancel":
            self.cancel_navigation()
        self.apply(self.manager.handle_intent(message.intent))

    def on_tts_status(self, message: String) -> None:
        status = message.data.strip().lower()
        if status == "speaking":
            self.deadline = None
        elif status == "completed":
            transition = self.manager.handle_event(DialogueEvent.TTS_COMPLETED)
            self.apply(transition)
            if (
                transition.accepted
                and self.manager.state == DialogueState.READY_TO_GUIDE
                and self.manager.guidance_announcement_completed
            ):
                self.request_navigation()
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
            DialogueEvent.QR_DETECTED,
            DialogueEvent.QR_VALID,
            DialogueEvent.QR_INVALID,
            DialogueEvent.QR_FAILED,
            DialogueEvent.NAVIGATION_STARTED,
            DialogueEvent.NAVIGATION_ARRIVED,
            DialogueEvent.NAVIGATION_FAILED,
        }:
            self.get_logger().warning(
                f"Ignoring internally owned dialogue event: {event.value}"
            )
            return
        self.apply(self.manager.handle_event(event))

    def on_qr_detection(self, message: String) -> None:
        acceptance = self.qr_scan_gate.accept(
            message.data,
            self.manager.state.value,
            self.manager.qr_prompt_completed,
        )
        if acceptance.decision in {
            ScanDecision.IGNORED_STATE,
            ScanDecision.DUPLICATE,
            ScanDecision.BUSY,
        }:
            return

        detected = self.manager.handle_event(DialogueEvent.QR_DETECTED)
        self.apply(detected)
        if not detected.accepted:
            return
        if acceptance.decision == ScanDecision.INVALID:
            self.apply(
                self.manager.handle_qr_result(QrValidationOutcome.INVALID)
            )
            return

        if not self.qr_validation_client.service_is_ready():
            self.qr_scan_gate.complete()
            self.apply(
                self.manager.handle_qr_result(QrValidationOutcome.UNAVAILABLE)
            )
            return

        request = ValidateQr.Request()
        request.qr_payload = acceptance.payload
        self.qr_request_token += 1
        request_token = self.qr_request_token
        request.request_id = str(request_token)
        future = self.qr_validation_client.call_async(request)
        future.add_done_callback(
            lambda completed: self.on_qr_validation_response(
                completed, request_token
            )
        )

    def on_qr_validation_response(self, future, request_token: int) -> None:
        if request_token != self.qr_request_token:
            return
        self.qr_scan_gate.complete()
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(f"QR validation service failed: {exc}")
            self.apply(
                self.manager.handle_qr_result(QrValidationOutcome.UNAVAILABLE)
            )
            return

        outcomes = {
            ValidateQr.Response.VALID: QrValidationOutcome.VALID,
            ValidateQr.Response.INVALID: QrValidationOutcome.INVALID,
            ValidateQr.Response.EXPIRED: QrValidationOutcome.EXPIRED,
            ValidateQr.Response.DUPLICATE: QrValidationOutcome.DUPLICATE,
            ValidateQr.Response.UNAVAILABLE: QrValidationOutcome.UNAVAILABLE,
        }
        outcome = outcomes.get(
            response.outcome, QrValidationOutcome.UNAVAILABLE
        )
        if response.request_id != str(request_token):
            self.get_logger().warning("QR validation response ID did not match request")
            self.apply(
                self.manager.handle_qr_result(QrValidationOutcome.UNAVAILABLE)
            )
            return
        self.apply(
            self.manager.handle_qr_result(
                outcome,
                destination_id=response.destination_id,
            )
        )

    def request_navigation(self) -> None:
        destination_id = self.manager.destination_id
        if not destination_id or not self.navigation_client.server_is_ready():
            self.apply(
                self.manager.handle_event(DialogueEvent.NAVIGATION_FAILED)
            )
            return

        self.navigation_request_token += 1
        request_token = self.navigation_request_token
        goal = GuideToDestination.Goal()
        goal.request_id = str(request_token)
        goal.destination_id = destination_id
        self.navigation_send_future = self.navigation_client.send_goal_async(
            goal,
            feedback_callback=self.on_navigation_feedback,
        )
        self.navigation_send_future.add_done_callback(
            lambda completed: self.on_navigation_goal_response(
                completed, request_token
            )
        )

    def on_navigation_goal_response(self, future, request_token: int) -> None:
        if request_token != self.navigation_request_token:
            self.cancel_late_navigation_goal(future)
            return
        try:
            goal_handle = future.result()
        except Exception as exc:
            self.get_logger().error(f"Navigation goal request failed: {exc}")
            self.apply(
                self.manager.handle_event(DialogueEvent.NAVIGATION_FAILED)
            )
            return
        if goal_handle is None or not goal_handle.accepted:
            self.apply(
                self.manager.handle_event(DialogueEvent.NAVIGATION_FAILED)
            )
            return

        self.navigation_goal_handle = goal_handle
        self.apply(
            self.manager.handle_event(DialogueEvent.NAVIGATION_STARTED)
        )
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda completed: self.on_navigation_result(
                completed, request_token
            )
        )

    def on_navigation_feedback(self, feedback_message) -> None:
        self.get_logger().debug(
            f"Navigation feedback: {feedback_message.feedback.state}"
        )

    def on_navigation_result(self, future, request_token: int) -> None:
        if request_token != self.navigation_request_token:
            return
        self.navigation_goal_handle = None
        try:
            wrapped_result = future.result()
            outcome = wrapped_result.result.outcome
        except Exception as exc:
            self.get_logger().error(f"Navigation result failed: {exc}")
            outcome = GuideToDestination.Result.FAILED

        if outcome == GuideToDestination.Result.ARRIVED:
            transition = self.manager.handle_event(
                DialogueEvent.NAVIGATION_ARRIVED
            )
        else:
            transition = self.manager.handle_event(
                DialogueEvent.NAVIGATION_FAILED
            )
        self.apply(transition)

    def cancel_navigation(self) -> None:
        self.navigation_request_token += 1
        if self.navigation_goal_handle is not None:
            self.navigation_goal_handle.cancel_goal_async()
            self.navigation_goal_handle = None
        elif (
            self.navigation_send_future is not None
            and not self.navigation_send_future.done()
        ):
            self.navigation_send_future.add_done_callback(
                self.cancel_late_navigation_goal
            )

    @staticmethod
    def cancel_late_navigation_goal(future) -> None:
        try:
            goal_handle = future.result()
            if goal_handle is not None and goal_handle.accepted:
                goal_handle.cancel_goal_async()
        except Exception:
            pass

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
        if (
            transition.previous == DialogueState.VERIFYING_QR
            and transition.current != DialogueState.VERIFYING_QR
        ):
            self.qr_request_token += 1
            self.qr_scan_gate.complete()
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
