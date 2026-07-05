from pathlib import Path

import pytest

from evo_navigation.waypoints import WaypointConfigurationError, WaypointRegistry


HOME_WAYPOINTS = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "home_reception_waypoints.yaml"
)


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


def test_home_registry_maps_reception_and_reservation_room_ids() -> None:
    registry = WaypointRegistry.from_yaml(HOME_WAYPOINTS)

    reception = registry.get("reception")
    room_a = registry.get("1")
    room_b = registry.get("2")

    assert reception is not None
    assert (reception.x, reception.y, reception.yaw) == (-0.03, 0.83, -1.74)
    assert room_a is not None
    assert (room_a.x, room_a.y, room_a.yaw) == (-0.80, 0.35, -2.64)
    assert room_b is not None
    assert (room_b.x, room_b.y, room_b.yaw) == (-0.01, 1.08, 1.55)
    assert registry.hardware_validated
