from pathlib import Path

import pytest

from evo_navigation.waypoints import WaypointConfigurationError, WaypointRegistry


def write_registry(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "waypoints.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_reception_and_room_waypoints(tmp_path: Path) -> None:
    path = write_registry(
        tmp_path,
        """
frame_id: map
hardware_validated: false
waypoints:
  reception: {x: 0.0, y: 0.0, yaw: 0.0}
  "42": {x: 1.5, y: -0.5, yaw: 1.57}
""",
    )

    registry = WaypointRegistry.from_yaml(path)

    assert registry.get("reception").frame_id == "map"
    assert registry.get("42").x == 1.5
    assert not registry.hardware_validated


def test_requires_reception_destination(tmp_path: Path) -> None:
    path = write_registry(
        tmp_path,
        """
frame_id: map
hardware_validated: false
waypoints:
  "42": {x: 1.0, y: 2.0, yaw: 0.0}
""",
    )

    with pytest.raises(WaypointConfigurationError, match="reception"):
        WaypointRegistry.from_yaml(path)


def test_rejects_non_numeric_coordinates(tmp_path: Path) -> None:
    path = write_registry(
        tmp_path,
        """
frame_id: map
hardware_validated: false
waypoints:
  reception: {x: unknown, y: 0.0, yaw: 0.0}
""",
    )

    with pytest.raises(WaypointConfigurationError, match="must be numeric"):
        WaypointRegistry.from_yaml(path)
