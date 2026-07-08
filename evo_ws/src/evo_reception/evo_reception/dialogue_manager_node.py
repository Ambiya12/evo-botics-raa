from __future__ import annotations

import time

from evo_reception_interfaces.action import GuideToDestination
from evo_reception_interfaces.msg import (
    IntentResult,
    PersonApproach,
    WorkflowStatus,
)
from evo_reception_interfaces.srv import ValidateQr
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String

from evo_reception._deadline_controller import DeadlineController
from evo_reception._navigation_driver import NavigationDriver
from evo_reception.dialogue_manager import (
    DeferredGreeting,
    DialogueEvent,
    DialogueManager,
    DialogueState,
    TtsStatusTracker,
    Transition,
)
from evo_reception.qr_integration import (
    QrScanGate,
    QrValidationOutcome,
    ScanDecision,
    _ensure_outcome_mapping,
    parse_destination_ids,
)


class DialogueManagerNode(Node):
    """ROS adapter for the hardware-free reception state machine."""

    def __init__(self) -> None:
        super().__init__("dialogue_manager_node")
        max_retries = int(self.declare_parameter("max_retries", 2).value)
        intent_timeout_sec = float(self.declare_parameter("intent_timeout_sec", 45.0).value)
        qr_inactivity_timeout_sec = float(self.declare_parameter("qr_inactivity_timeout_sec", 20.0).value)
        presence_greeting_fallback_sec = float(
            self.declare_parameter("presence_greeting_fallback_sec", 5.0).value
        )
        self.automatic_return_enabled = bool(
            self.declare_parameter("automatic_return_enabled", True).value
        )
        timer_period_sec = float(self.declare_parameter("timer_period_sec", 0.2).value)
        if max_retries < 0:
            raise ValueError("'max_retries' must be non-negative")
        if intent_timeout_sec <= 0.0:
            raise ValueError("'intent_timeout_sec' must be greater than zero")
        if qr_inactivity_timeout_sec <= 0.0:
            raise ValueError("'qr_inactivity_timeout_sec' must be greater than zero")
        if presence_greeting_fallback_sec < 0.0:
            raise ValueError("'presence_greeting_fallback_sec' must be non-negative")
        if timer_period_sec <= 0.0:
            raise ValueError("'timer_period_sec' must be greater than zero")

        intent_topic = str(self.declare_parameter("intent_topic", "/voice/intent/result").value)
        tts_request_topic = str(self.declare_parameter("tts_request_topic", "/voice/tts/request").value)
        tts_status_topic = str(self.declare_parameter("tts_status_topic", "/voice/tts/status").value)
        stt_status_topic = str(self.declare_parameter("stt_status_topic", "/voice/stt/status").value)
        event_topic = str(self.declare_parameter("event_topic", "/reception/dialogue/event").value)
        state_topic = str(self.declare_parameter("state_topic", "/reception/dialogue/state").value)
        qr_detections_topic = str(self.declare_parameter("qr_detections_topic", "/vision/qr/detections").value)
        qr_validation_service = str(self.declare_parameter("qr_validation_service", "/reception/qr/validate").value)
        duplicate_cooldown_sec = float(self.declare_parameter("duplicate_cooldown_sec", 5.0).value)
        guide_action_name = str(
            self.declare_parameter("guide_action_name", "/reception/guide_to_destination").value
        )
        approach_topic = str(self.declare_parameter("approach_topic", "/vision/people/approach").value)
        presence_topic = str(self.declare_parameter("presence_topic", "/vision/people/presence").value)
        workflow_status_topic = str(
            self.declare_parameter("workflow_status_topic", "/reception/workflow/status").value
        )
        self.allowed_destination_ids = parse_destination_ids(
            str(self.declare_parameter("allowed_destination_ids_csv", "1,2").value)
        )

        self.manager = DialogueManager(max_retries=max_retries)
        self.deadline = DeadlineController(
            intent_timeout_sec, qr_inactivity_timeout_sec, presence_greeting_fallback_sec
        )
        self.qr_scan_gate = QrScanGate(duplicate_cooldown_sec)
        self.qr_request_token = 0
        self.session_counter = 0
        self.session_id = ""
        self.tts_ready = False
        self.visitor_present = False
        self.deferred_greeting = DeferredGreeting()
        self.tts_status_tracker = TtsStatusTracker()

        self.navigation = NavigationDriver(
            self, guide_action_name,
            on_result=self._on_nav_result,
            on_failure=self._on_nav_failure,
        )

        self.tts_request_publisher = self.create_publisher(String, tts_request_topic, 10)
        state_qos = QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.state_publisher = self.create_publisher(String, state_topic, state_qos)
        self.workflow_status_publisher = self.create_publisher(
            WorkflowStatus, workflow_status_topic, state_qos
        )
        self.create_subscription(IntentResult, intent_topic, self.on_intent, 10)
        tts_status_qos = QoSProfile(
            depth=10, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(String, tts_status_topic, self.on_tts_status, tts_status_qos)
        self.create_subscription(String, stt_status_topic, self.on_stt_status, tts_status_qos)
        self.create_subscription(String, event_topic, self.on_external_event, 10)
        self.create_subscription(PersonApproach, approach_topic, self.on_person_approach, 10)
        presence_qos = QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(Bool, presence_topic, self.on_person_presence, presence_qos)
        self.create_subscription(String, qr_detections_topic, self.on_qr_detection, 10)
        self.qr_validation_client = self.create_client(ValidateQr, qr_validation_service)
        self.create_timer(timer_period_sec, self.on_timer)
        self.publish_state()
        self.publish_workflow_status("idle", "Waiting for a visitor.")
        self.get_logger().info(
            f"Dialogue manager ready: intent={intent_topic} event={event_topic} "
            f"state={state_topic}"
        )

    def on_intent(self, message: IntentResult) -> None:
        self.get_logger().info(
            f"Received intent={message.intent} confidence={message.confidence:.2f} "
            f"state={self.manager.state.value}"
        )
        if message.intent.strip().lower() == "cancel":
            self.navigation.cancel()
        self.apply(self.manager.handle_intent(message.intent))

    def on_person_approach(self, message: PersonApproach) -> None:
        self.visitor_present = True
        self.apply(self.manager.handle_event(DialogueEvent.VISITOR_APPROACHED))

    def on_person_presence(self, message: Bool) -> None:
        self.visitor_present = bool(message.data)
        self.get_logger().info(
            f"Received presence={str(message.data).lower()} "
            f"state={self.manager.state.value}"
        )
        if not message.data:
            if self.deferred_greeting.due:
                self.get_logger().info("Cleared deferred greeting after confirmed visitor absence")
            self.deferred_greeting.clear()
        event = (
            DialogueEvent.VISITOR_APPROACHED if message.data
            else DialogueEvent.VISITOR_LEFT
        )
        self.apply(self.manager.handle_event(event))

    def on_tts_status(self, message: String) -> None:
        status = message.data.strip().lower()
        if not self.tts_ready:
            self.tts_ready = True
            self.get_logger().info(f"TTS ready with status={status}")
            if self.visitor_present and self.manager.state == DialogueState.IDLE:
                self.apply(self.manager.handle_event(DialogueEvent.VISITOR_APPROACHED))
            self.release_deferred_greeting()
        if status == "speaking":
            self.deadline.clear_speech_deadline()
        event = self.tts_status_tracker.update(status)
        if event == DialogueEvent.TTS_COMPLETED:
            self._on_tts_completed()
        elif event == DialogueEvent.TTS_FAILED:
            self.apply(self.manager.handle_event(DialogueEvent.TTS_FAILED))

    def on_stt_status(self, message: String) -> None:
        status = message.data.strip().lower()
        if status == "transcribing":
            if self.deadline.on_stt_transcribing(self.manager.state):
                self.get_logger().info("Paused intent deadline while STT is transcribing")
        elif status == "idle" and self.deadline.on_stt_idle(self.manager.state):
            self.get_logger().info("Resumed intent deadline after STT transcription")

    def _on_tts_completed(self) -> None:
        transition = self.manager.handle_event(DialogueEvent.TTS_COMPLETED)
        self.apply(transition)
        if not transition.accepted:
            return
        if (
            self.manager.state == DialogueState.READY_TO_GUIDE
            and self.manager.guidance_announcement_completed
        ):
            self.navigation.request(self.manager.destination_id or "")
        elif (
            self.manager.state == DialogueState.ARRIVED
            and self.manager.return_to_reception_ready
        ):
            if self.automatic_return_enabled:
                self.navigation.request("reception", returning=True)
            else:
                self.get_logger().warning(
                    "Automatic Reception return is disabled; remaining at "
                    "the destination for controlled-site B4 acceptance"
                )

    def on_external_event(self, message: String) -> None:
        try:
            event = DialogueEvent(message.data.strip().lower())
        except ValueError:
            self.get_logger().warning(f"Ignoring unknown dialogue event: {message.data}")
            return
        if event in _INTERNAL_EVENTS:
            self.get_logger().warning(f"Ignoring internally owned dialogue event: {event.value}")
            return
        self.apply(self.manager.handle_event(event))

    def on_qr_detection(self, message: String) -> None:
        acceptance = self.qr_scan_gate.accept(
            message.data, self.manager.state.value, self.manager.qr_prompt_completed,
        )
        if acceptance.decision in {ScanDecision.IGNORED_STATE, ScanDecision.DUPLICATE, ScanDecision.BUSY}:
            return

        detected = self.manager.handle_event(DialogueEvent.QR_DETECTED)
        self.apply(detected)
        if not detected.accepted:
            return
        if acceptance.decision == ScanDecision.INVALID:
            self.apply(self.manager.handle_qr_result(QrValidationOutcome.INVALID))
            return

        if not self.qr_validation_client.service_is_ready():
            self.qr_scan_gate.complete()
            self.apply(self.manager.handle_qr_result(QrValidationOutcome.UNAVAILABLE))
            return

        request = ValidateQr.Request()
        request.qr_payload = acceptance.payload
        self.qr_request_token += 1
        request_token = self.qr_request_token
        request.request_id = str(request_token)
        future = self.qr_validation_client.call_async(request)
        future.add_done_callback(
            lambda completed: self._on_qr_validation(completed, request_token)
        )

    def _on_qr_validation(self, future, request_token: int) -> None:
        if request_token != self.qr_request_token:
            return
        self.qr_scan_gate.complete()
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(f"QR validation service failed: {exc}")
            self.apply(self.manager.handle_qr_result(QrValidationOutcome.UNAVAILABLE))
            return

        outcomes = _ensure_outcome_mapping()
        outcome = outcomes.get(response.outcome, QrValidationOutcome.UNAVAILABLE)
        if response.request_id != str(request_token):
            self.get_logger().warning("QR validation response ID did not match request")
            self.apply(self.manager.handle_qr_result(QrValidationOutcome.UNAVAILABLE))
            return
        destination_id = response.destination_id.strip()
        if outcome == QrValidationOutcome.VALID and destination_id not in self.allowed_destination_ids:
            self.get_logger().error("Validated QR returned an unsupported destination ID")
            self.apply(self.manager.handle_qr_result(QrValidationOutcome.UNAVAILABLE))
            return
        self.apply(self.manager.handle_qr_result(outcome, destination_id=destination_id))

    def _on_nav_result(self, _request_token: int, arrived: bool) -> None:
        if self.navigation.returning:
            transition = self.manager.handle_return_result(arrived)
        elif arrived:
            transition = self.manager.handle_event(DialogueEvent.NAVIGATION_ARRIVED)
        else:
            transition = self.manager.handle_event(DialogueEvent.NAVIGATION_FAILED)
        self.apply(transition)

    def _on_nav_failure(self, returning: bool) -> None:
        transition = (
            self.manager.handle_return_result(False)
            if returning
            else self.manager.handle_event(DialogueEvent.NAVIGATION_FAILED)
        )
        self.apply(transition)

    def on_timer(self) -> None:
        if not self.deadline.is_expired():
            return
        event = self.deadline.pop_expired()
        if event is None:
            return
        self.get_logger().info(
            f"Dialogue deadline expired: event={event.value} "
            f"state={self.manager.state.value} "
            f"tts_ready={str(self.tts_ready).lower()}"
        )
        if (
            event == DialogueEvent.PRESENCE_GREETING_TIMEOUT
            and not self.tts_ready
            and self.visitor_present
            and self.manager.state == DialogueState.PRESENCE_ARMED
        ):
            self.deferred_greeting.defer()
            self.get_logger().info("Greeting is due and will be emitted when TTS becomes ready")
            return
        self.apply(self.manager.handle_event(event))

    def release_deferred_greeting(self) -> None:
        if (
            self.manager.state == DialogueState.PRESENCE_ARMED
            and self.deferred_greeting.release(
                tts_ready=self.tts_ready, visitor_present=self.visitor_present,
            )
        ):
            self.get_logger().info("TTS became ready; emitting the deferred greeting")
            self.apply(self.manager.handle_event(DialogueEvent.PRESENCE_GREETING_TIMEOUT))

    def apply(self, transition: Transition) -> None:
        if not transition.accepted:
            self.get_logger().debug(f"Ignored invalid transition from {transition.current.value}")
            return
        if (
            transition.previous == DialogueState.VERIFYING_QR
            and transition.current != DialogueState.VERIFYING_QR
        ):
            self.qr_request_token += 1
            self.qr_scan_gate.complete()
        if transition.changed:
            if transition.current != DialogueState.PRESENCE_ARMED:
                self.deferred_greeting.clear()
            if (
                transition.previous == DialogueState.IDLE
                and transition.current == DialogueState.PRESENCE_ARMED
            ):
                self.session_counter += 1
                self.session_id = f"session-{self.session_counter}"
            self.publish_state()
            self.get_logger().info(
                f"Dialogue transition: {transition.previous.value} -> {transition.current.value}"
            )
        for phrase in transition.speech:
            self.tts_status_tracker.mark_requested()
            self.tts_request_publisher.publish(String(data=f"phrase:{phrase}"))
        self.deadline.refresh(self.manager.state, bool(transition.speech))
        outcome = transition.current.value.lower()
        if transition.current == DialogueState.ERROR:
            outcome = "failed"
        elif (
            transition.previous == DialogueState.ARRIVED
            and transition.current == DialogueState.IDLE
        ):
            outcome = "completed"
        self.publish_workflow_status(outcome, ",".join(transition.speech))

    def publish_state(self) -> None:
        self.state_publisher.publish(String(data=self.manager.state.value))

    def publish_workflow_status(
        self, outcome: str, detail: str, destination_id: str | None = None,
    ) -> None:
        status = WorkflowStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.session_id = self.session_id
        status.state = self.manager.state.value
        status.outcome = outcome
        status.detail = detail
        status.destination_id = (
            destination_id if destination_id is not None
            else (self.manager.destination_id or "")
        )
        self.workflow_status_publisher.publish(status)


_INTERNAL_EVENTS = frozenset({
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
    DialogueEvent.VISITOR_LEFT,
    DialogueEvent.PRESENCE_GREETING_TIMEOUT,
})


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
