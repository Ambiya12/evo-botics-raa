from pathlib import Path

from evo_navigation.navigation_orchestrator import (
    MockNavigator,
    NavigationGates,
    NavigationOrchestrator,
    NavigationOutcome,
)
from evo_navigation.waypoints import WaypointRegistry
from evo_reception.dialogue_manager import (
    DialogueEvent,
    DialogueManager,
    DialogueState,
)
from evo_reception.qr_integration import (
    QrScanGate,
    QrValidationOutcome,
    ScanDecision,
)
from evo_vision.human_approach import (
    ApproachConfig,
    HumanApproachFilter,
    PersonObservation,
)
from evo_voice.intent_detector import IntentDetector


SOURCE_ROOT = Path(__file__).resolve().parents[2]
INTENT_CONFIG = SOURCE_ROOT / "evo_voice" / "config" / "reception_intents.yaml"
WAYPOINT_CONFIG = (
    SOURCE_ROOT / "evo_navigation" / "config" / "reception_waypoints.yaml"
)


def approach_filter() -> HumanApproachFilter:
    return HumanApproachFilter(
        ApproachConfig(
            min_confidence=0.7,
            min_distance_m=0.5,
            max_distance_m=2.5,
            zone_min_x=0.25,
            zone_max_x=0.75,
            zone_min_y=0.2,
            zone_max_y=0.9,
            debounce_frames=2,
            cooldown_sec=5.0,
            absence_reset_sec=1.0,
        )
    )


def person() -> PersonObservation:
    return PersonObservation("mock-person", 0.95, 1.5, 0.5, 0.5)


def ready_gates() -> NavigationGates:
    return NavigationGates(False, True, True)


def advance_to_qr_verification(manager: DialogueManager) -> None:
    detector = approach_filter()
    assert detector.process(person(), now=0.0) is None
    approach = detector.process(person(), now=0.1)
    assert approach is not None

    manager.handle_event(DialogueEvent.VISITOR_APPROACHED)
    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    intent = IntentDetector.from_yaml(INTENT_CONFIG).detect(
        "I have a booking"
    )
    manager.handle_intent(intent.intent)
    manager.handle_event(DialogueEvent.TTS_COMPLETED)

    gate = QrScanGate(duplicate_cooldown_sec=5.0)
    scan = gate.accept(
        '{"decoded_text":"mock-signed-payload"}',
        manager.state.value,
        manager.qr_prompt_completed,
    )
    assert scan.decision == ScanDecision.ACCEPTED
    manager.handle_event(DialogueEvent.QR_DETECTED)
    assert manager.state == DialogueState.VERIFYING_QR


def make_orchestrator(navigator: MockNavigator, gates=ready_gates):
    return NavigationOrchestrator(
        WaypointRegistry.from_yaml(WAYPOINT_CONFIG),
        navigator,
        gates,
        lambda state, message: None,
    )


def test_complete_mock_workflow_returns_to_reception() -> None:
    manager = DialogueManager()
    advance_to_qr_verification(manager)
    manager.handle_qr_result(QrValidationOutcome.VALID, "1")
    manager.handle_event(DialogueEvent.TTS_COMPLETED)

    navigator = MockNavigator(NavigationOutcome.ARRIVED)
    orchestrator = make_orchestrator(navigator)
    manager.handle_event(DialogueEvent.NAVIGATION_STARTED)
    outbound = orchestrator.execute("1", timeout_sec=10.0)
    assert outbound.outcome == NavigationOutcome.ARRIVED
    arrival = manager.handle_event(DialogueEvent.NAVIGATION_ARRIVED)
    assert arrival.speech == ("arrived",)

    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    assert manager.return_to_reception_ready
    returned = orchestrator.execute("reception", timeout_sec=10.0)
    manager.handle_return_result(returned.outcome == NavigationOutcome.ARRIVED)

    assert manager.state == DialogueState.IDLE
    assert [waypoint.destination_id for waypoint in navigator.calls] == [
        "1",
        "reception",
    ]


def test_invalid_qr_never_calls_navigation() -> None:
    manager = DialogueManager(max_retries=0)
    advance_to_qr_verification(manager)
    transition = manager.handle_qr_result(QrValidationOutcome.INVALID)
    navigator = MockNavigator()

    assert manager.state == DialogueState.ERROR
    assert "guidance_start" not in transition.speech
    assert navigator.calls == []


def test_navigation_gate_failure_enters_safe_error_state() -> None:
    manager = DialogueManager()
    advance_to_qr_verification(manager)
    manager.handle_qr_result(QrValidationOutcome.VALID, "1")
    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    navigator = MockNavigator()
    orchestrator = make_orchestrator(
        navigator,
        gates=lambda: NavigationGates(True, True, True),
    )

    result = orchestrator.execute("1", timeout_sec=10.0)
    transition = manager.handle_event(DialogueEvent.NAVIGATION_FAILED)

    assert result.outcome == NavigationOutcome.FAILED
    assert navigator.calls == []
    assert manager.state == DialogueState.ERROR
    assert transition.speech == ("navigation_failed",)


def test_return_failure_enters_safe_error_state() -> None:
    manager = DialogueManager()
    advance_to_qr_verification(manager)
    manager.handle_qr_result(QrValidationOutcome.VALID, "1")
    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    manager.handle_event(DialogueEvent.NAVIGATION_STARTED)
    manager.handle_event(DialogueEvent.NAVIGATION_ARRIVED)
    manager.handle_event(DialogueEvent.TTS_COMPLETED)

    navigator = MockNavigator(NavigationOutcome.FAILED)
    result = make_orchestrator(navigator).execute(
        "reception", timeout_sec=10.0
    )
    transition = manager.handle_return_result(
        result.outcome == NavigationOutcome.ARRIVED
    )

    assert manager.state == DialogueState.ERROR
    assert transition.speech == ("navigation_failed",)
