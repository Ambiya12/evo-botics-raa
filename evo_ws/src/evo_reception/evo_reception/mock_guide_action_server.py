from __future__ import annotations

import time

from evo_reception_interfaces.action import GuideToDestination
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node


class MockGuideActionServer(Node):
    """Completes GuideToDestination goals without moving the robot."""

    def __init__(self) -> None:
        super().__init__("mock_guide_action_server")
        self.action_name = str(
            self.declare_parameter(
                "action_name", "/reception/guide_to_destination"
            ).value
        )
        self.travel_time_sec = float(
            self.declare_parameter("travel_time_sec", 3.0).value
        )
        self.return_time_sec = float(
            self.declare_parameter("return_time_sec", 3.0).value
        )
        self.feedback_period_sec = float(
            self.declare_parameter("feedback_period_sec", 0.5).value
        )
        if self.travel_time_sec < 0.0:
            raise ValueError("travel_time_sec must be non-negative")
        if self.return_time_sec < 0.0:
            raise ValueError("return_time_sec must be non-negative")
        if self.feedback_period_sec <= 0.0:
            raise ValueError("feedback_period_sec must be greater than zero")

        self._server = ActionServer(
            self,
            GuideToDestination,
            self.action_name,
            execute_callback=self.execute,
            goal_callback=self.on_goal,
            cancel_callback=self.on_cancel,
        )
        self.get_logger().info(
            f"Mock guide action server ready: action={self.action_name} "
            f"travel_time_sec={self.travel_time_sec:.1f} "
            f"return_time_sec={self.return_time_sec:.1f}"
        )

    def on_goal(self, goal_request: GuideToDestination.Goal) -> GoalResponse:
        self.get_logger().info(
            "Accepted mock guide goal "
            f"request_id={goal_request.request_id} "
            f"destination_id={goal_request.destination_id}"
        )
        return GoalResponse.ACCEPT

    def on_cancel(self, _goal_handle) -> CancelResponse:
        self.get_logger().info("Accepted mock guide cancel request")
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> GuideToDestination.Result:
        destination_id = goal_handle.request.destination_id.strip()
        duration = (
            self.return_time_sec
            if destination_id == "reception"
            else self.travel_time_sec
        )
        deadline = time.monotonic() + duration
        feedback = GuideToDestination.Feedback()
        while time.monotonic() < deadline:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return self._result(
                    GuideToDestination.Result.CANCELLED,
                    f"Mock navigation cancelled for {destination_id}",
                )
            feedback.state = f"mock_navigating:{destination_id}"
            goal_handle.publish_feedback(feedback)
            time.sleep(min(self.feedback_period_sec, max(0.0, deadline - time.monotonic())))

        goal_handle.succeed()
        return self._result(
            GuideToDestination.Result.ARRIVED,
            f"Mock arrived at {destination_id}",
        )

    @staticmethod
    def _result(outcome: int, message: str) -> GuideToDestination.Result:
        result = GuideToDestination.Result()
        result.outcome = outcome
        result.message = message
        return result


def main(args=None) -> None:
    rclpy.init(args=args)
    node: MockGuideActionServer | None = None
    try:
        node = MockGuideActionServer()
        rclpy.spin(node)
    except ValueError as exc:
        rclpy.logging.get_logger("mock_guide_action_server").fatal(str(exc))
        raise SystemExit(2) from exc
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
