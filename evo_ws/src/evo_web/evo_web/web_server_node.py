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
import io
import time
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import UInt8MultiArray, MultiArrayDimension, String

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class CameraSnapshotHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves static files + live camera JPEG + mic ingest."""

    def __init__(self, *args, jpeg_getter=None, mic_sink=None, **kwargs):
        self.jpeg_getter = jpeg_getter
        self.mic_sink = mic_sink
        super().__init__(*args, **kwargs)

    def do_GET(self):
        # Strip query string for route matching — browsers append ?t=... cache-busters.
        route = self.path.split("?", 1)[0]
        if route == "/camera/snapshot":
            self.serve_snapshot()
        elif route == "/camera/stream":
            self.serve_mjpeg_stream()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/mic/chunk"):
            self.handle_mic_chunk()
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        # CORS preflight for dashboards served from a different origin.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Mic-Mime, X-Mic-Sample-Rate")
        self.end_headers()

    def handle_mic_chunk(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > 2_000_000:
            self.send_error(400, "Missing or oversized body")
            return
        audio = self.rfile.read(length)
        mime = self.headers.get("X-Mic-Mime", "audio/webm;codecs=opus")
        rate = self.headers.get("X-Mic-Sample-Rate", "48000")
        if self.mic_sink:
            try:
                self.mic_sink(audio, mime, rate)
            except Exception:  # don't leak to client
                pass
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
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

    def serve_mjpeg_stream(self):
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

        # Mic audio sink: publish each chunk as raw bytes on /evo/mic_chunks
        # and a short meta String on /evo/mic_meta (mime + sample rate).
        self.mic_chunks_pub = self.create_publisher(UInt8MultiArray, "/evo/mic_chunks", 20)
        self.mic_meta_pub = self.create_publisher(String, "/evo/mic_meta", 5)
        self._mic_chunk_count = 0

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
                          jpeg_getter=self.get_jpeg,
                          mic_sink=self.on_mic_chunk,
                          directory=web_dir)
        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
        self.httpd.daemon_threads = True
        self.http_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.http_thread.start()
        self.get_logger().info(f"Web dashboard: http://0.0.0.0:{self.port}")

    def on_image(self, msg: Image):
        """Convert ROS Image to JPEG and cache it."""
        try:
            now = time.monotonic()
            if self.max_fps > 0 and now - self.last_encode_time < 1.0 / self.max_fps:
                return
            self.last_encode_time = now

            encoding = msg.encoding.lower()
            h, w = msg.height, msg.width
            data = bytes(msg.data)

            if encoding in ("rgb8",):
                arr = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            elif encoding in ("bgr8",):
                arr = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)
            elif encoding in ("mono8", "8uc1"):
                arr = np.frombuffer(data, dtype=np.uint8).reshape(h, w)
            elif encoding in ("rgba8",):
                arr = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 4)
                arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            elif encoding in ("bgra8",):
                arr = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 4)
                arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            else:
                return

            if self.max_width > 0 and w > self.max_width:
                scale = self.max_width / float(w)
                arr = cv2.resize(arr, (self.max_width, int(h * scale)))

            quality = max(30, min(95, self.jpeg_quality))
            _, jpeg_buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, quality])
            with self.jpeg_lock:
                self.latest_jpeg = jpeg_buf.tobytes()
                self.latest_jpeg_seq += 1
        except Exception:
            pass

    def get_jpeg(self):
        with self.jpeg_lock:
            if self.latest_jpeg is None:
                return None
            return self.latest_jpeg_seq, self.latest_jpeg

    def on_mic_chunk(self, audio_bytes: bytes, mime: str, sample_rate: str) -> None:
        """Called from the HTTP handler thread whenever a mic chunk arrives."""
        msg = UInt8MultiArray()
        msg.layout.dim = [MultiArrayDimension(label="bytes", size=len(audio_bytes), stride=1)]
        msg.data = list(audio_bytes)
        self.mic_chunks_pub.publish(msg)
        if self._mic_chunk_count == 0:
            meta = String()
            meta.data = f"mime={mime};rate={sample_rate}"
            self.mic_meta_pub.publish(meta)
            self.get_logger().info(f"Mic stream started: {meta.data}")
        self._mic_chunk_count += 1
        if self._mic_chunk_count % 40 == 0:
            self.get_logger().info(f"Mic: {self._mic_chunk_count} chunks received")


def main():
    rclpy.init()
    node = WebServerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.httpd.shutdown()
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
