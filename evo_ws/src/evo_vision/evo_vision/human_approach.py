from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ApproachConfig:
    min_confidence: float
    min_distance_m: float
    max_distance_m: float
    zone_min_x: float
    zone_max_x: float
    zone_min_y: float
    zone_max_y: float
    debounce_frames: int
    cooldown_sec: float
    absence_reset_sec: float

    def validate(self) -> None:
        errors: list[str] = []
        if not 0.0 <= self.min_confidence <= 1.0:
            errors.append("min_confidence must be between 0.0 and 1.0")
        if self.min_distance_m < 0.0:
            errors.append("min_distance_m must be non-negative")
        if self.max_distance_m <= self.min_distance_m:
            errors.append("max_distance_m must be greater than min_distance_m")
        for name, value in (
            ("zone_min_x", self.zone_min_x),
            ("zone_max_x", self.zone_max_x),
            ("zone_min_y", self.zone_min_y),
            ("zone_max_y", self.zone_max_y),
        ):
            if not 0.0 <= value <= 1.0:
                errors.append(f"{name} must be between 0.0 and 1.0")
        if self.zone_max_x <= self.zone_min_x:
            errors.append("zone_max_x must be greater than zone_min_x")
        if self.zone_max_y <= self.zone_min_y:
            errors.append("zone_max_y must be greater than zone_min_y")
        if self.debounce_frames < 1:
            errors.append("debounce_frames must be at least 1")
        if self.cooldown_sec < 0.0:
            errors.append("cooldown_sec must be non-negative")
        if self.absence_reset_sec <= 0.0:
            errors.append("absence_reset_sec must be greater than zero")
        if errors:
            raise ValueError("Invalid human approach configuration: " + "; ".join(errors))


@dataclass(frozen=True)
class PersonObservation:
    tracking_id: str
    confidence: float
    distance_m: float
    normalized_x: float
    normalized_y: float


@dataclass(frozen=True)
class ApproachEvent:
    tracking_id: str
    confidence: float
    distance_m: float


def detection_age_seconds(stamp_sec: float, now_sec: float) -> float | None:
    """Return message age, or None when a producer supplied no timestamp."""
    if stamp_sec == 0.0:
        return None
    return now_sec - stamp_sec


class HumanApproachFilter:
    """Turns repeated person observations into one clean approach event."""

    def __init__(
        self,
        config: ApproachConfig,
        initial_dialogue_state: str = "IDLE",
    ) -> None:
        config.validate()
        self.config = config
        self.dialogue_state = initial_dialogue_state.strip().upper()
        self.candidate_tracking_id = ""
        self.candidate_frames = 0
        self.presence_latched = False
        self.emitted_for_session = False
        self.last_valid_at: float | None = None
        self.last_event_at: float | None = None

    def update_dialogue_state(self, state: str) -> None:
        normalized = state.strip().upper()
        previous = self.dialogue_state
        self.dialogue_state = normalized
        if previous == "UNKNOWN" and normalized == "IDLE":
            self.presence_latched = False
            self._reset_candidate()
        if previous != "IDLE" and normalized == "IDLE":
            self.emitted_for_session = False

    def process(
        self,
        observation: PersonObservation,
        now: float,
    ) -> ApproachEvent | None:
        if not self.is_valid_observation(observation):
            self._reset_candidate()
            self.tick(now)
            return None

        self.last_valid_at = now
        if self.dialogue_state != "IDLE":
            self.presence_latched = True
            self._reset_candidate()
            return None
        if self.presence_latched or self.emitted_for_session:
            return None
        if (
            self.last_event_at is not None
            and now - self.last_event_at < self.config.cooldown_sec
        ):
            return None

        tracking_id = observation.tracking_id.strip() or "anonymous"
        if tracking_id == self.candidate_tracking_id:
            self.candidate_frames += 1
        else:
            self.candidate_tracking_id = tracking_id
            self.candidate_frames = 1
        if self.candidate_frames < self.config.debounce_frames:
            return None

        self.presence_latched = True
        self.emitted_for_session = True
        self.last_event_at = now
        self._reset_candidate()
        return ApproachEvent(
            tracking_id=tracking_id,
            confidence=observation.confidence,
            distance_m=observation.distance_m,
        )

    def tick(self, now: float) -> None:
        if self.last_valid_at is None:
            return
        if now - self.last_valid_at < self.config.absence_reset_sec:
            return
        self.last_valid_at = None
        self.presence_latched = False
        self._reset_candidate()
        if (
            self.dialogue_state == "IDLE"
            and self.last_event_at is not None
            and now - self.last_event_at >= self.config.cooldown_sec
        ):
            self.emitted_for_session = False

    def is_person_present(self, now: float) -> bool:
        return (
            self.presence_latched
            and self.last_valid_at is not None
            and now - self.last_valid_at < self.config.absence_reset_sec
        )

    def _reset_candidate(self) -> None:
        self.candidate_tracking_id = ""
        self.candidate_frames = 0
