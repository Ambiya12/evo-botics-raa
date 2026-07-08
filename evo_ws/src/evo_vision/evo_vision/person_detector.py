from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class DetectionBox:
    x: float
    y: float
    width: float
    height: float
    confidence: float

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)


@dataclass(frozen=True)
class LetterboxTransform:
    scale: float
    pad_x: float
    pad_y: float
    source_width: int
    source_height: int


def decode_yolov5_people(
    output: np.ndarray,
    transform: LetterboxTransform,
    confidence_threshold: float,
    person_class_id: int = 0,
) -> list[DetectionBox]:
    """Decode a YOLOv5 detection tensor into source-image person boxes."""
    values = np.asarray(output)
    if values.ndim == 3 and values.shape[0] == 1:
        values = values[0]
    if values.ndim != 2 or values.shape[1] <= 5 + person_class_id:
        return []
    if transform.scale <= 0.0:
        return []

    detections: list[DetectionBox] = []
    for row in values:
        objectness = float(row[4])
        class_score = float(row[5 + person_class_id])
        confidence = objectness * class_score
        if not math.isfinite(confidence) or confidence < confidence_threshold:
            continue

        center_x, center_y, width, height = (float(value) for value in row[:4])
        left = (center_x - width / 2.0 - transform.pad_x) / transform.scale
        top = (center_y - height / 2.0 - transform.pad_y) / transform.scale
        right = (center_x + width / 2.0 - transform.pad_x) / transform.scale
        bottom = (center_y + height / 2.0 - transform.pad_y) / transform.scale

        left = min(max(left, 0.0), float(transform.source_width))
        right = min(max(right, 0.0), float(transform.source_width))
        top = min(max(top, 0.0), float(transform.source_height))
        bottom = min(max(bottom, 0.0), float(transform.source_height))
        if right <= left or bottom <= top:
            continue
        detections.append(
            DetectionBox(
                x=left,
                y=top,
                width=right - left,
                height=bottom - top,
                confidence=confidence,
            )
        )
    return detections


def non_max_suppression(
    detections: list[DetectionBox],
    iou_threshold: float,
) -> list[DetectionBox]:
    """Suppress overlapping boxes using deterministic confidence ordering."""
    remaining = sorted(
        detections,
        key=lambda detection: (-detection.confidence, -detection.area),
    )
    selected: list[DetectionBox] = []
    while remaining:
        candidate = remaining.pop(0)
        selected.append(candidate)
        remaining = [
            detection
            for detection in remaining
            if intersection_over_union(candidate, detection) <= iou_threshold
        ]
    return selected


def intersection_over_union(first: DetectionBox, second: DetectionBox) -> float:
    left = max(first.x, second.x)
    top = max(first.y, second.y)
    right = min(first.x + first.width, second.x + second.width)
    bottom = min(first.y + first.height, second.y + second.height)
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = first.area + second.area - intersection
    return intersection / union if union > 0.0 else 0.0


def select_primary_person(
    detections: list[DetectionBox],
) -> DetectionBox | None:
    """Prefer the largest visible person, then confidence, for stable reception."""
    if not detections:
        return None
    return max(detections, key=lambda detection: (detection.area, detection.confidence))


def estimate_person_distance(
    depth_m: np.ndarray,
    detection: DetectionBox,
    color_width: int,
    color_height: int,
    roi_fraction: float,
    min_distance_m: float,
    max_distance_m: float,
    minimum_samples: int = 5,
) -> float | None:
    """Return median aligned depth from the central portion of a person box."""
    if (
        depth_m.ndim != 2
        or color_width <= 0
        or color_height <= 0
        or not 0.0 < roi_fraction <= 1.0
    ):
        return None

    center_x, center_y = detection.center
    roi_width = detection.width * roi_fraction
    roi_height = detection.height * roi_fraction
    color_left = center_x - roi_width / 2.0
    color_right = center_x + roi_width / 2.0
    color_top = center_y - roi_height / 2.0
    color_bottom = center_y + roi_height / 2.0

    depth_height, depth_width = depth_m.shape
    left = max(0, min(depth_width - 1, int(color_left * depth_width / color_width)))
    right = max(left + 1, min(depth_width, int(math.ceil(
        color_right * depth_width / color_width
    ))))
    top = max(0, min(depth_height - 1, int(color_top * depth_height / color_height)))
    bottom = max(top + 1, min(depth_height, int(math.ceil(
        color_bottom * depth_height / color_height
    ))))

    values = depth_m[top:bottom, left:right]
    valid = values[
        np.isfinite(values)
        & (values >= min_distance_m)
        & (values <= max_distance_m)
    ]
    if valid.size < minimum_samples:
        return None
    return float(np.median(valid))


class PresenceTracker:
    """Hold/release hysteresis for the /vision/people/presence topic.

    True is published only after *hold_sec* of continuous detections; False is
    published only after *release_sec* of continuous absence.  This prevents the
    greeting path from flickering on momentary detection dropouts.
    """

    def __init__(self, hold_sec: float = 5.0, release_sec: float = 1.0) -> None:
        if hold_sec < 0.0:
            raise ValueError("hold_sec must be non-negative")
        if release_sec < 0.0:
            raise ValueError("release_sec must be non-negative")
        self.hold_sec = hold_sec
        self.release_sec = release_sec
        self.active = False
        self.hold_start = 0.0
        self.release_start = 0.0

    def update(self, person_seen: bool, now: float) -> bool | None:
        """Return True / False when the published state should change, else None."""
        if person_seen:
            if not self.active:
                if self.hold_start == 0.0:
                    self.hold_start = now
                elif (now - self.hold_start) >= self.hold_sec:
                    self.active = True
                    self.hold_start = 0.0
                    self.release_start = 0.0
                    return True
            else:
                self.release_start = 0.0
        else:
            if self.active:
                if self.release_start == 0.0:
                    self.release_start = now
                elif (now - self.release_start) >= self.release_sec:
                    self.active = False
                    self.release_start = 0.0
                    self.hold_start = 0.0
                    return False
            else:
                self.hold_start = 0.0
        return None
