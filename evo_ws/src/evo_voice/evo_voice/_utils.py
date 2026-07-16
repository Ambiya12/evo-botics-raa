from __future__ import annotations

from pathlib import Path


def coerce_path(value: object) -> Path:
    text = str(value).strip()
    return Path(text).expanduser() if text else Path()
