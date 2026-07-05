from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import time
from typing import Callable
from urllib.parse import urlsplit


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


def validate_backend_configuration(
    mock_mode: bool,
    validation_url: str,
    request_timeout_sec: float,
    duplicate_cooldown_sec: float,
) -> str:
    """Validate backend settings and return the normalized URL."""
    errors: list[str] = []
    url = validation_url.strip()
    if request_timeout_sec <= 0.0:
        errors.append("request_timeout_sec must be greater than zero")
    if duplicate_cooldown_sec < 0.0:
        errors.append("duplicate_cooldown_sec must be non-negative")
    if not mock_mode:
        parsed = urlsplit(url)
        if not url:
            errors.append("validation_url is required when mock_mode is false")
        elif parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append("validation_url must be an absolute HTTP(S) URL")
        elif parsed.username is not None or parsed.password is not None:
            errors.append("validation_url must not contain credentials")
    if errors:
        raise ValueError(
            "Invalid QR backend configuration: " + "; ".join(errors)
        )
    return url


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
    if normalized in {
        "api_unreachable",
        "malformed_response",
        "timeout",
        "unavailable",
    }:
        return QrValidationOutcome.UNAVAILABLE
    return QrValidationOutcome.INVALID


def successful_validation_data(body: object) -> dict | None:
    """Return validated response data only for the approved success contract."""
    if not isinstance(body, dict) or body.get("status") != "success":
        return None
    data = body.get("data")
    return data if isinstance(data, dict) else None


def parse_destination_ids(value: str) -> frozenset[str]:
    destination_ids = frozenset(
        item.strip() for item in value.split(",") if item.strip()
    )
    if not destination_ids:
        raise ValueError(
            "At least one allowed destination ID must be configured"
        )
    return destination_ids


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
