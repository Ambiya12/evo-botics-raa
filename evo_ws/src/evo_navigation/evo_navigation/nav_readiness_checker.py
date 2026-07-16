"""Persistent ROS graph probe used to verify that Nav2 is ready."""

from __future__ import annotations

import argparse
import time
from typing import Dict, Optional

import rclpy
from lifecycle_msgs.srv import GetState
from rclpy.node import Node
from rclpy.task import Future


BASE_LIFECYCLE_NODES = (
    "map_server",
    "amcl",
    "controller_server",
    "smoother_server",
    "planner_server",
    "behavior_server",
    "bt_navigator",
    "waypoint_follower",
    "velocity_smoother",
    "global_costmap/global_costmap",
)

LIFECYCLE_REQUEST_TIMEOUT_SEC = 5.0


class NavReadinessChecker(Node):
    def __init__(
        self,
        require_collision_monitor: bool = False,
        lifecycle_request_timeout_sec: float = LIFECYCLE_REQUEST_TIMEOUT_SEC,
    ) -> None:
        super().__init__("nav_readiness_checker")
        if lifecycle_request_timeout_sec <= 0.0:
            raise ValueError("lifecycle_request_timeout_sec must be greater than zero")

        lifecycle_nodes = list(BASE_LIFECYCLE_NODES)
        if require_collision_monitor:
            lifecycle_nodes.append("collision_monitor")

        self._lifecycle_request_timeout_sec = lifecycle_request_timeout_sec
        self._lifecycle_clients = {
            name: self.create_client(GetState, f"/{name}/get_state")
            for name in lifecycle_nodes
        }
        self._lifecycle_futures: Dict[str, Optional[Future]] = {
            name: None for name in lifecycle_nodes
        }
        self._lifecycle_requested_at: Dict[str, Optional[float]] = {
            name: None for name in lifecycle_nodes
        }
        self._lifecycle_probe_timeouts = {name: 0 for name in lifecycle_nodes}
        self._lifecycle_probe_retrying = {name: False for name in lifecycle_nodes}
        self.lifecycle_states = {name: "unavailable" for name in lifecycle_nodes}

    def _replace_lifecycle_client(self, name: str) -> None:
        client = self._lifecycle_clients[name]
        self.destroy_client(client)
        self._lifecycle_clients[name] = self.create_client(
            GetState,
            f"/{name}/get_state",
        )

    def poll_lifecycle_states(self, now: Optional[float] = None) -> None:
        current_time = time.monotonic() if now is None else now
        for name in tuple(self._lifecycle_clients):
            if self.lifecycle_states[name] == "active":
                continue
            client = self._lifecycle_clients[name]
            future = self._lifecycle_futures[name]
            if future is not None:
                if future.done():
                    try:
                        response = future.result()
                        self.lifecycle_states[name] = response.current_state.label
                        self._lifecycle_probe_retrying[name] = False
                    except Exception:
                        self.lifecycle_states[name] = "unavailable"
                    self._lifecycle_futures[name] = None
                    self._lifecycle_requested_at[name] = None
                    continue

                requested_at = self._lifecycle_requested_at[name]
                if (
                    requested_at is not None
                    and current_time - requested_at
                    >= self._lifecycle_request_timeout_sec
                ):
                    try:
                        client.remove_pending_request(future)
                    except Exception:
                        future.cancel()
                    self._lifecycle_futures[name] = None
                    self._lifecycle_requested_at[name] = None
                    self._lifecycle_probe_timeouts[name] += 1
                    self._lifecycle_probe_retrying[name] = True
                    self.lifecycle_states[name] = "unavailable"
                    self._replace_lifecycle_client(name)
                return

            if client.service_is_ready():
                self._lifecycle_futures[name] = client.call_async(GetState.Request())
                self._lifecycle_requested_at[name] = current_time
                return

    def validator_available(self) -> bool:
        return any(
            name == "navigation_goal_validator" and namespace == "/"
            for name, namespace in self.get_node_names_and_namespaces()
        )

    def status(self) -> dict:
        inactive = next(
            (
                (
                    f"/{name}: {state} "
                    f"(lifecycle probe timed out "
                    f"{self._lifecycle_probe_timeouts[name]} time(s); retrying)"
                    if self._lifecycle_probe_retrying[name]
                    else f"/{name}: {state}"
                )
                for name, state in self.lifecycle_states.items()
                if state != "active"
            ),
            "active",
        )
        return {
            "lifecycle": inactive,
            "map": self.count_publishers("/map"),
            "validator": self.validator_available(),
            "cmd_vel_nav_raw": self.count_publishers("/cmd_vel_nav_raw"),
            "cmd_vel": self.count_publishers("/cmd_vel"),
        }

    @staticmethod
    def is_ready(status: dict) -> bool:
        return (
            status["lifecycle"] == "active"
            and status["map"] > 0
            and status["validator"]
            and status["cmd_vel_nav_raw"] > 0
            and status["cmd_vel"] == 1
        )


def format_status(status: dict) -> str:
    return (
        f"lifecycle={status['lifecycle']}; "
        f"map={status['map']}; "
        f"validator={'yes' if status['validator'] else 'no'}; "
        f"cmd_vel_nav_raw={status['cmd_vel_nav_raw']}; "
        f"cmd_vel={status['cmd_vel']}"
    )


def main(args=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-sec", type=float, default=115.0)
    parser.add_argument("--progress-sec", type=float, default=10.0)
    parser.add_argument("--require-collision-monitor", action="store_true")
    parsed, ros_args = parser.parse_known_args(args)

    rclpy.init(args=ros_args)
    checker = NavReadinessChecker(parsed.require_collision_monitor)
    deadline = time.monotonic() + parsed.timeout_sec
    next_progress = time.monotonic()
    last_status = checker.status()
    exit_code = 1
    try:
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(checker, timeout_sec=0.2)
            checker.poll_lifecycle_states()
            last_status = checker.status()
            if checker.is_ready(last_status):
                print(f"READY {format_status(last_status)}", flush=True)
                exit_code = 0
                break
            if time.monotonic() >= next_progress:
                remaining = max(0, int(deadline - time.monotonic()))
                print(
                    f"WAITING remaining={remaining}s; {format_status(last_status)}",
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
