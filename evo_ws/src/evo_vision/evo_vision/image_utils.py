from __future__ import annotations

import json
from typing import Optional

import numpy as np
from sensor_msgs.msg import Image


_ENCODING_CHANNELS: dict[str, int] = {
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


def encoding_channels(encoding: str) -> int | None:
    return _ENCODING_CHANNELS.get(encoding.lower().replace("-", "_"))


def color_image_to_bgr(msg: Image) -> Optional[np.ndarray]:
    """Convert common ROS color image encodings to an OpenCV BGR image."""
    try:
        import cv2
    except ImportError:
        return None

    encoding = msg.encoding.lower()
    height = int(msg.height)
    width = int(msg.width)
    data = bytes(msg.data)

    try:
        if encoding == "bgr8":
            return np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)
        if encoding == "rgb8":
            image = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if encoding in ("mono8", "8uc1"):
            image = np.frombuffer(data, dtype=np.uint8).reshape(height, width)
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if encoding == "rgba8":
            image = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 4)
            return cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        if encoding == "bgra8":
            image = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 4)
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    except ValueError:
        return None

    return None


def color_image_to_bgr_respecting_step(msg: Image) -> Optional[np.ndarray]:
    """Convert a ROS color image to BGR, respecting row padding in msg.step."""
    try:
        import cv2
    except ImportError:
        return None

    encoding = msg.encoding.lower().replace("-", "_")
    h, w = msg.height, msg.width
    if h <= 0 or w <= 0:
        return None
    channels = encoding_channels(encoding)
    if channels is None:
        return None

    packed_row_bytes = w * channels
    row_bytes = int(msg.step) if msg.step else packed_row_bytes
    if row_bytes < packed_row_bytes:
        return None

    data = np.frombuffer(bytes(msg.data), dtype=np.uint8)
    required_bytes = h * row_bytes
    if data.size < required_bytes:
        return None

    packed = data[:required_bytes].reshape(h, row_bytes)[:, :packed_row_bytes]
    if channels == 1:
        arr = packed.reshape(h, w)
    else:
        arr = packed.reshape(h, w, channels)

    return _to_bgr(arr, encoding)


def _to_bgr(arr: np.ndarray, encoding: str) -> Optional[np.ndarray]:
    try:
        import cv2
    except ImportError:
        return None

    if encoding in ("bgr8", "mono8", "8uc1"):
        return arr
    if encoding == "rgb8":
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    if encoding == "rgba8":
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    if encoding == "bgra8":
        return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
    if encoding in ("yuv422", "yuv422_yuy2", "yuyv"):
        return cv2.cvtColor(arr, cv2.COLOR_YUV2BGR_YUY2)
    if encoding == "uyvy":
        return cv2.cvtColor(arr, cv2.COLOR_YUV2BGR_UYVY)
    return None


def depth_image_to_meters(msg: Image) -> Optional[np.ndarray]:
    encoding = msg.encoding.lower()
    height = int(msg.height)
    width = int(msg.width)
    if height <= 0 or width <= 0:
        return None

    data = bytes(msg.data)
    step_bytes = int(msg.step) if msg.step else 0

    try:
        if encoding == "16uc1":
            raw = np.frombuffer(data, dtype=np.uint16)
            row_stride = step_bytes // 2 if step_bytes >= width * 2 else width
            if raw.size >= height * row_stride:
                return raw.reshape(height, row_stride)[:, :width].astype(np.float32) * 0.001
            if raw.size >= height * width:
                return raw.reshape(height, width).astype(np.float32) * 0.001
        if encoding == "32fc1":
            raw = np.frombuffer(data, dtype=np.float32)
            row_stride = step_bytes // 4 if step_bytes >= width * 4 else width
            if raw.size >= height * row_stride:
                return raw.reshape(height, row_stride)[:, :width]
            if raw.size >= height * width:
                return raw.reshape(height, width)
        if encoding in ("mono16", "16sc1"):
            raw = np.frombuffer(data, dtype=np.int16)
            row_stride = step_bytes // 2 if step_bytes >= width * 2 else width
            if raw.size >= height * row_stride:
                return raw.reshape(height, row_stride)[:, :width].astype(np.float32) * 0.001
            if raw.size >= height * width:
                return raw.reshape(height, width).astype(np.float32) * 0.001
    except ValueError:
        return None

    return None


def color_image_stamp_seconds(msg: Image) -> float:
    return float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) / 1_000_000_000.0
