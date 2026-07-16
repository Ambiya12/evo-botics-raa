#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
from evo_reception_interfaces.msg import PersonDetection
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

from evo_vision.image_utils import color_image_to_bgr, depth_image_to_meters
from evo_vision.person_detector import (
    LetterboxTransform,
    PresenceTracker,
    decode_yolov5_people,
    estimate_person_distance,
    non_max_suppression,
    select_primary_person,
)


class ObjectDetectorNode(Node):
    """Publish one depth-qualified primary person from real camera frames."""

    def __init__(self) -> None:
        super().__init__("object_detector_node")
        self.color_topic = str(
            self.declare_parameter(
                "color_topic", "/camera/color/image_raw"
            ).value
        )
        self.depth_topic = str(
            self.declare_parameter(
                "depth_topic", "/camera/depth/image_raw"
            ).value
        )
        self.detections_topic = str(
            self.declare_parameter(
                "detections_topic", "/vision/people/detections"
            ).value
        )
        self.status_topic = str(
            self.declare_parameter(
                "status_topic", "/vision/people/detector_status"
            ).value
        )
        self.model_path = Path(
            str(self.declare_parameter("model_path", "").value)
        ).expanduser()
        self.input_size = int(
            self.declare_parameter("input_size", 640).value
        )
        self.confidence_threshold = float(
            self.declare_parameter("confidence_threshold", 0.55).value
        )
        self.nms_threshold = float(
            self.declare_parameter("nms_threshold", 0.45).value
        )
        self.max_fps = float(
            self.declare_parameter("max_fps", 5.0).value
        )
        self.depth_sync_tolerance_sec = float(
            self.declare_parameter("depth_sync_tolerance_sec", 0.5).value
        )
        self.depth_timeout_sec = float(
            self.declare_parameter("depth_timeout_sec", 0.75).value
        )
        self.depth_roi_fraction = float(
            self.declare_parameter("depth_roi_fraction", 0.35).value
        )
        self.min_depth_m = float(
            self.declare_parameter("min_depth_m", 0.2).value
        )
        self.max_depth_m = float(
            self.declare_parameter("max_depth_m", 5.0).value
        )
        self.presence_topic = str(
            self.declare_parameter(
                "presence_topic", "/vision/people/presence"
            ).value
        )
        self.presence_hold_sec = float(
            self.declare_parameter("presence_hold_sec", 5.0).value
        )
        self.presence_release_sec = float(
            self.declare_parameter("presence_release_sec", 1.0).value
        )
        self.health_topic = str(
            self.declare_parameter(
                "health_topic", "/vision/people/health"
            ).value
        )
        self._validate_configuration()

        try:
            self.network = cv2.dnn.readNetFromONNX(str(self.model_path))
            self.network.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.network.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        except cv2.error as exc:
            raise ValueError(
                f"Could not load person detector model {self.model_path}: {exc}"
            ) from exc

        self.latest_depth: np.ndarray | None = None
        self.latest_depth_stamp = 0.0
        self.latest_depth_received_at = 0.0
        self.last_inference_at = 0.0
        self.last_status = ""
        self.presence_tracker = PresenceTracker(
            hold_sec=self.presence_hold_sec,
            release_sec=self.presence_release_sec,
        )
        self.last_detection_at = 0.0
        self._inference_times: list[float] = []
        self._depth_sync_ok = False
        self._model_loaded = True

        self.detection_publisher = self.create_publisher(
            PersonDetection,
            self.detections_topic,
            10,
        )
        status_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.status_publisher = self.create_publisher(
            String,
            self.status_topic,
            status_qos,
        )
        presence_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.presence_publisher = self.create_publisher(
            Bool,
            self.presence_topic,
            presence_qos,
        )
        self.health_publisher = self.create_publisher(
            String,
            self.health_topic,
            presence_qos,
        )
        self.create_subscription(
            Image,
            self.depth_topic,
            self.on_depth,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Image,
            self.color_topic,
            self.on_color,
            qos_profile_sensor_data,
        )
        self.publish_status("ready", "Person detector is ready.")
        self.get_logger().info(
            f"YOLOv5 person detector: color={self.color_topic} "
            f"depth={self.depth_topic} detections={self.detections_topic} "
            f"model={self.model_path} max_fps={self.max_fps:.1f}"
        )

    def _validate_configuration(self) -> None:
        errors: list[str] = []
        if not self.model_path.is_file():
            errors.append(f"model_path does not exist: {self.model_path}")
        if self.input_size < 32:
            errors.append("input_size must be at least 32")
        if not 0.0 < self.confidence_threshold <= 1.0:
            errors.append("confidence_threshold must be between 0 and 1")
        if not 0.0 <= self.nms_threshold <= 1.0:
            errors.append("nms_threshold must be between 0 and 1")
        if self.max_fps <= 0.0:
            errors.append("max_fps must be greater than zero")
        if self.depth_sync_tolerance_sec < 0.0:
            errors.append("depth_sync_tolerance_sec must be non-negative")
        if self.depth_timeout_sec <= 0.0:
            errors.append("depth_timeout_sec must be greater than zero")
        if not 0.0 < self.depth_roi_fraction <= 1.0:
            errors.append("depth_roi_fraction must be between 0 and 1")
        if self.min_depth_m < 0.0 or self.max_depth_m <= self.min_depth_m:
            errors.append("max_depth_m must be greater than min_depth_m")
        if errors:
            raise ValueError(
                "Invalid person detector configuration: " + "; ".join(errors)
            )

    def on_depth(self, message: Image) -> None:
        depth = depth_image_to_meters(message)
        if depth is None:
            self.publish_status(
                "depth_error",
                f"Unsupported depth encoding: {message.encoding}",
            )
            return
        self.latest_depth = depth
        self.latest_depth_stamp = self._stamp_seconds(message)
        self.latest_depth_received_at = time.monotonic()

    def on_color(self, message: Image) -> None:
        now = time.monotonic()
        if now - self.last_inference_at < 1.0 / self.max_fps:
            return
        self.last_inference_at = now
        self._inference_times.append(now)
        self._depth_sync_ok = (
            self.latest_depth is not None
            and now - self.latest_depth_received_at <= self.depth_timeout_sec
        )

        if (
            self.latest_depth is None
            or now - self.latest_depth_received_at > self.depth_timeout_sec
        ):
            self.publish_status("waiting_for_depth", "Fresh depth data is required.")
            self.publish_health()
            return
        color_stamp = self._stamp_seconds(message)
        if (
            color_stamp > 0.0
            and self.latest_depth_stamp > 0.0
            and abs(color_stamp - self.latest_depth_stamp)
            > self.depth_sync_tolerance_sec
        ):
            self._depth_sync_ok = False
            self.publish_status(
                "depth_out_of_sync",
                "Color and depth frames are outside the synchronization tolerance.",
            )
            self.publish_health()
            return
        self._depth_sync_ok = True

        image = color_image_to_bgr(message)
        if image is None:
            self.publish_status(
                "color_error",
                f"Unsupported color encoding: {message.encoding}",
            )
            self.publish_health()
            return

        try:
            blob, transform = self._make_blob(image)
            self.network.setInput(blob)
            output = self.network.forward()
            detections = decode_yolov5_people(
                output,
                transform,
                self.confidence_threshold,
            )
            detections = non_max_suppression(
                detections,
                self.nms_threshold,
            )
        except (cv2.error, ValueError) as exc:
            self.get_logger().error(f"Person inference failed: {exc}")
            self.publish_status("inference_error", "Person inference failed.")
            self.publish_health()
            return

        primary = select_primary_person(detections)
        if primary is None:
            self._update_presence(False, now)
            self.publish_status("active", "No person detected.")
            self.publish_health()
            return
        distance_m = estimate_person_distance(
            self.latest_depth,
            primary,
            color_width=image.shape[1],
            color_height=image.shape[0],
            roi_fraction=self.depth_roi_fraction,
            min_distance_m=self.min_depth_m,
            max_distance_m=self.max_depth_m,
        )
        if distance_m is None:
            self.publish_status(
                "depth_unavailable",
                "Person detected without a reliable depth measurement.",
            )
            self.publish_health()
            return

        center_x, center_y = primary.center
        detection = PersonDetection()
        detection.header = message.header
        detection.tracking_id = "primary-person"
        detection.confidence = float(primary.confidence)
        detection.distance_m = distance_m
        detection.normalized_x = float(center_x / image.shape[1])
        detection.normalized_y = float(center_y / image.shape[0])
        self.detection_publisher.publish(detection)
        self.last_detection_at = now
        self._update_presence(True, now)
        self.publish_status("detecting", "Depth-qualified person detected.")
        self.publish_health()

    def _update_presence(self, person_seen: bool, now: float) -> None:
        change = self.presence_tracker.update(person_seen, now)
        if change is True:
            self.presence_publisher.publish(Bool(data=True))
        elif change is False:
            self.presence_publisher.publish(Bool(data=False))

    def _make_blob(
        self,
        image: np.ndarray,
    ) -> tuple[np.ndarray, LetterboxTransform]:
        source_height, source_width = image.shape[:2]
        scale = min(
            self.input_size / source_width,
            self.input_size / source_height,
        )
        resized_width = max(1, int(round(source_width * scale)))
        resized_height = max(1, int(round(source_height * scale)))
        resized = cv2.resize(
            image,
            (resized_width, resized_height),
            interpolation=cv2.INTER_LINEAR,
        )
        pad_x = (self.input_size - resized_width) // 2
        pad_y = (self.input_size - resized_height) // 2
        canvas = np.full(
            (self.input_size, self.input_size, 3),
            114,
            dtype=np.uint8,
        )
        canvas[
            pad_y:pad_y + resized_height,
            pad_x:pad_x + resized_width,
        ] = resized
        blob = cv2.dnn.blobFromImage(
            canvas,
            scalefactor=1.0 / 255.0,
            size=(self.input_size, self.input_size),
            swapRB=True,
            crop=False,
        )
        return blob, LetterboxTransform(
            scale=scale,
            pad_x=float(pad_x),
            pad_y=float(pad_y),
            source_width=source_width,
            source_height=source_height,
        )

    def publish_health(self) -> None:
        now = time.monotonic()
        cutoff = now - 5.0
        self._inference_times = [t for t in self._inference_times if t >= cutoff]
        fps = len(self._inference_times) / 5.0 if self._inference_times else 0.0
        last_detection_age = (
            now - self.last_detection_at if self.last_detection_at > 0.0 else -1.0
        )
        payload = String()
        payload.data = json.dumps(
            {
                "fps": round(fps, 2),
                "last_detection_age_sec": round(last_detection_age, 2),
                "depth_sync_ok": self._depth_sync_ok,
                "model_loaded": self._model_loaded,
                "presence_active": self.presence_tracker.active,
            },
            separators=(",", ":"),
        )
        self.health_publisher.publish(payload)

    def publish_status(self, state: str, message: str) -> None:
        if state == self.last_status:
            return
        self.last_status = state
        payload = String()
        payload.data = json.dumps(
            {"state": state, "message": message},
            separators=(",", ":"),
        )
        self.status_publisher.publish(payload)

    @staticmethod
    def _stamp_seconds(message: Image) -> float:
        return (
            float(message.header.stamp.sec)
            + float(message.header.stamp.nanosec) / 1_000_000_000.0
        )


def main() -> None:
    rclpy.init()
    node: ObjectDetectorNode | None = None
    try:
        node = ObjectDetectorNode()
        rclpy.spin(node)
    except ValueError as exc:
        rclpy.logging.get_logger("object_detector_node").fatal(str(exc))
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
