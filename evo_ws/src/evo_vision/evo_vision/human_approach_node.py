from __future__ import annotations

import time

from evo_reception_interfaces.msg import PersonApproach, PersonDetection
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String

from evo_vision.human_approach import (
    ApproachConfig,
    HumanApproachFilter,
    PersonObservation,
    detection_age_seconds,
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
        presence_topic = str(
            self.declare_parameter(
                "presence_topic", "/vision/people/presence"
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
        self.detection_max_age_sec = float(
            self.declare_parameter("detection_max_age_sec", 1.0).value
        )
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
                self.declare_parameter("absence_reset_sec", 10.0).value
            ),
        )
        if not self.zone_id:
            raise ValueError("'zone_id' must not be empty")
        if self.detection_max_age_sec <= 0.0:
            raise ValueError("'detection_max_age_sec' must be greater than zero")
        self.filter = HumanApproachFilter(
            config, initial_dialogue_state="UNKNOWN"
        )
        self.event_counter = 0
        self.approach_publisher = self.create_publisher(
            PersonApproach, approach_topic, 10
        )
        presence_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.presence_publisher = self.create_publisher(
            Bool, presence_topic, presence_qos
        )
        self.presence_state: bool | None = None
        self.warned_zero_detection_stamp = False
        self.last_stale_log_at = 0.0
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
        self.publish_presence(False)
        self.get_logger().info(
            f"Human approach filter ready: detections={detections_topic} "
            f"approach={approach_topic} presence={presence_topic} "
            f"zone={self.zone_id} "
            f"distance_m={config.min_distance_m}..{config.max_distance_m} "
            f"normalized_zone=({config.zone_min_x},{config.zone_min_y})"
            f"..({config.zone_max_x},{config.zone_max_y}) "
            f"confidence>={config.min_confidence} "
            f"debounce_frames={config.debounce_frames} "
            f"detection_max_age_sec={self.detection_max_age_sec} "
            f"absence_reset_sec={config.absence_reset_sec} "
            f"cooldown_sec={config.cooldown_sec}"
        )

    def on_detection(self, message: PersonDetection) -> None:
        now = time.monotonic()
        stamp_sec = (
            float(message.header.stamp.sec)
            + float(message.header.stamp.nanosec) / 1_000_000_000.0
        )
        if stamp_sec == 0.0:
            if not self.warned_zero_detection_stamp:
                self.warned_zero_detection_stamp = True
                self.get_logger().warning(
                    "Person detection has no timestamp; accepting it for "
                    "compatibility, but freshness cannot be verified"
                )
        else:
            detection_age_sec = detection_age_seconds(
                stamp_sec,
                self.get_clock().now().nanoseconds / 1_000_000_000.0
            )
            assert detection_age_sec is not None
            if detection_age_sec > self.detection_max_age_sec:
                if now - self.last_stale_log_at >= 1.0:
                    self.last_stale_log_at = now
                    self.get_logger().warning(
                        "Rejected stale person detection: "
                        f"age_sec={detection_age_sec:.3f} "
                        f"max_age_sec={self.detection_max_age_sec:.3f} "
                        f"confidence={float(message.confidence):.3f}"
                    )
                return

        observation = PersonObservation(
            tracking_id=message.tracking_id,
            confidence=float(message.confidence),
            distance_m=float(message.distance_m),
            normalized_x=float(message.normalized_x),
            normalized_y=float(message.normalized_y),
        )
        valid = self.filter.is_valid_observation(observation)
        self.get_logger().debug(
            "Person detection evaluated: "
            f"valid={str(valid).lower()} "
            f"confidence={observation.confidence:.3f} "
            f"distance_m={observation.distance_m:.3f} "
            f"position=({observation.normalized_x:.3f},"
            f"{observation.normalized_y:.3f})"
        )
        event = self.filter.process(observation, now=now)
        self.publish_presence(self.filter.is_person_present(now))
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
        self.get_logger().info(
            "Published debounced visitor approach: "
            f"event_id={approach.event_id} confidence={event.confidence:.3f} "
            f"distance_m={event.distance_m:.3f}"
        )

    def on_dialogue_state(self, message: String) -> None:
        self.filter.update_dialogue_state(message.data)

    def on_timer(self) -> None:
        now = time.monotonic()
        self.filter.tick(now)
        self.publish_presence(self.filter.is_person_present(now))

    def publish_presence(self, present: bool) -> None:
        if present == self.presence_state:
            return
        self.presence_state = present
        self.presence_publisher.publish(Bool(data=present))
        self.get_logger().info(
            f"Human presence changed: present={str(present).lower()}"
        )


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
