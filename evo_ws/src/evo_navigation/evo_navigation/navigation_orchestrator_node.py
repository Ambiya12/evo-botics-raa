from __future__ import annotations

import math
from pathlib import Path
import time

from action_msgs.msg import GoalStatus
from ament_index_python.packages import get_package_share_directory
from evo_reception_interfaces.action import GuideToDestination
from evo_reception_interfaces.msg import NavigationStatus
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool

from evo_navigation.navigation_orchestrator import (
    MockNavigator,
    NavigationGates,
    NavigationOrchestrator,
    NavigationOutcome,
    NavigationResult,
    NavigationState,
    validate_navigation_mode,
)
from evo_navigation.waypoints import Waypoint, WaypointConfigurationError, WaypointRegistry


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


class NavigationOrchestratorNode(Node):
    def __init__(self) -> None:
        super().__init__("navigation_orchestrator_node")
        default_registry = (
            Path(get_package_share_directory("evo_navigation"))
            / "config"
            / "reception_waypoints.yaml"
        )
        registry_path = Path(
            str(
                self.declare_parameter(
                    "waypoint_config_path", str(default_registry)
                ).value
            )
        ).expanduser()
        self.mock_navigation = bool(
            self.declare_parameter("mock_navigation", True).value
        )
        self.allow_real_navigation = bool(
            self.declare_parameter("allow_real_navigation", False).value
        )
        mock_outcome_value = str(
            self.declare_parameter("mock_outcome", "arrived").value
        ).strip().lower()
        self.navigation_timeout_sec = float(
            self.declare_parameter("navigation_timeout_sec", 120.0).value
        )
        action_name = str(
            self.declare_parameter(
                "guide_action_name", "/reception/guide_to_destination"
            ).value
        )
        status_topic = str(
            self.declare_parameter(
                "status_topic", "/reception/navigation/status"
            ).value
        )
        nav2_action_name = str(
            self.declare_parameter(
                "nav2_action_name", "/navigate_to_pose"
            ).value
        )
        estop_topic = str(
            self.declare_parameter("estop_topic", "/e_stop_active").value
        )
        localization_topic = str(
            self.declare_parameter("localization_topic", "/amcl_pose").value
        )
        self.estop_active = bool(
            self.declare_parameter(
                "mock_estop_active", False if self.mock_navigation else True
            ).value
        )
        self.localization_ready = bool(
            self.declare_parameter(
                "mock_localization_ready", self.mock_navigation
            ).value
        )
        self.mock_nav2_ready = bool(
            self.declare_parameter("mock_nav2_ready", self.mock_navigation).value
        )
        if self.navigation_timeout_sec <= 0.0:
            raise ValueError("'navigation_timeout_sec' must be greater than zero")

        self.registry = WaypointRegistry.from_yaml(registry_path)
        self.navigation_mode = validate_navigation_mode(
            self.mock_navigation,
            self.allow_real_navigation,
            self.registry.hardware_validated,
        )

        if self.mock_navigation:
            try:
                mock_outcome = NavigationOutcome(mock_outcome_value)
            except ValueError as exc:
                raise ValueError(
                    "'mock_outcome' must be arrived, cancelled, timeout, or failed"
                ) from exc
            self.navigator = MockNavigator(mock_outcome)
            self.nav2_navigator = None
        else:
            self.nav2_navigator = Nav2Navigator(self, nav2_action_name)
            self.navigator = self.nav2_navigator

        status_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.status_publisher = self.create_publisher(
            NavigationStatus, status_topic, status_qos
        )
        self.create_subscription(Bool, estop_topic, self.on_estop, status_qos)
        if not self.mock_navigation:
            self.create_subscription(
                PoseWithCovarianceStamped,
                localization_topic,
                self.on_localization,
                10,
            )

        self.active_goal_handle = None
        self.active_request_id = ""
        self.active_destination_id = ""
        self.orchestrator = NavigationOrchestrator(
            self.registry,
            self.navigator,
            self.current_gates,
            self.publish_status,
        )
        callback_group = ReentrantCallbackGroup()
        self.action_server = ActionServer(
            self,
            GuideToDestination,
            action_name,
            execute_callback=self.execute_goal,
            goal_callback=self.accept_goal,
            cancel_callback=self.accept_cancel,
            callback_group=callback_group,
        )
        if self.mock_navigation:
            self.get_logger().warning(
                "STATIONARY SAFETY MODE ACTIVE: mock_navigation=true; "
                "Nav2 goals will not be sent."
            )
        else:
            self.get_logger().warning(
                "REAL NAVIGATION MODE ACTIVE: mock_navigation=false and "
                "allow_real_navigation=true; Nav2 goals may move the robot."
            )
        self.get_logger().info(
            f"Navigation orchestrator ready: mode={self.navigation_mode} "
            f"action={action_name} waypoint_config={registry_path}"
        )

    def current_gates(self) -> NavigationGates:
        nav2_ready = (
            self.mock_nav2_ready
            if self.mock_navigation
            else bool(self.nav2_navigator and self.nav2_navigator.ready())
        )
        return NavigationGates(
            estop_active=self.estop_active,
            localization_ready=self.localization_ready,
            nav2_ready=nav2_ready,
        )

    def on_estop(self, message: Bool) -> None:
        self.estop_active = message.data

    def on_localization(self, message: PoseWithCovarianceStamped) -> None:
        self.localization_ready = bool(message.header.frame_id)

    def accept_goal(self, goal_request) -> GoalResponse:
        if self.active_goal_handle is not None:
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def accept_cancel(self, goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def execute_goal(self, goal_handle):
        request = goal_handle.request
        self.active_goal_handle = goal_handle
        self.active_request_id = request.request_id
        self.active_destination_id = request.destination_id
        result = self.orchestrator.execute(
            request.destination_id,
            self.navigation_timeout_sec,
            cancelled=lambda: (
                goal_handle.is_cancel_requested or self.estop_active
            ),
        )

        response = GuideToDestination.Result()
        outcomes = {
            NavigationOutcome.ARRIVED: GuideToDestination.Result.ARRIVED,
            NavigationOutcome.CANCELLED: GuideToDestination.Result.CANCELLED,
            NavigationOutcome.TIMEOUT: GuideToDestination.Result.TIMEOUT,
            NavigationOutcome.FAILED: GuideToDestination.Result.FAILED,
        }
        response.outcome = outcomes[result.outcome]
        response.message = result.message
        if result.outcome == NavigationOutcome.ARRIVED:
            goal_handle.succeed()
        elif result.outcome == NavigationOutcome.CANCELLED:
            goal_handle.canceled()
        else:
            goal_handle.abort()
        self.active_goal_handle = None
        return response

    def publish_status(self, state: NavigationState, message: str) -> None:
        status = NavigationStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.request_id = self.active_request_id
        status.destination_id = self.active_destination_id
        status.state = state.value
        status.message = message
        self.status_publisher.publish(status)
        if self.active_goal_handle is not None:
            feedback = GuideToDestination.Feedback()
            feedback.state = state.value
            self.active_goal_handle.publish_feedback(feedback)

    def destroy_node(self) -> bool:
        self.action_server.destroy()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node: NavigationOrchestratorNode | None = None
    try:
        node = NavigationOrchestratorNode()
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(node)
        executor.spin()
    except (ValueError, WaypointConfigurationError) as exc:
        rclpy.logging.get_logger("navigation_orchestrator_node").fatal(str(exc))
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
