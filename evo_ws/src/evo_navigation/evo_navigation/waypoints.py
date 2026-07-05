from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import yaml


class WaypointConfigurationError(ValueError):
    """Raised when waypoint configuration is missing or unsafe."""


@dataclass(frozen=True)
class Waypoint:
    destination_id: str
    frame_id: str
    x: float
    y: float
    yaw: float


class WaypointRegistry:
    def __init__(
        self,
        waypoints: dict[str, Waypoint],
        hardware_validated: bool,
    ) -> None:
        self._waypoints = waypoints
        self.hardware_validated = hardware_validated

    @classmethod
    def from_yaml(cls, path: Path) -> "WaypointRegistry":
        try:
            with path.open(encoding="utf-8") as stream:
                document = yaml.safe_load(stream)
        except (OSError, yaml.YAMLError) as exc:
            raise WaypointConfigurationError(
                f"Could not load waypoint configuration {path}: {exc}"
            ) from exc

        if not isinstance(document, dict):
            raise WaypointConfigurationError("Waypoint configuration must be a map")
        frame_id = document.get("frame_id")
        hardware_validated = document.get("hardware_validated")
        entries = document.get("waypoints")
        if not isinstance(frame_id, str) or not frame_id.strip():
            raise WaypointConfigurationError("'frame_id' must be a non-empty string")
        if not isinstance(hardware_validated, bool):
            raise WaypointConfigurationError("'hardware_validated' must be boolean")
        if not isinstance(entries, dict) or not entries:
            raise WaypointConfigurationError("'waypoints' must be a non-empty map")

        waypoints: dict[str, Waypoint] = {}
        for raw_destination_id, value in entries.items():
            destination_id = str(raw_destination_id).strip()
            if not destination_id:
                raise WaypointConfigurationError("Waypoint IDs must not be empty")
            if destination_id in waypoints:
                raise WaypointConfigurationError(
                    f"Duplicate waypoint ID after normalization: {destination_id}"
                )
            if not isinstance(value, dict):
                raise WaypointConfigurationError(
                    f"Waypoint '{destination_id}' must be a map"
                )
            coordinates = []
            for field in ("x", "y", "yaw"):
                coordinate = value.get(field)
                if isinstance(coordinate, bool) or not isinstance(
                    coordinate, (int, float)
                ):
                    raise WaypointConfigurationError(
                        f"Waypoint '{destination_id}' field '{field}' must be numeric"
                    )
                number = float(coordinate)
                if not math.isfinite(number):
                    raise WaypointConfigurationError(
                        f"Waypoint '{destination_id}' field '{field}' must be finite"
                    )
                coordinates.append(number)
            waypoints[destination_id] = Waypoint(
                destination_id,
                frame_id.strip(),
                coordinates[0],
                coordinates[1],
                coordinates[2],
            )

        if "reception" not in waypoints:
            raise WaypointConfigurationError(
                "Waypoint configuration must include 'reception'"
            )
        return cls(waypoints, hardware_validated)

    def get(self, destination_id: str) -> Waypoint | None:
        return self._waypoints.get(destination_id.strip())
