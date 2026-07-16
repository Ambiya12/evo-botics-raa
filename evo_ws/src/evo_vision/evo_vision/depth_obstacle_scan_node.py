#!/usr/bin/env python3
from __future__ import annotations

import time
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, PointCloud2, PointField

from evo_vision.image_utils import depth_image_to_meters


class DepthObstacleScanNode(Node):
    """Project calibrated depth pixels into a marking-only obstacle point cloud.

    The previous implementation published angular LaserScan bins in
    ``base_footprint`` without using camera intrinsics or camera-to-base TF.
    This node preserves the camera optical frame and lets Nav2 transform real
    XYZ points through TF, avoiding false obstacle geometry.
    """

    def __init__(self) -> None:
        super().__init__("depth_obstacle_scan_node")

        self.depth_topic = self.declare_parameter(
            "depth_topic", "/camera/depth/image_raw"
        ).value
        self.camera_info_topic = self.declare_parameter(
            "camera_info_topic", "/camera/depth/camera_info"
        ).value
        self.pointcloud_topic = self.declare_parameter(
            "pointcloud_topic", "/vision/obstacles/points"
        ).value
        self.publish_rate_hz = float(self.declare_parameter("publish_rate_hz", 5.0).value)
        self.range_min = float(self.declare_parameter("range_min", 0.15).value)
        self.range_max = float(self.declare_parameter("range_max", 2.5).value)
        self.roi_top_ratio = float(self.declare_parameter("roi_top_ratio", 0.15).value)
        self.roi_bottom_ratio = float(
            self.declare_parameter("roi_bottom_ratio", 0.72).value
        )
        self.roi_left_ratio = float(self.declare_parameter("roi_left_ratio", 0.08).value)
        self.roi_right_ratio = float(
            self.declare_parameter("roi_right_ratio", 0.92).value
        )
        self.pixel_stride = max(1, int(self.declare_parameter("pixel_stride", 8).value))
        self.frame_timeout_s = float(
            self.declare_parameter("frame_timeout_s", 0.5).value
        )

        self.latest_depth: Optional[np.ndarray] = None
        self.latest_depth_msg: Optional[Image] = None
        self.camera_info: Optional[CameraInfo] = None
        self.latest_received_monotonic = 0.0
        self.last_published_stamp: Optional[tuple[int, int]] = None

        self.pointcloud_pub = self.create_publisher(
            PointCloud2, self.pointcloud_topic, qos_profile_sensor_data
        )
        self.create_subscription(
            Image, self.depth_topic, self.on_depth, qos_profile_sensor_data
        )
        self.create_subscription(
            CameraInfo,
            self.camera_info_topic,
            self.on_camera_info,
            qos_profile_sensor_data,
        )
        self.create_timer(1.0 / max(self.publish_rate_hz, 0.1), self.publish_points)
        self.get_logger().info(
            f"Calibrated depth obstacles: {self.depth_topic} + "
            f"{self.camera_info_topic} -> {self.pointcloud_topic}"
        )

    def on_camera_info(self, msg: CameraInfo) -> None:
        if msg.k[0] <= 0.0 or msg.k[4] <= 0.0:
            self.get_logger().warning("Ignoring CameraInfo with invalid focal length.")
            return
        self.camera_info = msg

    def on_depth(self, msg: Image) -> None:
        depth = depth_image_to_meters(msg)
        if depth is None:
            return
        self.latest_depth = depth
        self.latest_depth_msg = msg
        self.latest_received_monotonic = time.monotonic()

    def publish_points(self) -> None:
        depth = self.latest_depth
        depth_msg = self.latest_depth_msg
        camera_info = self.camera_info
        if depth is None or depth_msg is None or camera_info is None:
            return
        if time.monotonic() - self.latest_received_monotonic > self.frame_timeout_s:
            return

        stamp_key = (depth_msg.header.stamp.sec, depth_msg.header.stamp.nanosec)
        if stamp_key == self.last_published_stamp:
            return
        if camera_info.width and camera_info.height:
            if int(camera_info.width) != depth.shape[1] or int(camera_info.height) != depth.shape[0]:
                self.get_logger().warning(
                    "Depth image and CameraInfo dimensions differ; obstacle frame skipped."
                )
                return

        height, width = depth.shape
        top = self._clamp_index(self.roi_top_ratio * height, 0, height - 1)
        bottom = self._clamp_index(self.roi_bottom_ratio * height, top + 1, height)
        left = self._clamp_index(self.roi_left_ratio * width, 0, width - 1)
        right = self._clamp_index(self.roi_right_ratio * width, left + 1, width)

        rows = np.arange(top, bottom, self.pixel_stride, dtype=np.int32)
        cols = np.arange(left, right, self.pixel_stride, dtype=np.int32)
        if rows.size == 0 or cols.size == 0:
            return
        pixel_u, pixel_v = np.meshgrid(cols, rows)
        z = depth[pixel_v, pixel_u]
        valid = np.isfinite(z) & (z >= self.range_min) & (z <= self.range_max)
        if not np.any(valid):
            points = np.empty((0, 3), dtype=np.float32)
        else:
            z_valid = z[valid].astype(np.float32)
            u_valid = pixel_u[valid].astype(np.float32)
            v_valid = pixel_v[valid].astype(np.float32)
            fx = float(camera_info.k[0])
            fy = float(camera_info.k[4])
            cx = float(camera_info.k[2])
            cy = float(camera_info.k[5])

            # REP-103 optical frame: +X right, +Y down, +Z forward.
            x = (u_valid - cx) * z_valid / fx
            y = (v_valid - cy) * z_valid / fy
            points = np.column_stack((x, y, z_valid)).astype(np.float32, copy=False)

        cloud = PointCloud2()
        cloud.header.stamp = depth_msg.header.stamp
        cloud.header.frame_id = depth_msg.header.frame_id or camera_info.header.frame_id
        cloud.height = 1
        cloud.width = int(points.shape[0])
        cloud.fields = [
            PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        cloud.is_bigendian = False
        cloud.point_step = 12
        cloud.row_step = cloud.point_step * cloud.width
        cloud.data = points.tobytes()
        cloud.is_dense = False
        self.pointcloud_pub.publish(cloud)
        self.last_published_stamp = stamp_key

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
