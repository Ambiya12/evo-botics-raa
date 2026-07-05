from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Callable, Protocol

from evo_navigation.waypoints import Waypoint, WaypointRegistry


class NavigationState(str, Enum):
    ACCEPTED = "accepted"
    ACTIVE = "active"
    ARRIVED = "arrived"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    FAILED = "failed"


class NavigationOutcome(str, Enum):
    ARRIVED = "arrived"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    FAILED = "failed"


def validate_navigation_mode(
    mock_navigation: bool,
    allow_real_navigation: bool,
    hardware_validated: bool,
) -> str:
    """Return the active mode or reject an unsafe real-navigation setup."""
    if mock_navigation:
        return "mock"
    if not allow_real_navigation:
        raise ValueError(
            "Real navigation is locked. Set both mock_navigation:=false and "
            "allow_real_navigation:=true only at a controlled navigation site."
        )
    if not hardware_validated:
        raise ValueError(
            "Real navigation requires hardware_validated: true in the waypoint registry"
        )
    return "real"


@dataclass(frozen=True)
class NavigationGates:
    estop_active: bool
    localization_ready: bool
    nav2_ready: bool

    def rejection_reason(self) -> str | None:
        if self.estop_active:
            return "Emergency stop is active."
        if not self.localization_ready:
            return "Localization is not ready."
        if not self.nav2_ready:
            return "Nav2 is not ready."
        return None


@dataclass(frozen=True)
class NavigationResult:
    outcome: NavigationOutcome
    message: str


class Navigator(Protocol):
    def navigate(
        self,
        waypoint: Waypoint,
        timeout_sec: float,
        cancelled: Callable[[], bool],
    ) -> NavigationResult:
        """Navigate to one already-validated configured waypoint."""


class MockNavigator:
    def __init__(self, outcome: NavigationOutcome = NavigationOutcome.ARRIVED) -> None:
        self.outcome = outcome
        self.calls: list[Waypoint] = []

    def navigate(
        self,
        waypoint: Waypoint,
        timeout_sec: float,
        cancelled: Callable[[], bool],
    ) -> NavigationResult:
        self.calls.append(waypoint)
        if cancelled():
            return NavigationResult(
                NavigationOutcome.CANCELLED, "Mock navigation cancelled."
            )
        messages = {
            NavigationOutcome.ARRIVED: "Mock navigation arrived.",
            NavigationOutcome.CANCELLED: "Mock navigation cancelled.",
            NavigationOutcome.TIMEOUT: "Mock navigation timed out.",
            NavigationOutcome.FAILED: "Mock navigation failed.",
        }
        return NavigationResult(self.outcome, messages[self.outcome])


class NavigationOrchestrator:
    def __init__(
        self,
        registry: WaypointRegistry,
        navigator: Navigator,
        gates: Callable[[], NavigationGates],
        status_callback: Callable[[NavigationState, str], None],
    ) -> None:
        self.registry = registry
        self.navigator = navigator
        self.gates = gates
        self.status_callback = status_callback
        self._execution_lock = Lock()

    def execute(
        self,
        destination_id: str,
        timeout_sec: float,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> NavigationResult:
        if timeout_sec <= 0.0:
            raise ValueError("timeout_sec must be greater than zero")
        if not self._execution_lock.acquire(blocking=False):
            result = NavigationResult(
                NavigationOutcome.FAILED, "Another navigation request is active."
            )
            self.status_callback(NavigationState.FAILED, result.message)
            return result

        try:
            rejection = self.gates().rejection_reason()
            if rejection is not None:
                result = NavigationResult(NavigationOutcome.FAILED, rejection)
                self.status_callback(NavigationState.FAILED, result.message)
                return result

            waypoint = self.registry.get(destination_id)
            if waypoint is None:
                result = NavigationResult(
                    NavigationOutcome.FAILED,
                    f"Unknown destination ID: {destination_id}",
                )
                self.status_callback(NavigationState.FAILED, result.message)
                return result

            self.status_callback(
                NavigationState.ACCEPTED,
                f"Destination '{destination_id}' accepted.",
            )
            self.status_callback(
                NavigationState.ACTIVE,
                f"Navigating to '{destination_id}'.",
            )
            try:
                result = self.navigator.navigate(
                    waypoint, timeout_sec, cancelled
                )
            except Exception as exc:
                result = NavigationResult(
                    NavigationOutcome.FAILED,
                    f"Navigation backend failed: {exc}",
                )
            self.status_callback(NavigationState(result.outcome.value), result.message)
            return result
        finally:
            self._execution_lock.release()
