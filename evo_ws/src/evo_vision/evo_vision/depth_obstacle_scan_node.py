#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, LaserScan

from evo_vision.image_utils import depth_image_to_meters


class DepthObstacleScanNode(Node):
    def __init__(self) -> None:
        super().__init__("depth_obstacle_scan_node")

        self.depth_topic = self.declare_parameter(
            "depth_topic", "/camera/depth/image_raw"
        ).value
        self.scan_topic = self.declare_parameter(
            "scan_topic", "/vision/obstacles/scan"
        ).value
        self.frame_id = self.declare_parameter("frame_id", "base_footprint").value
        self.publish_rate_hz = float(self.declare_parameter("publish_rate_hz", 5.0).value)
        self.horizontal_fov_deg = float(
            self.declare_parameter("horizontal_fov_deg", 60.0).value
        )
        self.scan_bins = int(self.declare_parameter("scan_bins", 61).value)
        self.range_min = float(self.declare_parameter("range_min", 0.15).value)
        self.range_max = float(self.declare_parameter("range_max", 2.5).value)
        self.roi_top_ratio = float(self.declare_parameter("roi_top_ratio", 0.35).value)
        self.roi_bottom_ratio = float(
            self.declare_parameter("roi_bottom_ratio", 0.85).value
        )
        self.roi_left_ratio = float(self.declare_parameter("roi_left_ratio", 0.10).value)
        self.roi_right_ratio = float(
            self.declare_parameter("roi_right_ratio", 0.90).value
        )
        self.depth_percentile = float(
            self.declare_parameter("depth_percentile", 10.0).value
        )

        self.latest_depth: Optional[np.ndarray] = None
        self.latest_stamp = None
        self.frames_seen = 0
        self.unsupported_frames = 0

        self.scan_pub = self.create_publisher(LaserScan, self.scan_topic, 10)
        self.create_subscription(
            Image, self.depth_topic, self.on_depth, qos_profile_sensor_data
        )
        self.create_timer(1.0 / max(self.publish_rate_hz, 0.1), self.publish_scan)
        self.get_logger().info(
            f"Depth obstacle scan subscribed to {self.depth_topic}, publishing {self.scan_topic}"
        )

    def on_depth(self, msg: Image) -> None:
        depth = depth_image_to_meters(msg)
        if depth is None:
            self.unsupported_frames += 1
            return
        self.frames_seen += 1
        self.latest_depth = depth
        self.latest_stamp = msg.header.stamp

    def publish_scan(self) -> None:
        depth = self.latest_depth
        if depth is None:
            return

        height, width = depth.shape
        top = self._clamp_index(self.roi_top_ratio * height, 0, height - 1)
        bottom = self._clamp_index(self.roi_bottom_ratio * height, top + 1, height)
        left = self._clamp_index(self.roi_left_ratio * width, 0, width - 1)
        right = self._clamp_index(self.roi_right_ratio * width, left + 1, width)
        roi = depth[top:bottom, left:right]

        bins = max(3, self.scan_bins)
        if bins % 2 == 0:
            bins += 1

        ranges = []
        for section in np.array_split(roi, bins, axis=1):
            valid = section[np.isfinite(section)]
            valid = valid[(valid >= self.range_min) & (valid <= self.range_max)]
            if valid.size == 0:
                ranges.append(math.inf)
            else:
                ranges.append(float(np.percentile(valid, self.depth_percentile)))

        scan = LaserScan()
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.header.frame_id = self.frame_id
        fov_rad = math.radians(self.horizontal_fov_deg)
        scan.angle_min = -fov_rad / 2.0
        scan.angle_max = fov_rad / 2.0
        scan.angle_increment = fov_rad / float(max(1, bins - 1))
        scan.time_increment = 0.0
        scan.scan_time = 1.0 / max(self.publish_rate_hz, 0.1)
        scan.range_min = self.range_min
        scan.range_max = self.range_max
        scan.ranges = ranges
        self.scan_pub.publish(scan)

    @staticmethod
    def _clamp_index(value: float, min_value: int, max_value: int) -> int:
        return max(min_value, min(int(round(value)), max_value))


def main() -> None:
    rclpy.init()
    node = DepthObstacleScanNode()
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
