import pytest

from evo_reception.dialogue_manager import (
    DialogueEvent,
    DialogueManager,
    DialogueState,
)


def start_session(manager: DialogueManager) -> None:
    manager.handle_event(DialogueEvent.VISITOR_APPROACHED)
    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    assert manager.state == DialogueState.WAITING_FOR_INTENT


def test_happy_path_reaches_arrival_and_resets() -> None:
    manager = DialogueManager(max_retries=2)

    assert manager.state == DialogueState.IDLE
    assert manager.handle_event(
        DialogueEvent.VISITOR_APPROACHED
    ).speech == ("greeting",)
    assert manager.state == DialogueState.GREETING

    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    assert manager.state == DialogueState.WAITING_FOR_INTENT

    assert manager.handle_intent("reservation").speech == ("request_qr",)
    assert manager.state == DialogueState.WAITING_FOR_QR
    manager.handle_event(DialogueEvent.TTS_COMPLETED)

    manager.handle_event(DialogueEvent.QR_DETECTED)
    assert manager.state == DialogueState.VERIFYING_QR
    assert manager.handle_event(DialogueEvent.QR_VALID).speech == (
        "guidance_start",
    )
    assert manager.state == DialogueState.READY_TO_GUIDE

    assert not manager.handle_event(DialogueEvent.NAVIGATION_STARTED).accepted
    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    manager.handle_event(DialogueEvent.NAVIGATION_STARTED)
    assert manager.state == DialogueState.NAVIGATING

    assert manager.handle_event(DialogueEvent.NAVIGATION_ARRIVED).speech == (
        "arrived",
    )
    assert manager.state == DialogueState.ARRIVED
    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    assert manager.state == DialogueState.IDLE


@pytest.mark.parametrize(
    ("state", "event"),
    [
        (DialogueState.IDLE, DialogueEvent.QR_DETECTED),
        (DialogueState.IDLE, DialogueEvent.NAVIGATION_STARTED),
        (DialogueState.GREETING, DialogueEvent.QR_VALID),
        (DialogueState.WAITING_FOR_INTENT, DialogueEvent.NAVIGATION_ARRIVED),
    ],
)
def test_invalid_transitions_are_ignored(
    state: DialogueState,
    event: DialogueEvent,
) -> None:
    manager = DialogueManager()
    manager.state = state

    transition = manager.handle_event(event)

    assert not transition.accepted
    assert manager.state == state


def test_unknown_intent_repeats_then_enters_error() -> None:
    manager = DialogueManager(max_retries=2)
    start_session(manager)

    first = manager.handle_intent("unknown")
    second = manager.handle_intent("unknown")
    exhausted = manager.handle_intent("unknown")

    assert first.speech == ("clarify_intent",)
    assert second.speech == ("clarify_intent",)
    assert exhausted.speech == ("clarification_failed",)
    assert manager.retry_count == 2
    assert manager.state == DialogueState.ERROR


def test_cancellation_resets_session() -> None:
    manager = DialogueManager()
    start_session(manager)
    manager.handle_intent("unknown")

    transition = manager.handle_intent("cancel")

    assert transition.speech == ("cancelled",)
    assert manager.state == DialogueState.IDLE
    assert manager.retry_count == 0


def test_inactivity_timeout_enters_error_then_resets_safely() -> None:
    manager = DialogueManager()
    start_session(manager)

    transition = manager.handle_event(DialogueEvent.INACTIVITY_TIMEOUT)

    assert transition.speech == ("session_timeout",)
    assert manager.state == DialogueState.ERROR

    manager.handle_event(DialogueEvent.TTS_COMPLETED)
    assert manager.state == DialogueState.IDLE


def test_qr_cannot_be_accepted_before_prompt_completes() -> None:
    manager = DialogueManager()
    start_session(manager)
    manager.handle_intent("check_in")

    transition = manager.handle_event(DialogueEvent.QR_DETECTED)

    assert not transition.accepted
    assert manager.state == DialogueState.WAITING_FOR_QR
