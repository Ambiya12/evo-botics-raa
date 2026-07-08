from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Callable, Protocol

from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node

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


def validate_navigation_configuration(
    allow_real_navigation: bool,
    hardware_validated: bool,
) -> None:
    """Reject an unsafe real-navigation setup."""
    if not allow_real_navigation:
        raise ValueError(
            "Real navigation is locked. Set allow_real_navigation:=true only "
            "at a controlled navigation site."
        )
    if not hardware_validated:
        raise ValueError(
            "Real navigation requires hardware_validated: true in the waypoint registry"
        )


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


def localization_is_ready(
    valid_pose_received: bool,
    last_seen_at: float,
    timeout_sec: float,
    now: float,
) -> bool:
    """Evaluate AMCL readiness without requiring periodic stationary updates.

    AMCL may not republish a pose while the robot is stationary. A timeout of
    zero therefore keeps a covariance-validated pose ready; positive values
    remain available for deployments that explicitly require freshness.
    """
    if not valid_pose_received:
        return False
    if timeout_sec == 0.0:
        return True
    return now - last_seen_at <= timeout_sec


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


class Nav2Navigator:
    def __init__(self, node: Node, action_name: str) -> None:
        self.node = node
        self.client = ActionClient(
            node,
            NavigateToPose,
            action_name,
            callback_group=ReentrantCallbackGroup(),
        )

    def ready(self) -> bool:
        return self.client.wait_for_server(timeout_sec=0.0)

    def navigate(
        self,
        waypoint: Waypoint,
        timeout_sec: float,
        cancelled,
    ) -> NavigationResult:
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = waypoint.frame_id
        goal.pose.header.stamp = self.node.get_clock().now().to_msg()
        goal.pose.pose.position.x = waypoint.x
        goal.pose.pose.position.y = waypoint.y
        goal.pose.pose.orientation.z = math.sin(waypoint.yaw / 2.0)
        goal.pose.pose.orientation.w = math.cos(waypoint.yaw / 2.0)

        deadline = time.monotonic() + timeout_sec
        send_future = self.client.send_goal_async(goal)
        while not send_future.done():
            if cancelled() or time.monotonic() >= deadline:
                send_future.add_done_callback(self._cancel_late_goal)
                outcome = (
                    NavigationOutcome.CANCELLED
                    if cancelled()
                    else NavigationOutcome.TIMEOUT
                )
                return NavigationResult(
                    outcome, f"Navigation {outcome.value} before goal acceptance."
                )
            time.sleep(0.02)

        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return NavigationResult(
                NavigationOutcome.FAILED, "Nav2 rejected the waypoint."
            )

        result_future = goal_handle.get_result_async()
        while not result_future.done():
            if cancelled():
                goal_handle.cancel_goal_async()
                return NavigationResult(
                    NavigationOutcome.CANCELLED, "Navigation cancelled."
                )
            if time.monotonic() >= deadline:
                goal_handle.cancel_goal_async()
                return NavigationResult(
                    NavigationOutcome.TIMEOUT, "Navigation timed out."
                )
            time.sleep(0.02)

        wrapped_result = result_future.result()
        if wrapped_result.status == GoalStatus.STATUS_SUCCEEDED:
            return NavigationResult(
                NavigationOutcome.ARRIVED, "Nav2 reached the destination."
            )
        if wrapped_result.status == GoalStatus.STATUS_CANCELED:
            return NavigationResult(
                NavigationOutcome.CANCELLED, "Nav2 navigation was cancelled."
            )
        return NavigationResult(
            NavigationOutcome.FAILED, "Nav2 navigation failed."
        )

    @staticmethod
    def _cancel_late_goal(future) -> None:
        try:
            goal_handle = future.result()
            if goal_handle is not None and goal_handle.accepted:
                goal_handle.cancel_goal_async()
        except Exception:
            pass
