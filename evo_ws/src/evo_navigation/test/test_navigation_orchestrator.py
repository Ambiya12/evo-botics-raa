import pytest

from evo_navigation.navigation_orchestrator import (
    NavigationGates,
    NavigationOrchestrator,
    NavigationOutcome,
    NavigationResult,
    NavigationState,
    localization_is_ready,
    validate_navigation_configuration,
)
from evo_navigation.waypoints import Waypoint, WaypointRegistry


class RecordingNavigator:
    def __init__(self, outcome: NavigationOutcome = NavigationOutcome.ARRIVED) -> None:
        self.outcome = outcome
        self.calls: list[Waypoint] = []

    def navigate(self, waypoint, timeout_sec, cancelled) -> NavigationResult:
        self.calls.append(waypoint)
        outcome = (
            NavigationOutcome.CANCELLED if cancelled() else self.outcome
        )
        return NavigationResult(outcome, f"Navigation {outcome.value}.")


def registry() -> WaypointRegistry:
    return WaypointRegistry(
        {
            "reception": Waypoint("reception", "map", 0.0, 0.0, 0.0),
            "42": Waypoint("42", "map", 1.0, 2.0, 0.5),
        },
        hardware_validated=False,
    )


def ready_gates() -> NavigationGates:
    return NavigationGates(
        estop_active=False,
        localization_ready=True,
        nav2_ready=True,
    )


def make_orchestrator(
    navigator: RecordingNavigator,
    gates=ready_gates,
):
    statuses: list[tuple[NavigationState, str]] = []
    orchestrator = NavigationOrchestrator(
        registry(),
        navigator,
        gates,
        lambda state, message: statuses.append((state, message)),
    )
    return orchestrator, statuses


def test_navigation_success() -> None:
    navigator = RecordingNavigator(NavigationOutcome.ARRIVED)
    orchestrator, statuses = make_orchestrator(navigator)

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.ARRIVED
    assert [state for state, _ in statuses] == [
        NavigationState.ACCEPTED,
        NavigationState.ACTIVE,
        NavigationState.ARRIVED,
    ]
    assert [waypoint.destination_id for waypoint in navigator.calls] == ["42"]


def test_real_navigation_requires_explicit_opt_in() -> None:
    with pytest.raises(ValueError, match="locked"):
        validate_navigation_configuration(False, True)


def test_real_navigation_requires_validated_waypoints() -> None:
    with pytest.raises(ValueError, match="hardware_validated"):
        validate_navigation_configuration(True, False)


def test_real_navigation_accepts_both_safety_keys() -> None:
    assert validate_navigation_configuration(True, True) is None


def test_unknown_destination_fails_without_movement() -> None:
    navigator = RecordingNavigator()
    gate_checks = []
    orchestrator, statuses = make_orchestrator(
        navigator,
        gates=lambda: gate_checks.append(True) or ready_gates(),
    )

    result = orchestrator.execute("unknown", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.FAILED
    assert [state for state, _ in statuses] == [NavigationState.FAILED]
    assert navigator.calls == []
    assert gate_checks == [True]


def test_navigation_cancellation() -> None:
    navigator = RecordingNavigator()
    orchestrator, statuses = make_orchestrator(navigator)

    result = orchestrator.execute(
        "42", timeout_sec=10.0, cancelled=lambda: True
    )

    assert result.outcome == NavigationOutcome.CANCELLED
    assert [state for state, _ in statuses][-1] == NavigationState.CANCELLED


def test_navigation_timeout() -> None:
    navigator = RecordingNavigator(NavigationOutcome.TIMEOUT)
    orchestrator, statuses = make_orchestrator(navigator)

    result = orchestrator.execute("42", timeout_sec=0.01)

    assert result.outcome == NavigationOutcome.TIMEOUT
    assert [state for state, _ in statuses][-1] == NavigationState.TIMEOUT


def test_navigation_failure() -> None:
    navigator = RecordingNavigator(NavigationOutcome.FAILED)
    orchestrator, statuses = make_orchestrator(navigator)

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.FAILED
    assert [state for state, _ in statuses][-1] == NavigationState.FAILED


def test_estop_gates_every_request() -> None:
    navigator = RecordingNavigator()
    orchestrator, statuses = make_orchestrator(
        navigator,
        gates=lambda: NavigationGates(True, True, True),
    )

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.FAILED
    assert "Emergency stop" in result.message
    assert navigator.calls == []
    assert statuses[-1][0] == NavigationState.FAILED


def test_localization_readiness_gates_every_request() -> None:
    navigator = RecordingNavigator()
    orchestrator, _ = make_orchestrator(
        navigator,
        gates=lambda: NavigationGates(False, False, True),
    )

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.FAILED
    assert "Localization" in result.message
    assert navigator.calls == []


def test_nav2_readiness_gates_every_request() -> None:
    navigator = RecordingNavigator()
    orchestrator, _ = make_orchestrator(
        navigator,
        gates=lambda: NavigationGates(False, True, False),
    )

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.FAILED
    assert "Nav2" in result.message
    assert navigator.calls == []


def test_stationary_valid_amcl_pose_does_not_expire_by_default() -> None:
    assert localization_is_ready(
        valid_pose_received=True,
        last_seen_at=10.0,
        timeout_sec=0.0,
        now=10_000.0,
    )


def test_optional_amcl_freshness_limit_remains_available() -> None:
    assert not localization_is_ready(
        valid_pose_received=True,
        last_seen_at=10.0,
        timeout_sec=5.0,
        now=16.0,
    )
    assert not localization_is_ready(
        valid_pose_received=False,
        last_seen_at=0.0,
        timeout_sec=0.0,
        now=16.0,
    )
