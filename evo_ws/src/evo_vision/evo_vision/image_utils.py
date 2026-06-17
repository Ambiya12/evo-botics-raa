from __future__ import annotations

from typing import Optional

import numpy as np
from sensor_msgs.msg import Image


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


def depth_image_to_meters(msg: Image) -> Optional[np.ndarray]:
    """Convert common ROS depth image encodings to float32 meters."""
    encoding = msg.encoding.lower()
    height = int(msg.height)
    width = int(msg.width)
    data = bytes(msg.data)

    try:
        if encoding in ("16uc1", "mono16"):
            depth_mm = np.frombuffer(data, dtype=np.uint16).reshape(height, width)
            depth = depth_mm.astype(np.float32) / 1000.0
            depth[depth_mm == 0] = np.nan
            return depth
        if encoding == "32fc1":
            return np.frombuffer(data, dtype=np.float32).reshape(height, width).copy()
    except ValueError:
        return None

    return None
