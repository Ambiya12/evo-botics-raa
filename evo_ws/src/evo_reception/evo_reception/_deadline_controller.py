from __future__ import annotations

import time
from typing import Callable

from evo_reception.dialogue_manager import DialogueEvent, DialogueState


class DeadlineController:
    """Manages time-based state-machine deadlines including STT pause/resume."""

    def __init__(
        self,
        intent_timeout_sec: float,
        qr_inactivity_timeout_sec: float,
        presence_greeting_fallback_sec: float,
    ) -> None:
        self.intent_timeout_sec = intent_timeout_sec
        self.qr_inactivity_timeout_sec = qr_inactivity_timeout_sec
        self.presence_greeting_fallback_sec = presence_greeting_fallback_sec
        self.deadline: float | None = None
        self.deadline_event: DialogueEvent | None = None
        self.paused_intent_deadline_remaining: float | None = None

    def refresh(self, state: DialogueState, has_speech: bool) -> None:
        self.paused_intent_deadline_remaining = None
        if has_speech:
            self.deadline = None
            self.deadline_event = None
        elif state == DialogueState.PRESENCE_ARMED:
            if self.presence_greeting_fallback_sec > 0.0:
                self.deadline = time.monotonic() + self.presence_greeting_fallback_sec
                self.deadline_event = DialogueEvent.PRESENCE_GREETING_TIMEOUT
            else:
                self.deadline = None
                self.deadline_event = None
        elif state == DialogueState.WAITING_FOR_INTENT:
            self.deadline = time.monotonic() + self.intent_timeout_sec
            self.deadline_event = DialogueEvent.INACTIVITY_TIMEOUT
        elif state == DialogueState.WAITING_FOR_QR:
            self.deadline = time.monotonic() + self.qr_inactivity_timeout_sec
            self.deadline_event = DialogueEvent.INACTIVITY_TIMEOUT
        else:
            self.deadline = None
            self.deadline_event = None

    def on_stt_transcribing(self, state: DialogueState) -> bool:
        if (
            state == DialogueState.WAITING_FOR_INTENT
            and self.deadline is not None
        ):
            self.paused_intent_deadline_remaining = max(
                0.0, self.deadline - time.monotonic()
            )
            self.deadline = None
            self.deadline_event = None
            return True
        return False

    def on_stt_idle(self, state: DialogueState) -> bool:
        if self.paused_intent_deadline_remaining is not None:
            if state == DialogueState.WAITING_FOR_INTENT:
                self.deadline = time.monotonic() + self.paused_intent_deadline_remaining
                self.deadline_event = DialogueEvent.INACTIVITY_TIMEOUT
            self.paused_intent_deadline_remaining = None
            return True
        return False

    def clear_speech_deadline(self) -> None:
        self.deadline = None
        self.deadline_event = None

    def is_expired(self) -> bool:
        return self.deadline is not None and time.monotonic() >= self.deadline

    def pop_expired(self) -> DialogueEvent | None:
        if not self.is_expired():
            return None
        event = self.deadline_event or DialogueEvent.INACTIVITY_TIMEOUT
        self.deadline = None
        self.deadline_event = None
        return event
