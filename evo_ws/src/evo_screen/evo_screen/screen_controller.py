"""Orchestration pure de l'écran : parse -> render -> adapter, filet deadline. Sans ROS ni cv2."""
from __future__ import annotations

from evo_screen.display_state import DisplayState
from evo_screen.lcd_renderer import (
    DEFAULT_FONT_PATH,
    render_welcome, render_validating, render_success, render_error, render_guide,
)
from evo_screen.qr_status import parse


class ScreenController:
    def __init__(self, adapter, *, width: int = 1024, height: int = 600,
                 font_path: str = DEFAULT_FONT_PATH, font_size: int = 96,
                 duration: float = 10.0):
        self._adapter = adapter
        self._w = width
        self._h = height
        self._font_path = font_path
        self._font_size = font_size
        self._duration = duration
        self._state = DisplayState()

    def _render(self, screen: str, reservation: dict):
        kw = dict(font_path=self._font_path, font_size=self._font_size)
        if screen == "welcome":
            return render_welcome(self._w, self._h, **kw)
        if screen == "validating":
            return render_validating(self._w, self._h, **kw)
        if screen == "success":
            return render_success(reservation, self._w, self._h, **kw)
        if screen == "error":
            return render_error(self._w, self._h, **kw)
        if screen == "guide":
            return render_guide(self._w, self._h, **kw)
        raise ValueError(f"écran inconnu : {screen}")

    def _show(self, image) -> None:
        if self._adapter is not None:
            self._adapter.show(image)

    def show_welcome(self) -> None:
        self._show(self._render("welcome", {}))

    def on_status(self, data: str, now: float) -> bool:
        cmd = parse(data)
        if cmd is None:
            return False
        self._show(self._render(cmd.screen, cmd.reservation))
        if cmd.terminal:
            self._state.request(now, self._duration)
        else:
            self._state.mark_cleared()
        return True

    def tick(self, now: float) -> None:
        if self._state.active and self._state.should_clear(now):
            self._show(self._render("welcome", {}))   # retour welcome (jamais clear -> pas d'écran noir)
            self._state.mark_cleared()
        elif self._adapter is not None:
            self._adapter.pump()

    def abort(self) -> None:
        self._state.mark_cleared()

    def shutdown(self) -> None:
        if self._adapter is not None:
            self._adapter.clear()
