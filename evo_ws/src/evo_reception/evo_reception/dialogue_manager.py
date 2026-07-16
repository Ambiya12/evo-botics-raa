from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from evo_reception.qr_integration import QrValidationOutcome


class DialogueState(str, Enum):
    IDLE = "IDLE"
    PRESENCE_ARMED = "PRESENCE_ARMED"
    GREETING = "GREETING"
    WAITING_FOR_INTENT = "WAITING_FOR_INTENT"
    WAITING_FOR_QR = "WAITING_FOR_QR"
    VERIFYING_QR = "VERIFYING_QR"
    READY_TO_GUIDE = "READY_TO_GUIDE"
    NAVIGATING = "NAVIGATING"
    ARRIVED = "ARRIVED"
    ERROR = "ERROR"


class DialogueEvent(str, Enum):
    VISITOR_APPROACHED = "visitor_approached"
    VISITOR_LEFT = "visitor_left"
    PRESENCE_GREETING_TIMEOUT = "presence_greeting_timeout"
    TTS_COMPLETED = "tts_completed"
    TTS_FAILED = "tts_failed"
    QR_DETECTED = "qr_detected"
    QR_VALID = "qr_valid"
    QR_INVALID = "qr_invalid"
    QR_FAILED = "qr_failed"
    NAVIGATION_STARTED = "navigation_started"
    NAVIGATION_ARRIVED = "navigation_arrived"
    NAVIGATION_FAILED = "navigation_failed"
    INACTIVITY_TIMEOUT = "inactivity_timeout"


class TtsStatusTracker:
    """Correlates TTS statuses with one dialogue-owned speech request."""

    def __init__(self) -> None:
        self.pending = False
        self.speaking_seen = False
        self._sequence = 0

    def mark_requested(self) -> None:
        self.pending = True
        self.speaking_seen = False
        self._sequence += 1

    def update(self, status: str) -> DialogueEvent | None:
        normalized = status.strip().lower()
        if not self.pending:
            return None
        if normalized == "speaking":
            self.speaking_seen = True
            return None
        if normalized == "completed":
            self.pending = False
            self.speaking_seen = False
            return DialogueEvent.TTS_COMPLETED
        if normalized == "failed":
            self.pending = False
            self.speaking_seen = False
            return DialogueEvent.TTS_FAILED
        if normalized == "idle" and self.speaking_seen:
            self.pending = False
            self.speaking_seen = False
            return DialogueEvent.TTS_COMPLETED
        return None


class DeferredGreeting:
    """Remembers one elapsed greeting deadline until speech is available."""

    def __init__(self) -> None:
        self.due = False

    def defer(self) -> None:
        self.due = True

    def clear(self) -> None:
        self.due = False

    def release(self, *, tts_ready: bool, visitor_present: bool) -> bool:
        if not self.due or not tts_ready or not visitor_present:
            return False
        self.due = False
        return True


QR_ELIGIBLE_INTENTS = frozenset({"affirmative", "reservation"})


@dataclass(frozen=True)
class Transition:
    previous: DialogueState
    current: DialogueState
    accepted: bool
    speech: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.previous != self.current


class DialogueManager:
    """Pure reception state machine; all external work is returned as commands."""

    def __init__(self, max_retries: int = 2) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.max_retries = max_retries
        self.state = DialogueState.IDLE
        self.retry_count = 0
        self.qr_prompt_completed = False
        self.guidance_announcement_completed = False
        self.return_to_reception_ready = False
        self.destination_id: str | None = None

    # ---- handle_intent -------------------------------------------------------

    def handle_intent(self, intent: str) -> Transition:
        normalized = intent.strip().lower()
        previous = self.state

        if normalized == "cancel" and self.state != DialogueState.IDLE:
            self._reset()
            return Transition(previous, self.state, True, ("cancelled",))

        if self.state == DialogueState.WAITING_FOR_INTENT:
            return _intent_waiting(self, previous, normalized)

        handler = _INTENT_TRANSITIONS.get(self.state)
        if handler is None:
            return self._invalid(previous)
        return handler(self, previous)

    # ---- handle_event --------------------------------------------------------

    def handle_event(self, event: DialogueEvent) -> Transition:
        previous = self.state

        if event == DialogueEvent.TTS_FAILED:
            if self.state == DialogueState.IDLE:
                return self._invalid(previous)
            self._reset()
            return Transition(previous, self.state, True)

        handler = _EVENT_TRANSITIONS.get((self.state, event))
        if handler is not None:
            return handler(self, previous)

        return self._invalid(previous)

    # ---- handle_qr_result ----------------------------------------------------

    def handle_qr_result(
        self,
        outcome: QrValidationOutcome,
        destination_id: str = "",
    ) -> Transition:
        previous = self.state
        if self.state != DialogueState.VERIFYING_QR:
            return self._invalid(previous)

        if outcome == QrValidationOutcome.VALID:
            stable_destination = destination_id.strip()
            if not stable_destination:
                self.state = DialogueState.ERROR
                return Transition(previous, self.state, True, ("validation_unavailable",))
            self.destination_id = stable_destination
            self.state = DialogueState.READY_TO_GUIDE
            self.guidance_announcement_completed = False
            return Transition(previous, self.state, True, ("guidance_start",))

        if outcome == QrValidationOutcome.INVALID:
            return self._handle_rejected_qr(previous, "invalid_qr", use_retry=True)
        if outcome == QrValidationOutcome.EXPIRED:
            self.state = DialogueState.ERROR
            return Transition(previous, self.state, True, ("expired_qr",))
        if outcome == QrValidationOutcome.DUPLICATE:
            self.state = DialogueState.WAITING_FOR_QR
            self.qr_prompt_completed = False
            return Transition(previous, self.state, True, ("duplicate_qr",))

        self.state = DialogueState.ERROR
        return Transition(previous, self.state, True, ("validation_unavailable",))

    # ---- handle_return_result ------------------------------------------------

    def handle_return_result(self, arrived: bool) -> Transition:
        previous = self.state
        if self.state != DialogueState.ARRIVED or not self.return_to_reception_ready:
            return self._invalid(previous)
        if arrived:
            self._reset()
            return Transition(previous, self.state, True)
        self.state = DialogueState.ERROR
        self.return_to_reception_ready = False
        return Transition(previous, self.state, True, ("navigation_failed",))

    # ---- helpers -------------------------------------------------------------

    def _handle_rejected_qr(
        self, previous: DialogueState, phrase: str, use_retry: bool
    ) -> Transition:
        if use_retry and self.retry_count < self.max_retries:
            self.retry_count += 1
            self.state = DialogueState.WAITING_FOR_QR
            self.qr_prompt_completed = False
            return Transition(previous, self.state, True, (phrase,))
        self.state = DialogueState.ERROR
        return Transition(previous, self.state, True, (phrase,))

    def _reset(self) -> None:
        self.state = DialogueState.IDLE
        self.retry_count = 0
        self.qr_prompt_completed = False
        self.guidance_announcement_completed = False
        self.return_to_reception_ready = False
        self.destination_id = None

    def _invalid(self, previous: DialogueState) -> Transition:
        return Transition(previous, self.state, False)


# ---- Transition dispatch tables ----------------------------------------------

_Handler = Callable[["DialogueManager", DialogueState], Transition]


def _invalid(manager: DialogueManager, previous: DialogueState) -> Transition:
    return manager._invalid(previous)


def _intent_greeting(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.state = DialogueState.GREETING
    return Transition(previous, manager.state, True, ("greeting",))


def _intent_qr_eligible(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.retry_count = 0
    manager.qr_prompt_completed = False
    manager.state = DialogueState.WAITING_FOR_QR
    return Transition(previous, manager.state, True, ("request_qr",))


def _intent_negative(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager._reset()
    return Transition(previous, manager.state, True, ("no_reservation",))


def _intent_repeat(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.qr_prompt_completed = False
    return Transition(previous, manager.state, True, ("request_qr",))


def _intent_clarify(manager: DialogueManager, previous: DialogueState) -> Transition:
    return Transition(previous, manager.state, True, ("clarify_intent",))


def _intent_waiting(manager: DialogueManager, previous: DialogueState, normalized: str) -> Transition:
    if normalized in QR_ELIGIBLE_INTENTS:
        manager.retry_count = 0
        manager.qr_prompt_completed = False
        manager.state = DialogueState.WAITING_FOR_QR
        return Transition(previous, manager.state, True, ("request_qr",))
    if normalized == "negative":
        manager._reset()
        return Transition(previous, manager.state, True, ("no_reservation",))
    if normalized in {"repeat", "greeting"}:
        return Transition(previous, manager.state, True, ("clarify_intent",))
    if normalized == "unknown":
        if manager.retry_count < manager.max_retries:
            manager.retry_count += 1
            return Transition(previous, manager.state, True, ("clarify_intent",))
        manager.state = DialogueState.ERROR
        return Transition(previous, manager.state, True, ("clarification_failed",))
    return manager._invalid(previous)


_INTENT_TRANSITIONS: dict[DialogueState, _Handler] = {
    DialogueState.IDLE: _intent_greeting,
    DialogueState.PRESENCE_ARMED: _intent_greeting,
    DialogueState.WAITING_FOR_QR: _intent_repeat,
}


def _event_visitor_approached(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.state = DialogueState.PRESENCE_ARMED
    return Transition(previous, manager.state, True)


def _event_visitor_left(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager._reset()
    return Transition(previous, manager.state, True)


def _event_presence_greeting_timeout(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.state = DialogueState.GREETING
    return Transition(previous, manager.state, True, ("greeting",))


def _event_tts_completed_greeting(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.state = DialogueState.WAITING_FOR_INTENT
    return Transition(previous, manager.state, True)


def _event_tts_completed_wwf(manager: DialogueManager, previous: DialogueState) -> Transition:
    return Transition(previous, manager.state, True)


def _event_tts_completed_wqr(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.qr_prompt_completed = True
    return Transition(previous, manager.state, True)


def _event_tts_completed_rtg(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.guidance_announcement_completed = True
    return Transition(previous, manager.state, True)


def _event_inactivity_timeout_wwf(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.state = DialogueState.ERROR
    return Transition(previous, manager.state, True, ("session_timeout",))


def _event_inactivity_timeout_wqr(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.state = DialogueState.ERROR
    return Transition(previous, manager.state, True, ("session_timeout",))


def _event_qr_detected(manager: DialogueManager, previous: DialogueState) -> Transition:
    if not manager.qr_prompt_completed:
        return manager._invalid(previous)
    manager.state = DialogueState.VERIFYING_QR
    return Transition(previous, manager.state, True)


def _event_nav_started(manager: DialogueManager, previous: DialogueState) -> Transition:
    if not manager.guidance_announcement_completed:
        return manager._invalid(previous)
    manager.state = DialogueState.NAVIGATING
    return Transition(previous, manager.state, True)


def _event_nav_failed(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.state = DialogueState.ERROR
    return Transition(previous, manager.state, True, ("navigation_failed",))


def _event_nav_arrived(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.state = DialogueState.ARRIVED
    return Transition(previous, manager.state, True, ("arrived",))


def _event_tts_completed_arrived(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager.return_to_reception_ready = True
    return Transition(previous, manager.state, True)


def _event_error_recovery(manager: DialogueManager, previous: DialogueState) -> Transition:
    manager._reset()
    return Transition(previous, manager.state, True)


_EVENT_TRANSITIONS: dict[tuple[DialogueState, DialogueEvent], _Handler] = {
    (DialogueState.IDLE, DialogueEvent.VISITOR_APPROACHED): _event_visitor_approached,
    (DialogueState.PRESENCE_ARMED, DialogueEvent.VISITOR_LEFT): _event_visitor_left,
    (DialogueState.PRESENCE_ARMED, DialogueEvent.PRESENCE_GREETING_TIMEOUT): _event_presence_greeting_timeout,
    (DialogueState.GREETING, DialogueEvent.TTS_COMPLETED): _event_tts_completed_greeting,
    (DialogueState.WAITING_FOR_INTENT, DialogueEvent.TTS_COMPLETED): _event_tts_completed_wwf,
    (DialogueState.WAITING_FOR_INTENT, DialogueEvent.INACTIVITY_TIMEOUT): _event_inactivity_timeout_wwf,
    (DialogueState.WAITING_FOR_QR, DialogueEvent.TTS_COMPLETED): _event_tts_completed_wqr,
    (DialogueState.WAITING_FOR_QR, DialogueEvent.INACTIVITY_TIMEOUT): _event_inactivity_timeout_wqr,
    (DialogueState.WAITING_FOR_QR, DialogueEvent.QR_DETECTED): _event_qr_detected,
    (DialogueState.READY_TO_GUIDE, DialogueEvent.TTS_COMPLETED): _event_tts_completed_rtg,
    (DialogueState.READY_TO_GUIDE, DialogueEvent.NAVIGATION_STARTED): _event_nav_started,
    (DialogueState.READY_TO_GUIDE, DialogueEvent.NAVIGATION_FAILED): _event_nav_failed,
    (DialogueState.NAVIGATING, DialogueEvent.NAVIGATION_ARRIVED): _event_nav_arrived,
    (DialogueState.NAVIGATING, DialogueEvent.NAVIGATION_FAILED): _event_nav_failed,
    (DialogueState.ARRIVED, DialogueEvent.TTS_COMPLETED): _event_tts_completed_arrived,
    (DialogueState.ERROR, DialogueEvent.TTS_COMPLETED): _event_error_recovery,
    (DialogueState.ERROR, DialogueEvent.INACTIVITY_TIMEOUT): _event_error_recovery,
}
