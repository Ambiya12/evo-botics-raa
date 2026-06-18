#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any, Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String

from evo_vision.image_utils import color_image_to_bgr

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except ImportError:
    pyzbar_decode = None


def opencv_has_quirc() -> bool:
    if cv2 is None:
        return False
    try:
        build_info = cv2.getBuildInformation().lower()
    except Exception:
        return False
    if "quirc" not in build_info:
        return False
    return "quirc:                   yes" in build_info or "quirc: yes" in build_info


class QrScannerNode(Node):
    def __init__(self) -> None:
        super().__init__("qr_scanner_node")

        self.camera_topic = self.declare_parameter(
            "camera_topic", "/camera/color/image_raw"
        ).value
        self.detections_topic = self.declare_parameter(
            "detections_topic", "/vision/qr/detections"
        ).value
        self.status_topic = self.declare_parameter(
            "status_topic", "/vision/qr/status"
        ).value
        self.cooldown_sec = float(self.declare_parameter("cooldown_sec", 2.0).value)
        self.min_scan_interval_sec = float(
            self.declare_parameter("min_scan_interval_sec", 0.25).value
        )
        self.max_width = int(self.declare_parameter("max_width", 640).value)
        self.decoder_backend = self.declare_parameter("decoder_backend", "auto").value

        self.opencv_decoder_available = opencv_has_quirc()
        self.pyzbar_available = pyzbar_decode is not None
        self.detector = cv2.QRCodeDetector() if self.opencv_decoder_available else None
        self.last_value = ""
        self.last_emit_ns = 0
        self.last_scan_ns = 0
        self.frames_seen = 0
        self.decode_count = 0
        self.unsupported_frames = 0
        self.decode_errors = 0

        self.detections_pub = self.create_publisher(String, self.detections_topic, 10)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        sensor_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )
        self.create_subscription(
            Image, self.camera_topic, self.on_image, sensor_qos
        )
        self.create_timer(2.0, self.publish_status)

        if self.selected_backend() is None:
            self.get_logger().error(
                "No QR decoder is available. Install pyzbar/zbar in the robot container "
                "or use an OpenCV build linked with QUIRC."
            )
        else:
            self.get_logger().info(
                f"QR scanner subscribed to {self.camera_topic} using {self.selected_backend()}"
            )

    def selected_backend(self) -> Optional[str]:
        requested = str(self.decoder_backend).lower()
        if requested in ("pyzbar", "zbar") and self.pyzbar_available:
            return "pyzbar"
        if requested == "opencv" and self.opencv_decoder_available:
            return "opencv"
        if requested == "auto":
            if self.pyzbar_available:
                return "pyzbar"
            if self.opencv_decoder_available:
                return "opencv"
        return None

    def on_image(self, msg: Image) -> None:
        self.frames_seen += 1
        backend = self.selected_backend()
        if backend is None:
            return

        now_ns = self.get_clock().now().nanoseconds
        if now_ns - self.last_scan_ns < int(self.min_scan_interval_sec * 1e9):
            return
        self.last_scan_ns = now_ns

        image = color_image_to_bgr(msg)
        if image is None:
            self.unsupported_frames += 1
            return

        if self.max_width > 0 and image.shape[1] > self.max_width and cv2 is not None:
            scale = self.max_width / float(image.shape[1])
            image = cv2.resize(image, (self.max_width, int(image.shape[0] * scale)))

        decoded_text = self.decode_qr(image, backend)
        if decoded_text is None:
            return

        if not decoded_text:
            return

        if (
            decoded_text == self.last_value
            and now_ns - self.last_emit_ns < int(self.cooldown_sec * 1e9)
        ):
            return

        self.last_value = decoded_text
        self.last_emit_ns = now_ns
        self.decode_count += 1

        parsed: Any = None
        is_json = False
        try:
            parsed = json.loads(decoded_text)
            is_json = True
        except json.JSONDecodeError:
            parsed = None

        event = {
            "decoded_text": decoded_text,
            "stamp": {"sec": int(msg.header.stamp.sec), "nanosec": int(msg.header.stamp.nanosec)},
            "camera_topic": self.camera_topic,
            "decoder_backend": backend,
            "is_json": is_json,
            "parsed_type": parsed.get("type") if isinstance(parsed, dict) else None,
            "has_uuid": isinstance(parsed, dict) and bool(parsed.get("uuid")),
        }
        out = String()
        out.data = json.dumps(event, separators=(",", ":"))
        self.detections_pub.publish(out)
        self.get_logger().info("QR detected and published")

    def decode_qr(self, image, backend: str) -> Optional[str]:
        try:
            if backend == "pyzbar":
                if cv2 is not None:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                decoded = pyzbar_decode(image)
                if not decoded:
                    return ""
                return decoded[0].data.decode("utf-8", errors="replace")

            if backend == "opencv" and self.detector is not None:
                decoded_text, _, _ = self.detector.detectAndDecode(image)
                return decoded_text
        except Exception as exc:
            self.decode_errors += 1
            if self.decode_errors <= 3 or self.decode_errors % 20 == 0:
                self.get_logger().warning(f"QR decode failed using {backend}: {exc}")
        return None

    def publish_status(self) -> None:
        status = {
            "node": self.get_name(),
            "camera_topic": self.camera_topic,
            "frames_seen": self.frames_seen,
            "decode_count": self.decode_count,
            "unsupported_frames": self.unsupported_frames,
            "decode_errors": self.decode_errors,
            "selected_backend": self.selected_backend(),
            "pyzbar_available": self.pyzbar_available,
            "opencv_available": cv2 is not None,
            "opencv_quirc_available": self.opencv_decoder_available,
        }
        msg = String()
        msg.data = json.dumps(status, separators=(",", ":"))
        self.status_pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = QrScannerNode()
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
