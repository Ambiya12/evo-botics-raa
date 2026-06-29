from evo_navigation.navigation_orchestrator import (
    MockNavigator,
    NavigationGates,
    NavigationOrchestrator,
    NavigationOutcome,
    NavigationState,
)
from evo_navigation.waypoints import Waypoint, WaypointRegistry


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
    navigator: MockNavigator,
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


def test_mock_navigation_success() -> None:
    navigator = MockNavigator(NavigationOutcome.ARRIVED)
    orchestrator, statuses = make_orchestrator(navigator)

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.ARRIVED
    assert [state for state, _ in statuses] == [
        NavigationState.ACCEPTED,
        NavigationState.ACTIVE,
        NavigationState.ARRIVED,
    ]
    assert [waypoint.destination_id for waypoint in navigator.calls] == ["42"]


def test_unknown_destination_fails_without_movement() -> None:
    navigator = MockNavigator()
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


def test_mock_navigation_cancellation() -> None:
    navigator = MockNavigator()
    orchestrator, statuses = make_orchestrator(navigator)

    result = orchestrator.execute(
        "42", timeout_sec=10.0, cancelled=lambda: True
    )

    assert result.outcome == NavigationOutcome.CANCELLED
    assert [state for state, _ in statuses][-1] == NavigationState.CANCELLED


def test_mock_navigation_timeout() -> None:
    navigator = MockNavigator(NavigationOutcome.TIMEOUT)
    orchestrator, statuses = make_orchestrator(navigator)

    result = orchestrator.execute("42", timeout_sec=0.01)

    assert result.outcome == NavigationOutcome.TIMEOUT
    assert [state for state, _ in statuses][-1] == NavigationState.TIMEOUT


def test_mock_navigation_failure() -> None:
    navigator = MockNavigator(NavigationOutcome.FAILED)
    orchestrator, statuses = make_orchestrator(navigator)

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.FAILED
    assert [state for state, _ in statuses][-1] == NavigationState.FAILED


def test_estop_gates_every_request() -> None:
    navigator = MockNavigator()
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
    navigator = MockNavigator()
    orchestrator, _ = make_orchestrator(
        navigator,
        gates=lambda: NavigationGates(False, False, True),
    )

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.FAILED
    assert "Localization" in result.message
    assert navigator.calls == []


def test_nav2_readiness_gates_every_request() -> None:
    navigator = MockNavigator()
    orchestrator, _ = make_orchestrator(
        navigator,
        gates=lambda: NavigationGates(False, True, False),
    )

    result = orchestrator.execute("42", timeout_sec=10.0)

    assert result.outcome == NavigationOutcome.FAILED
    assert "Nav2" in result.message
    assert navigator.calls == []
