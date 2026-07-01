from __future__ import annotations

import time

from evo_reception_interfaces.msg import PersonApproach, PersonDetection
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from evo_vision.human_approach import (
    ApproachConfig,
    HumanApproachFilter,
    PersonObservation,
)


class HumanApproachNode(Node):
    """Filters detector/replay observations and publishes approach events only."""

    def __init__(self) -> None:
        super().__init__("human_approach_node")
        detections_topic = str(
            self.declare_parameter(
                "detections_topic", "/vision/people/detections"
            ).value
        )
        approach_topic = str(
            self.declare_parameter(
                "approach_topic", "/vision/people/approach"
            ).value
        )
        dialogue_state_topic = str(
            self.declare_parameter(
                "dialogue_state_topic", "/reception/dialogue/state"
            ).value
        )
        self.zone_id = str(
            self.declare_parameter("zone_id", "reception").value
        ).strip()
        config = ApproachConfig(
            min_confidence=float(
                self.declare_parameter("min_confidence", 0.65).value
            ),
            min_distance_m=float(
                self.declare_parameter("min_distance_m", 0.5).value
            ),
            max_distance_m=float(
                self.declare_parameter("max_distance_m", 2.5).value
            ),
            zone_min_x=float(
                self.declare_parameter("zone_min_x", 0.25).value
            ),
            zone_max_x=float(
                self.declare_parameter("zone_max_x", 0.75).value
            ),
            zone_min_y=float(
                self.declare_parameter("zone_min_y", 0.15).value
            ),
            zone_max_y=float(
                self.declare_parameter("zone_max_y", 0.95).value
            ),
            debounce_frames=int(
                self.declare_parameter("debounce_frames", 3).value
            ),
            cooldown_sec=float(
                self.declare_parameter("cooldown_sec", 10.0).value
            ),
            absence_reset_sec=float(
                self.declare_parameter("absence_reset_sec", 1.0).value
            ),
        )
        if not self.zone_id:
            raise ValueError("'zone_id' must not be empty")
        self.filter = HumanApproachFilter(
            config, initial_dialogue_state="UNKNOWN"
        )
        self.event_counter = 0
        self.approach_publisher = self.create_publisher(
            PersonApproach, approach_topic, 10
        )
        self.create_subscription(
            PersonDetection, detections_topic, self.on_detection, 10
        )
        state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            String,
            dialogue_state_topic,
            self.on_dialogue_state,
            state_qos,
        )
        self.create_timer(0.1, self.on_timer)
        self.get_logger().info(
            f"Human approach filter ready: detections={detections_topic} "
            f"approach={approach_topic} zone={self.zone_id} "
            f"distance_m={config.min_distance_m}..{config.max_distance_m} "
            f"normalized_zone=({config.zone_min_x},{config.zone_min_y})"
            f"..({config.zone_max_x},{config.zone_max_y}) "
            f"confidence>={config.min_confidence} "
            f"debounce_frames={config.debounce_frames} "
            f"absence_reset_sec={config.absence_reset_sec} "
            f"cooldown_sec={config.cooldown_sec}"
        )

    def on_detection(self, message: PersonDetection) -> None:
        event = self.filter.process(
            PersonObservation(
                tracking_id=message.tracking_id,
                confidence=float(message.confidence),
                distance_m=float(message.distance_m),
                normalized_x=float(message.normalized_x),
                normalized_y=float(message.normalized_y),
            ),
            now=time.monotonic(),
        )
        if event is None:
            return

        self.event_counter += 1
        approach = PersonApproach()
        approach.header = message.header
        approach.event_id = f"approach-{self.event_counter}"
        approach.tracking_id = event.tracking_id
        approach.zone_id = self.zone_id
        approach.confidence = event.confidence
        approach.distance_m = event.distance_m
        self.approach_publisher.publish(approach)

    def on_dialogue_state(self, message: String) -> None:
        self.filter.update_dialogue_state(message.data)

    def on_timer(self) -> None:
        self.filter.tick(time.monotonic())


def main(args=None) -> None:
    rclpy.init(args=args)
    node: HumanApproachNode | None = None
    try:
        node = HumanApproachNode()
        rclpy.spin(node)
    except ValueError as exc:
        rclpy.logging.get_logger("human_approach_node").fatal(str(exc))
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
