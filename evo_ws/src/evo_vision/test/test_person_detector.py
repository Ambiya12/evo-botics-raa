import numpy as np

from evo_vision.person_detector import (
    DetectionBox,
    LetterboxTransform,
    decode_yolov5_people,
    estimate_person_distance,
    non_max_suppression,
    select_primary_person,
)


def transform() -> LetterboxTransform:
    return LetterboxTransform(
        scale=1.0,
        pad_x=0.0,
        pad_y=0.0,
        source_width=640,
        source_height=640,
    )


def test_decodes_only_confident_person_rows() -> None:
    output = np.zeros((1, 3, 85), dtype=np.float32)
    output[0, 0, :6] = [320.0, 320.0, 100.0, 200.0, 0.9, 0.8]
    output[0, 1, :6] = [100.0, 100.0, 40.0, 40.0, 0.4, 0.4]
    output[0, 2, :7] = [200.0, 200.0, 50.0, 50.0, 0.9, 0.1, 0.9]

    detections = decode_yolov5_people(
        output,
        transform(),
        confidence_threshold=0.5,
    )

    assert len(detections) == 1
    detection = detections[0]
    assert (detection.x, detection.y) == (270.0, 220.0)
    assert (detection.width, detection.height) == (100.0, 200.0)
    assert detection.confidence == np.float32(0.9) * np.float32(0.8)


def test_letterbox_padding_is_removed_and_boxes_are_clamped() -> None:
    output = np.zeros((1, 1, 85), dtype=np.float32)
    output[0, 0, :6] = [320.0, 320.0, 640.0, 320.0, 1.0, 1.0]
    letterbox = LetterboxTransform(
        scale=1.0,
        pad_x=0.0,
        pad_y=160.0,
        source_width=640,
        source_height=320,
    )

    detection = decode_yolov5_people(
        output,
        letterbox,
        confidence_threshold=0.5,
    )[0]

    assert (detection.x, detection.y) == (0.0, 0.0)
    assert (detection.width, detection.height) == (640.0, 320.0)


def test_non_max_suppression_keeps_best_overlapping_box() -> None:
    best = DetectionBox(10.0, 10.0, 100.0, 100.0, 0.9)
    overlap = DetectionBox(12.0, 12.0, 100.0, 100.0, 0.8)
    separate = DetectionBox(300.0, 300.0, 50.0, 50.0, 0.7)

    selected = non_max_suppression(
        [overlap, separate, best],
        iou_threshold=0.45,
    )

    assert selected == [best, separate]


def test_primary_person_prefers_largest_visible_box() -> None:
    small = DetectionBox(0.0, 0.0, 20.0, 20.0, 0.99)
    large = DetectionBox(0.0, 0.0, 100.0, 150.0, 0.75)

    assert select_primary_person([small, large]) == large


def test_distance_uses_median_valid_depth_in_central_roi() -> None:
    depth = np.full((100, 100), np.nan, dtype=np.float32)
    depth[40:60, 40:60] = 1.5
    depth[50, 50] = 4.0
    detection = DetectionBox(20.0, 20.0, 60.0, 60.0, 0.9)

    distance = estimate_person_distance(
        depth,
        detection,
        color_width=100,
        color_height=100,
        roi_fraction=0.4,
        min_distance_m=0.2,
        max_distance_m=3.0,
    )

    assert distance == 1.5


def test_distance_fails_closed_without_enough_depth_samples() -> None:
    depth = np.full((20, 20), np.nan, dtype=np.float32)
    depth[10, 10] = 1.0

    assert estimate_person_distance(
        depth,
        DetectionBox(0.0, 0.0, 20.0, 20.0, 0.9),
        color_width=20,
        color_height=20,
        roi_fraction=1.0,
        min_distance_m=0.2,
        max_distance_m=3.0,
    ) is None
