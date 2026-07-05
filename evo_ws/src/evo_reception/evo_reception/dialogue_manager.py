from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from evo_reception.qr_integration import QrValidationOutcome


class DialogueState(str, Enum):
    IDLE = "IDLE"
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

    def mark_requested(self) -> None:
        self.pending = True
        self.speaking_seen = False

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
            # QueuedTts publishes completed and idle back-to-back. If DDS
            # drops completed, idle is a safe completion fallback because a
            # dialogue-owned request was observed speaking and is still pending.
            self.pending = False
            self.speaking_seen = False
            return DialogueEvent.TTS_COMPLETED
        return None


SUPPORTED_RECEPTION_INTENTS = {
    "reservation",
    "check_in",
    "meeting_room",
    "help",
}


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

    def handle_intent(self, intent: str) -> Transition:
        normalized = intent.strip().lower()
        previous = self.state

        if normalized == "cancel" and self.state != DialogueState.IDLE:
            self._reset()
            return Transition(previous, self.state, True, ("cancelled",))

        if self.state == DialogueState.WAITING_FOR_INTENT:
            if normalized in SUPPORTED_RECEPTION_INTENTS:
                self.retry_count = 0
                self.qr_prompt_completed = False
                self.state = DialogueState.WAITING_FOR_QR
                return Transition(
                    previous, self.state, True, ("request_qr",)
                )
            if normalized == "repeat":
                return Transition(
                    previous, self.state, True, ("clarify_intent",)
                )
            if normalized == "unknown":
                if self.retry_count < self.max_retries:
                    self.retry_count += 1
                    return Transition(
                        previous, self.state, True, ("clarify_intent",)
                    )
                self.state = DialogueState.ERROR
                return Transition(
                    previous, self.state, True, ("clarification_failed",)
                )

        if self.state == DialogueState.WAITING_FOR_QR and normalized == "repeat":
            self.qr_prompt_completed = False
            return Transition(previous, self.state, True, ("request_qr",))

        return self._invalid(previous)

    def handle_event(self, event: DialogueEvent) -> Transition:
        previous = self.state

        if event == DialogueEvent.TTS_FAILED:
            if self.state == DialogueState.IDLE:
                return self._invalid(previous)
            self._reset()
            return Transition(previous, self.state, True)

        if self.state == DialogueState.IDLE:
            if event == DialogueEvent.VISITOR_APPROACHED:
                self.state = DialogueState.GREETING
                return Transition(previous, self.state, True, ("greeting",))

        elif self.state == DialogueState.GREETING:
            if event == DialogueEvent.TTS_COMPLETED:
                self.state = DialogueState.WAITING_FOR_INTENT
                return Transition(previous, self.state, True)

        elif self.state == DialogueState.WAITING_FOR_INTENT:
            if event == DialogueEvent.INACTIVITY_TIMEOUT:
                self.state = DialogueState.ERROR
                return Transition(
                    previous, self.state, True, ("session_timeout",)
                )
            if event == DialogueEvent.TTS_COMPLETED:
                return Transition(previous, self.state, True)

        elif self.state == DialogueState.WAITING_FOR_QR:
            if event == DialogueEvent.TTS_COMPLETED:
                self.qr_prompt_completed = True
                return Transition(previous, self.state, True)
            if (
                event == DialogueEvent.QR_DETECTED
                and self.qr_prompt_completed
            ):
                self.state = DialogueState.VERIFYING_QR
                return Transition(previous, self.state, True)
            if event == DialogueEvent.INACTIVITY_TIMEOUT:
                self.state = DialogueState.ERROR
                return Transition(
                    previous, self.state, True, ("session_timeout",)
                )

        elif self.state == DialogueState.VERIFYING_QR:
            # QR outcomes enter through handle_qr_result so a valid result must
            # carry the verified stable destination ID.
            pass

        elif self.state == DialogueState.READY_TO_GUIDE:
            if event == DialogueEvent.TTS_COMPLETED:
                self.guidance_announcement_completed = True
                return Transition(previous, self.state, True)
            if (
                event == DialogueEvent.NAVIGATION_STARTED
                and self.guidance_announcement_completed
            ):
                self.state = DialogueState.NAVIGATING
                return Transition(previous, self.state, True)
            if event == DialogueEvent.NAVIGATION_FAILED:
                self.state = DialogueState.ERROR
                return Transition(
                    previous, self.state, True, ("navigation_failed",)
                )

        elif self.state == DialogueState.NAVIGATING:
            if event == DialogueEvent.NAVIGATION_ARRIVED:
                self.state = DialogueState.ARRIVED
                return Transition(previous, self.state, True, ("arrived",))
            if event == DialogueEvent.NAVIGATION_FAILED:
                self.state = DialogueState.ERROR
                return Transition(
                    previous, self.state, True, ("navigation_failed",)
                )

        elif self.state == DialogueState.ARRIVED:
            if event == DialogueEvent.TTS_COMPLETED:
                self.return_to_reception_ready = True
                return Transition(previous, self.state, True)

        elif self.state == DialogueState.ERROR:
            if event in {
                DialogueEvent.TTS_COMPLETED,
                DialogueEvent.INACTIVITY_TIMEOUT,
            }:
                self._reset()
                return Transition(previous, self.state, True)

        return self._invalid(previous)

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
                return Transition(
                    previous,
                    self.state,
                    True,
                    ("validation_unavailable",),
                )
            self.destination_id = stable_destination
            self.state = DialogueState.READY_TO_GUIDE
            self.guidance_announcement_completed = False
            return Transition(
                previous, self.state, True, ("guidance_start",)
            )

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
        return Transition(
            previous, self.state, True, ("validation_unavailable",)
        )

    def handle_return_result(self, arrived: bool) -> Transition:
        previous = self.state
        if (
            self.state != DialogueState.ARRIVED
            or not self.return_to_reception_ready
        ):
            return self._invalid(previous)
        if arrived:
            self._reset()
            return Transition(previous, self.state, True)
        self.state = DialogueState.ERROR
        self.return_to_reception_ready = False
        return Transition(
            previous, self.state, True, ("navigation_failed",)
        )

    def _handle_rejected_qr(
        self,
        previous: DialogueState,
        phrase: str,
        use_retry: bool,
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
