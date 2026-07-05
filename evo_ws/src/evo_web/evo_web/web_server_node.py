#!/usr/bin/env python3
"""
Minimal ROS2 node that serves the web dashboard over HTTP.

It serves static files from the package's web/ directory and also provides
a /camera/snapshot endpoint that returns the latest camera frame as JPEG.
This avoids sending raw images through rosbridge (which is slow).

Usage:
  ros2 run evo_web web_server_node
  ros2 run evo_web web_server_node --ros-args -p port:=8080
"""
import json
import time
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Image

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class CameraSnapshotHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves static files and live camera JPEGs."""

    def __init__(self, *args, camera_status_getter=None, jpeg_getter=None, **kwargs):
        self.camera_status_getter = camera_status_getter
        self.jpeg_getter = jpeg_getter
        super().__init__(*args, **kwargs)

    def do_GET(self):
        # Strip query string for route matching — browsers append ?t=... cache-busters.
        route = self.path.split("?", 1)[0]
        if route == "/camera/snapshot":
            self.serve_snapshot()
        elif route == "/camera/stream":
            self.serve_mjpeg_stream()
        elif route == "/camera/status":
            self.serve_camera_status()
        else:
            super().do_GET()

    def do_OPTIONS(self):
        # CORS preflight for camera clients served from a different origin.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def serve_snapshot(self):
        frame = self.jpeg_getter() if self.jpeg_getter else None
        jpeg = frame[1] if frame else None
        if jpeg is None:
            self.send_error(503, "No camera frame available yet")
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(jpeg)

    def serve_camera_status(self):
        status = self.camera_status_getter() if self.camera_status_getter else {}
        payload = json.dumps(status).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def serve_mjpeg_stream(self):
        # Do not return a successful, permanently blank stream. Waiting briefly
        # lets a warming camera connect; a 503 then activates the dashboard's
        # status/snapshot fallback with a useful diagnosis.
        deadline = time.monotonic() + 2.0
        frame = self.jpeg_getter() if self.jpeg_getter else None
        while frame is None and time.monotonic() < deadline:
            time.sleep(0.05)
            frame = self.jpeg_getter() if self.jpeg_getter else None
        if frame is None:
            self.send_error(503, "No camera frame available yet")
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        last_seq = -1
        try:
            while True:
                frame = self.jpeg_getter() if self.jpeg_getter else None
                if frame is not None:
                    seq, jpeg = frame
                    if seq == last_seq:
                        time.sleep(0.02)
                        continue
                    last_seq = seq
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                time.sleep(0.02)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        pass  # suppress per-request logs


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    """Allow immediate restart after the previous camera server exits."""

    allow_reuse_address = True


class WebServerNode(Node):
    def __init__(self):
        super().__init__("web_server_node")
        self.port = int(self.declare_parameter("port", 8080).value)
        self.camera_topic = self.declare_parameter(
            "camera_topic", "/camera/color/image_raw"
        ).value
        self.max_fps = float(self.declare_parameter("max_fps", 8.0).value)
        self.max_width = int(self.declare_parameter("max_width", 640).value)
        self.jpeg_quality = int(self.declare_parameter("jpeg_quality", 60).value)

        self.latest_jpeg = None
        self.latest_jpeg_seq = 0
        self.jpeg_lock = threading.Lock()
        self.last_encode_time = 0.0
        self.received_frame_count = 0
        self.encoded_frame_count = 0
        self.last_frame_time = None
        self.last_frame_encoding = None
        self.last_camera_error = None
        self.last_error_log_time = 0.0

        if HAS_CV2:
            sensor_qos = QoSProfile(
                history=QoSHistoryPolicy.KEEP_LAST,
                depth=1,
                reliability=QoSReliabilityPolicy.BEST_EFFORT,
            )
            self.create_subscription(
                Image, self.camera_topic, self.on_image, sensor_qos,
            )
            self.get_logger().info(
                f"Subscribed to camera: {self.camera_topic} "
                f"(max_fps={self.max_fps}, max_width={self.max_width}, quality={self.jpeg_quality})"
            )
        else:
            self.get_logger().warning(
                "OpenCV not found -- camera snapshot endpoint disabled. "
                "Install with: pip3 install opencv-python"
            )

        # Resolve web directory (installed share path)
        from ament_index_python.packages import get_package_share_directory
        web_dir = str(Path(get_package_share_directory("evo_web")) / "web")

        handler = partial(CameraSnapshotHandler,
                          camera_status_getter=self.get_camera_status,
                          jpeg_getter=self.get_jpeg,
                          directory=web_dir)
        self.httpd = ReusableThreadingHTTPServer(("0.0.0.0", self.port), handler)
        self.httpd.daemon_threads = True
        self.http_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.http_thread.start()
        self.get_logger().info(f"Web dashboard: http://0.0.0.0:{self.port}")

    def on_image(self, msg: Image):
        """Convert ROS Image to JPEG and cache it."""
        self.received_frame_count += 1
        self.last_frame_time = time.time()
        self.last_frame_encoding = msg.encoding
        try:
            now = time.monotonic()
            if self.max_fps > 0 and now - self.last_encode_time < 1.0 / self.max_fps:
                return
            self.last_encode_time = now

            encoding = msg.encoding.lower().replace("-", "_")
            h, w = msg.height, msg.width
            if h <= 0 or w <= 0:
                raise ValueError(f"invalid image size {w}x{h}")

            channels_by_encoding = {
                "rgb8": 3,
                "bgr8": 3,
                "rgba8": 4,
                "bgra8": 4,
                "mono8": 1,
                "8uc1": 1,
                "yuv422": 2,
                "yuv422_yuy2": 2,
                "yuyv": 2,
                "uyvy": 2,
            }
            channels = channels_by_encoding.get(encoding)
            if channels is None:
                raise ValueError(f"unsupported image encoding {msg.encoding!r}")

            packed_row_bytes = w * channels
            row_bytes = int(msg.step) if msg.step else packed_row_bytes
            if row_bytes < packed_row_bytes:
                raise ValueError(
                    f"image step {row_bytes} is smaller than {packed_row_bytes}"
                )

            data = np.frombuffer(bytes(msg.data), dtype=np.uint8)
            required_bytes = h * row_bytes
            if data.size < required_bytes:
                raise ValueError(
                    f"image payload has {data.size} bytes; expected at least {required_bytes}"
                )

            # ROS Image.step may include row padding. Slice it away before
            # reshaping so valid camera frames are not silently discarded.
            packed = data[:required_bytes].reshape(h, row_bytes)[:, :packed_row_bytes]
            if channels == 1:
                arr = packed.reshape(h, w)
            else:
                arr = packed.reshape(h, w, channels)

            if encoding == "rgb8":
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            elif encoding == "rgba8":
                arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            elif encoding == "bgra8":
                arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            elif encoding in ("yuv422", "yuv422_yuy2", "yuyv"):
                arr = cv2.cvtColor(arr, cv2.COLOR_YUV2BGR_YUY2)
            elif encoding == "uyvy":
                arr = cv2.cvtColor(arr, cv2.COLOR_YUV2BGR_UYVY)

            if self.max_width > 0 and w > self.max_width:
                scale = self.max_width / float(w)
                arr = cv2.resize(arr, (self.max_width, int(h * scale)))

            quality = max(30, min(95, self.jpeg_quality))
            encoded, jpeg_buf = cv2.imencode(
                ".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            if not encoded:
                raise ValueError("OpenCV failed to encode the camera frame")
            with self.jpeg_lock:
                self.latest_jpeg = jpeg_buf.tobytes()
                self.latest_jpeg_seq += 1
                self.encoded_frame_count += 1
                self.last_camera_error = None
        except Exception as exc:
            self.last_camera_error = str(exc)
            now = time.monotonic()
            if now - self.last_error_log_time >= 5.0:
                self.get_logger().error(
                    f"Camera frame rejected on {self.camera_topic}: {exc}"
                )
                self.last_error_log_time = now

    def get_jpeg(self):
        with self.jpeg_lock:
            if self.latest_jpeg is None:
                return None
            return self.latest_jpeg_seq, self.latest_jpeg

    def get_camera_status(self):
        with self.jpeg_lock:
            return {
                "available": self.latest_jpeg is not None,
                "topic": self.camera_topic,
                "opencv_available": HAS_CV2,
                "received_frames": self.received_frame_count,
                "encoded_frames": self.encoded_frame_count,
                "last_frame_at": self.last_frame_time,
                "last_encoding": self.last_frame_encoding,
                "error": self.last_camera_error,
            }

def main():
    rclpy.init()
    node = WebServerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.httpd.shutdown()
        node.httpd.server_close()
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
