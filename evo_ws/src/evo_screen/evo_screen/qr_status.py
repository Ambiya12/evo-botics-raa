"""Parsing pur du JSON de /reception/qr/status vers une commande d'écran. Sans ROS ni Pillow."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScreenCommand:
    screen: str          # welcome | validating | success | error | guide
    reservation: dict    # {} si non applicable
    terminal: bool        # True => retour auto à welcome après la fenêtre d'affichage


# state du bridge -> (écran, terminal). Tout state absent de cette table => ignoré.
_STATE_TO_SCREEN = {
    "waiting": ("welcome", False),
    "scanned": ("validating", False),
    "validating": ("validating", False),
    "success": ("success", True),
    "error": ("error", True),
    "guide": ("guide", False),  # jamais émis par le bridge ; rendu prêt si un jour il l'est
}


def parse(data: str) -> Optional[ScreenCommand]:
    try:
        obj = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    mapping = _STATE_TO_SCREEN.get(obj.get("state"))
    if mapping is None:
        return None
    screen, terminal = mapping
    reservation = obj.get("reservation")
    if not isinstance(reservation, dict):
        reservation = {}
    return ScreenCommand(screen=screen, reservation=reservation, terminal=terminal)
