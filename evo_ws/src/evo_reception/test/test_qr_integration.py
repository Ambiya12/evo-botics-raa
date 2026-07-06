from dataclasses import dataclass

import pytest

from evo_reception.dialogue_manager import (
    DialogueEvent,
    DialogueManager,
    DialogueState,
)
from evo_reception.qr_integration import (
    QrScanGate,
    QrValidationOutcome,
    ScanDecision,
    parse_destination_ids,
    extract_decoded_text,
    outcome_from_error_code,
    successful_validation_data,
    validate_backend_configuration,
)


def test_destination_allowlist_parses_room_ids() -> None:
    assert parse_destination_ids("1, 2,2") == frozenset({"1", "2"})


def test_destination_allowlist_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match="destination"):
        parse_destination_ids(" , ")


@dataclass(frozen=True)
class BridgeResult:
    outcome: QrValidationOutcome
    destination_id: str = ""


class RecordingReservationBridge:
    def __init__(self, result: BridgeResult) -> None:
        self.result = result
        self.calls: list[str] = []

    def verify(self, payload: str) -> BridgeResult:
        self.calls.append(payload)
        return self.result


def waiting_for_qr(max_retries: int = 0) -> DialogueManager:
    manager = DialogueManager(max_retries=max_retries)
    manager.handle_event(DialogueEvent.VISITOR_APPROACHED)
    manager.handle_intent("greeting")
    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    manager.handle_intent("reservation")
    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    assert manager.state == DialogueState.WAITING_FOR_QR
    return manager


def verify_scan(
    manager: DialogueManager,
    gate: QrScanGate,
    bridge: RecordingReservationBridge,
    raw_scan: str = '{"decoded_text":"signed-payload"}',
):
    acceptance = gate.accept(
        raw_scan,
        manager.state.value,
        manager.qr_prompt_completed,
    )
    assert acceptance.decision == ScanDecision.ACCEPTED
    manager.handle_event(DialogueEvent.QR_DETECTED)
    result = bridge.verify(acceptance.payload)
    gate.complete()
    return manager.handle_qr_result(result.outcome, result.destination_id)


def test_scanner_json_extracts_existing_decoded_text_contract() -> None:
    assert (
        extract_decoded_text('{"decoded_text":"signed-payload","has_uuid":true}')
        == "signed-payload"
    )


@pytest.mark.parametrize(
    ("error_code", "outcome"),
    [
        ("invalid_qr", QrValidationOutcome.INVALID),
        ("expired", QrValidationOutcome.EXPIRED),
        ("already_used", QrValidationOutcome.DUPLICATE),
        ("api_unreachable", QrValidationOutcome.UNAVAILABLE),
        ("timeout", QrValidationOutcome.UNAVAILABLE),
        ("malformed_response", QrValidationOutcome.UNAVAILABLE),
    ],
)
def test_bridge_error_codes_map_to_workflow_outcomes(
    error_code: str,
    outcome: QrValidationOutcome,
) -> None:
    assert outcome_from_error_code(error_code) == outcome


def test_real_backend_requires_explicit_absolute_url() -> None:
    with pytest.raises(ValueError, match="validation_url"):
        validate_backend_configuration("", 3.0, 5.0)
    with pytest.raises(ValueError, match="absolute HTTP"):
        validate_backend_configuration("localhost/api", 3.0, 5.0)


def test_backend_rejects_invalid_timeout_and_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="request_timeout_sec"):
        validate_backend_configuration("https://example.test/validate", 0.0, 5.0)
    with pytest.raises(ValueError, match="credentials"):
        validate_backend_configuration(
            "https://user:secret@example.test/validate",
            3.0,
            5.0,
        )


def test_only_approved_backend_success_shape_returns_data() -> None:
    valid_data = {"room_id": 42}

    assert successful_validation_data(
        {"status": "success", "data": valid_data}
    ) == valid_data
    assert successful_validation_data({"data": valid_data}) is None
    assert successful_validation_data(
        {"status": "error", "data": valid_data}
    ) is None
    assert successful_validation_data(["unexpected"]) is None


def test_scan_outside_waiting_for_qr_never_calls_bridge() -> None:
    manager = DialogueManager()
    gate = QrScanGate(duplicate_cooldown_sec=5.0)
    bridge = RecordingReservationBridge(
        BridgeResult(QrValidationOutcome.VALID, "room-42")
    )

    acceptance = gate.accept(
        '{"decoded_text":"signed-payload"}',
        manager.state.value,
        manager.qr_prompt_completed,
    )

    assert acceptance.decision == ScanDecision.IGNORED_STATE
    assert bridge.calls == []
    assert manager.state == DialogueState.IDLE


def test_malformed_scan_is_invalid_without_calling_bridge() -> None:
    manager = waiting_for_qr(max_retries=0)
    gate = QrScanGate(duplicate_cooldown_sec=5.0)
    bridge = RecordingReservationBridge(
        BridgeResult(QrValidationOutcome.VALID, "room-42")
    )

    acceptance = gate.accept(
        '{"missing_decoded_text":true}',
        manager.state.value,
        manager.qr_prompt_completed,
    )
    assert acceptance.decision == ScanDecision.INVALID
    manager.handle_event(DialogueEvent.QR_DETECTED)
    transition = manager.handle_qr_result(QrValidationOutcome.INVALID)

    assert bridge.calls == []
    assert manager.state == DialogueState.ERROR
    assert manager.destination_id is None
    assert "guidance_start" not in transition.speech


def test_valid_result_stores_stable_destination_id() -> None:
    manager = waiting_for_qr()
    gate = QrScanGate(duplicate_cooldown_sec=5.0)
    bridge = RecordingReservationBridge(
        BridgeResult(QrValidationOutcome.VALID, "42")
    )

    verify_scan(manager, gate, bridge)

    assert bridge.calls == ["signed-payload"]
    assert manager.state == DialogueState.READY_TO_GUIDE
    assert manager.destination_id == "42"


@pytest.mark.parametrize(
    "outcome",
    [
        QrValidationOutcome.INVALID,
        QrValidationOutcome.EXPIRED,
        QrValidationOutcome.UNAVAILABLE,
    ],
)
def test_rejected_results_never_store_destination_or_request_guidance(
    outcome: QrValidationOutcome,
) -> None:
    manager = waiting_for_qr(max_retries=0)
    gate = QrScanGate(duplicate_cooldown_sec=5.0)
    bridge = RecordingReservationBridge(BridgeResult(outcome))

    transition = verify_scan(manager, gate, bridge)

    assert manager.state == DialogueState.ERROR
    assert manager.destination_id is None
    assert "guidance_start" not in transition.speech


def test_duplicate_scan_is_ignored_without_second_bridge_call() -> None:
    now = [10.0]
    manager = waiting_for_qr(max_retries=1)
    gate = QrScanGate(duplicate_cooldown_sec=5.0, clock=lambda: now[0])
    bridge = RecordingReservationBridge(
        BridgeResult(QrValidationOutcome.INVALID)
    )
    verify_scan(manager, gate, bridge)
    manager.handle_event(DialogueEvent.TTS_COMPLETED)

    duplicate = gate.accept(
        '{"decoded_text":"signed-payload"}',
        manager.state.value,
        manager.qr_prompt_completed,
    )

    assert duplicate.decision == ScanDecision.DUPLICATE
    assert bridge.calls == ["signed-payload"]
    assert manager.state == DialogueState.WAITING_FOR_QR


def test_invalid_qr_allows_a_new_scan_after_retry_message_completes() -> None:
    manager = waiting_for_qr(max_retries=2)
    gate = QrScanGate(duplicate_cooldown_sec=5.0)
    bridge = RecordingReservationBridge(
        BridgeResult(QrValidationOutcome.INVALID)
    )

    transition = verify_scan(manager, gate, bridge)

    assert transition.speech == ("invalid_qr",)
    assert manager.state == DialogueState.WAITING_FOR_QR
    assert not manager.qr_prompt_completed
    assert gate.accept(
        '{"decoded_text":"second-signed-payload"}',
        manager.state.value,
        manager.qr_prompt_completed,
    ).decision == ScanDecision.IGNORED_STATE

    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    retry = gate.accept(
        '{"decoded_text":"second-signed-payload"}',
        manager.state.value,
        manager.qr_prompt_completed,
    )

    assert retry.decision == ScanDecision.ACCEPTED
    assert manager.destination_id is None


def test_bridge_duplicate_response_returns_to_qr_wait_without_guidance() -> None:
    manager = waiting_for_qr()
    gate = QrScanGate(duplicate_cooldown_sec=5.0)
    bridge = RecordingReservationBridge(
        BridgeResult(QrValidationOutcome.DUPLICATE)
    )

    transition = verify_scan(manager, gate, bridge)

    assert manager.state == DialogueState.WAITING_FOR_QR
    assert manager.destination_id is None
    assert transition.speech == ("duplicate_qr",)
    assert "guidance_start" not in transition.speech


def test_valid_response_without_destination_fails_closed() -> None:
    manager = waiting_for_qr()
    gate = QrScanGate(duplicate_cooldown_sec=5.0)
    bridge = RecordingReservationBridge(
        BridgeResult(QrValidationOutcome.VALID, "")
    )

    transition = verify_scan(manager, gate, bridge)

    assert manager.state == DialogueState.ERROR
    assert manager.destination_id is None
    assert transition.speech == ("validation_unavailable",)
