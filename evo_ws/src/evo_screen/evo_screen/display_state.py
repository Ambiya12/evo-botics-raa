"""Machine d'état pure de la fenêtre d'affichage (deadline). Sans ROS ni matériel."""
from __future__ import annotations

from typing import Optional


class DisplayState:
    def __init__(self) -> None:
        self._deadline: Optional[float] = None

    @property
    def active(self) -> bool:
        return self._deadline is not None

    def request(self, now: float, duration: float) -> None:
        self._deadline = now + duration

    def should_clear(self, now: float) -> bool:
        return self._deadline is not None and now >= self._deadline

    def mark_cleared(self) -> None:
        self._deadline = None
