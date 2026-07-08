from __future__ import annotations

from typing import Callable

from evo_reception_interfaces.action import GuideToDestination
from rclpy.action import ActionClient
from rclpy.node import Node


class NavigationDriver:
    """Manages the lifecycle of a single active navigation action goal."""

    def __init__(
        self,
        node: Node,
        guide_action_name: str,
        on_result: Callable[[int, bool], None],
        on_failure: Callable[[bool], None],
    ) -> None:
        self._node = node
        self._on_result = on_result
        self._on_failure = on_failure
        self._client = ActionClient(node, GuideToDestination, guide_action_name)
        self._request_token = 0
        self._goal_handle = None
        self._send_future = None
        self._is_returning = False

    @property
    def returning(self) -> bool:
        return self._is_returning

    def request(
        self,
        destination_id: str,
        returning: bool = False,
    ) -> None:
        if not destination_id or not self._client.server_is_ready():
            self._on_failure(returning)
            return

        self._request_token += 1
        request_token = self._request_token
        self._is_returning = returning
        goal = GuideToDestination.Goal()
        goal.request_id = str(request_token)
        goal.destination_id = destination_id
        self._send_future = self._client.send_goal_async(
            goal, feedback_callback=self._on_feedback
        )
        self._send_future.add_done_callback(
            lambda completed: self._on_goal_response(completed, request_token)
        )

    def cancel(self) -> None:
        self._request_token += 1
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
            self._goal_handle = None
        elif self._send_future is not None and not self._send_future.done():
            self._send_future.add_done_callback(self._cancel_late_goal)

    def _on_goal_response(self, future, request_token: int) -> None:
        if request_token != self._request_token:
            self._cancel_late_goal(future)
            return
        try:
            goal_handle = future.result()
        except Exception as exc:
            self._node.get_logger().error(f"Navigation goal request failed: {exc}")
            self._on_failure(self._is_returning)
            return
        if goal_handle is None or not goal_handle.accepted:
            self._on_failure(self._is_returning)
            return

        self._goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda completed: self._on_result_callback(completed, request_token)
        )

    def _on_result_callback(self, future, request_token: int) -> None:
        if request_token != self._request_token:
            return
        self._goal_handle = None
        try:
            wrapped_result = future.result()
            outcome = wrapped_result.result.outcome
        except Exception as exc:
            self._node.get_logger().error(f"Navigation result failed: {exc}")
            outcome = GuideToDestination.Result.FAILED

        arrived = outcome == GuideToDestination.Result.ARRIVED
        self._on_result(self._request_token, arrived)

    def _on_feedback(self, feedback_message) -> None:
        self._node.get_logger().debug(
            f"Navigation feedback: {feedback_message.feedback.state}"
        )

    @staticmethod
    def _cancel_late_goal(future) -> None:
        try:
            goal_handle = future.result()
            if goal_handle is not None and goal_handle.accepted:
                goal_handle.cancel_goal_async()
        except Exception:
            pass
