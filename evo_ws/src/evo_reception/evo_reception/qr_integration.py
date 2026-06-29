from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import time
from typing import Callable


class QrValidationOutcome(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    DUPLICATE = "duplicate"
    UNAVAILABLE = "unavailable"


class ScanDecision(str, Enum):
    ACCEPTED = "accepted"
    IGNORED_STATE = "ignored_state"
    INVALID = "invalid"
    DUPLICATE = "duplicate"
    BUSY = "busy"


@dataclass(frozen=True)
class ScanAcceptance:
    decision: ScanDecision
    payload: str = ""


def extract_decoded_text(raw_data: str) -> str | None:
    try:
        event = json.loads(raw_data)
    except json.JSONDecodeError:
        text = raw_data.strip()
        return text or None

    if isinstance(event, dict) and isinstance(event.get("decoded_text"), str):
        text = event["decoded_text"].strip()
        return text or None
    return None


def outcome_from_error_code(error_code: str) -> QrValidationOutcome:
    normalized = error_code.strip().lower()
    if normalized in {"already_used", "duplicate", "duplicate_qr"}:
        return QrValidationOutcome.DUPLICATE
    if normalized in {"expired", "expired_reservation", "reservation_expired"}:
        return QrValidationOutcome.EXPIRED
    if normalized in {"api_unreachable", "unavailable"}:
        return QrValidationOutcome.UNAVAILABLE
    return QrValidationOutcome.INVALID


class QrScanGate:
    """Allows one QR validation only during the dialogue QR waiting state."""

    def __init__(
        self,
        duplicate_cooldown_sec: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if duplicate_cooldown_sec < 0.0:
            raise ValueError("duplicate_cooldown_sec must be non-negative")
        self.duplicate_cooldown_sec = duplicate_cooldown_sec
        self.clock = clock
        self.in_flight = False
        self.last_payload = ""
        self.last_payload_at = 0.0

    def accept(
        self,
        raw_data: str,
        dialogue_state: str,
        qr_prompt_completed: bool,
    ) -> ScanAcceptance:
        if dialogue_state != "WAITING_FOR_QR" or not qr_prompt_completed:
            return ScanAcceptance(ScanDecision.IGNORED_STATE)

        payload = extract_decoded_text(raw_data)
        if payload is None:
            return ScanAcceptance(ScanDecision.INVALID)

        now = self.clock()
        if (
            payload == self.last_payload
            and now - self.last_payload_at < self.duplicate_cooldown_sec
        ):
            return ScanAcceptance(ScanDecision.DUPLICATE)
        if self.in_flight:
            return ScanAcceptance(ScanDecision.BUSY)

        self.in_flight = True
        self.last_payload = payload
        self.last_payload_at = now
        return ScanAcceptance(ScanDecision.ACCEPTED, payload)

    def complete(self) -> None:
        self.in_flight = False
