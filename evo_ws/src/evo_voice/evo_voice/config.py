from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rclpy.node import Node

DEFAULT_CAPTURE_PATH = Path(tempfile.gettempdir()) / "evo_voice_capture.wav"
DEFAULT_PLAYBACK_PATH = Path(tempfile.gettempdir()) / "evo_voice_playback.wav"


class ConfigurationError(ValueError):
    """Raised when the legacy translator cannot start safely."""


@dataclass(frozen=True)
class VoiceConfig:
    model_path: Path
    device: str
    language: str
    audio_device: int
    french_voice_path: Path
    english_voice_path: Path
    capture_path: Path
    playback_path: Path
    mock_audio: bool

    @classmethod
    def from_node(cls, node: "Node") -> "VoiceConfig":
        config = cls(
            model_path=_path(node.declare_parameter("model_path", "").value),
            device=str(node.declare_parameter("device", "cpu").value).strip(),
            language=str(node.declare_parameter("language", "auto").value).lower(),
            audio_device=int(node.declare_parameter("audio_device", -1).value),
            french_voice_path=_path(
                node.declare_parameter("french_voice_path", "").value
            ),
            english_voice_path=_path(
                node.declare_parameter("english_voice_path", "").value
            ),
            capture_path=_path(
                node.declare_parameter(
                    "capture_path", str(DEFAULT_CAPTURE_PATH)
                ).value
            ),
            playback_path=_path(
                node.declare_parameter(
                    "playback_path", str(DEFAULT_PLAYBACK_PATH)
                ).value
            ),
            mock_audio=bool(node.declare_parameter("mock_audio", True).value),
        )
        config.validate()
        return config

    def validate(self) -> None:
        errors: list[str] = []

        if not self.device:
            errors.append("'device' must not be empty")
        if self.language not in {"auto", "fr", "en"}:
            errors.append("'language' must be one of: auto, fr, en")
        if self.audio_device < -1:
            errors.append("'audio_device' must be -1 (system default) or a non-negative index")
        if not self.capture_path.name:
            errors.append("'capture_path' must name a file")
        if not self.playback_path.name:
            errors.append("'playback_path' must name a file")

        if not self.mock_audio:
            self._require_existing_path(self.model_path, "model_path", errors)
            self._require_existing_path(
                self.french_voice_path, "french_voice_path", errors
            )
            self._require_existing_path(
                self.english_voice_path, "english_voice_path", errors
            )
            for executable in ("piper", "mpv"):
                if shutil.which(executable) is None:
                    errors.append(
                        f"required executable '{executable}' was not found on PATH"
                    )

        if errors:
            raise ConfigurationError("Invalid evo_voice configuration: " + "; ".join(errors))

    @staticmethod
    def _require_existing_path(
        path: Path, parameter_name: str, errors: list[str]
    ) -> None:
        if path == Path():
            errors.append(f"'{parameter_name}' is required when mock_audio is false")
        elif not path.exists():
            errors.append(f"'{parameter_name}' does not exist: {path}")


def _path(value: object) -> Path:
    text = str(value).strip()
    return Path(text).expanduser() if text else Path()
