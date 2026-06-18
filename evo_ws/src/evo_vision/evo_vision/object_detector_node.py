#!/usr/bin/env python3
from __future__ import annotations

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ObjectDetectorNode(Node):
    """Placeholder for a future model-backed object detector."""

    def __init__(self) -> None:
        super().__init__("object_detector_node")
        self.detections_topic = self.declare_parameter(
            "detections_topic", "/vision/objects/detections"
        ).value
        self.model_path = self.declare_parameter("model_path", "").value
        self.enabled = bool(self.declare_parameter("enabled", False).value)
        self.pub = self.create_publisher(String, self.detections_topic, 10)
        self.create_timer(5.0, self.publish_status)
        self.get_logger().info(
            "Object detector scaffold started; no model runtime is enabled in V1"
        )

    def publish_status(self) -> None:
        msg = String()
        msg.data = json.dumps(
            {
                "node": self.get_name(),
                "enabled": self.enabled,
                "model_path": self.model_path,
                "detections": [],
                "status": "scaffold_only",
            },
            separators=(",", ":"),
        )
        self.pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = ObjectDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
