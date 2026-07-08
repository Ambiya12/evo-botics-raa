"""Typed readiness probe for real reception navigation."""

from __future__ import annotations

import argparse
import math
import time

from evo_reception_interfaces.action import GuideToDestination
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool


class ReceptionNavReadinessChecker(Node):
    def __init__(
        self,
        action_name: str = "/reception/guide_to_destination",
        max_localization_xy_variance: float = 0.5,
    ) -> None:
        super().__init__("reception_nav_readiness_checker")
        if max_localization_xy_variance <= 0.0:
            raise ValueError(
                "max_localization_xy_variance must be greater than zero"
            )

        self.max_localization_xy_variance = max_localization_xy_variance
        self.map_ready = False
        self.localization_ready = False
        self.estop_active: bool | None = None
        self.action_client = ActionClient(
            self,
            GuideToDestination,
            action_name,
        )

        latched_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            OccupancyGrid,
            "/map",
            self._on_map,
            latched_qos,
        )
        self.create_subscription(
            Bool,
            "/e_stop_active",
            self._on_estop,
            latched_qos,
        )
        self.create_subscription(
            PoseWithCovarianceStamped,
            "/amcl_pose",
            self._on_localization,
            10,
        )

    def _on_map(self, _message: OccupancyGrid) -> None:
        self.map_ready = True

    def _on_estop(self, message: Bool) -> None:
        self.estop_active = bool(message.data)

    def _on_localization(self, message: PoseWithCovarianceStamped) -> None:
        covariance = message.pose.covariance
        x_variance = float(covariance[0])
        y_variance = float(covariance[7])
        self.localization_ready = (
            message.header.frame_id == "map"
            and math.isfinite(x_variance)
            and math.isfinite(y_variance)
            and 0.0 <= x_variance <= self.max_localization_xy_variance
            and 0.0 <= y_variance <= self.max_localization_xy_variance
        )

    def status(self) -> dict:
        return {
            "action": self.action_client.server_is_ready(),
            "map": self.map_ready,
            "localization": self.localization_ready,
            "estop": self.estop_active,
        }

    @staticmethod
    def is_ready(status: dict) -> bool:
        return (
            status["action"]
            and status["map"]
            and status["localization"]
            and status["estop"] is False
        )


def format_status(status: dict) -> str:
    estop = status["estop"]
    return (
        f"action={'ready' if status['action'] else 'missing'}; "
        f"map={'ready' if status['map'] else 'missing'}; "
        f"localization={'ready' if status['localization'] else 'missing'}; "
        f"estop={'clear' if estop is False else 'active' if estop else 'missing'}"
    )


def main(args=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-sec", type=float, default=60.0)
    parser.add_argument("--progress-sec", type=float, default=5.0)
    parser.add_argument(
        "--action-name",
        default="/reception/guide_to_destination",
    )
    parser.add_argument(
        "--max-localization-xy-variance",
        type=float,
        default=0.5,
    )
    parsed, ros_args = parser.parse_known_args(args)
    if parsed.timeout_sec <= 0.0:
        parser.error("--timeout-sec must be greater than zero")

    rclpy.init(args=ros_args)
    checker = ReceptionNavReadinessChecker(
        action_name=parsed.action_name,
        max_localization_xy_variance=parsed.max_localization_xy_variance,
    )
    deadline = time.monotonic() + parsed.timeout_sec
    next_progress = time.monotonic()
    last_status = checker.status()
    exit_code = 1
    try:
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(checker, timeout_sec=0.2)
            last_status = checker.status()
            if checker.is_ready(last_status):
                print(f"READY {format_status(last_status)}", flush=True)
                exit_code = 0
                break
            if time.monotonic() >= next_progress:
                remaining = max(0, int(deadline - time.monotonic()))
                print(
                    f"WAITING remaining={remaining}s; "
                    f"{format_status(last_status)}",
                    flush=True,
                )
                next_progress = time.monotonic() + parsed.progress_sec
        else:
            print(f"FAILED {format_status(last_status)}", flush=True)
    finally:
        checker.destroy_node()
        rclpy.shutdown()

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
