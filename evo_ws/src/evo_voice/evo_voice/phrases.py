from __future__ import annotations

from pathlib import Path

import yaml


class PhraseConfigurationError(ValueError):
    """Raised when reception phrase configuration is missing or malformed."""


class PhraseBook:
    def __init__(self, phrases: dict[str, str]) -> None:
        self._phrases = phrases

    @classmethod
    def from_yaml(cls, path: Path) -> "PhraseBook":
        if not path.is_file():
            raise PhraseConfigurationError(
                f"Reception phrase configuration does not exist: {path}"
            )

        try:
            with path.open(encoding="utf-8") as stream:
                document = yaml.safe_load(stream)
        except (OSError, yaml.YAMLError) as exc:
            raise PhraseConfigurationError(
                f"Could not load reception phrase configuration: {path}: {exc}"
            ) from exc
        values = document.get("phrases") if isinstance(document, dict) else None
        if not isinstance(values, dict) or not values:
            raise PhraseConfigurationError(
                "Reception phrase configuration must contain a non-empty 'phrases' map"
            )

        phrases: dict[str, str] = {}
        for key, value in values.items():
            if not isinstance(key, str) or not key.strip():
                raise PhraseConfigurationError(
                    "Reception phrase keys must be non-empty strings"
                )
            if not isinstance(value, str) or not value.strip():
                raise PhraseConfigurationError(
                    f"Reception phrase '{key}' must be a non-empty string"
                )
            phrases[key] = value.strip()
        return cls(phrases)

    def resolve_request(self, value: str) -> str:
        request = value.strip()
        if not request:
            raise ValueError("Speak request must not be empty")
        if not request.startswith("phrase:"):
            return request

        key = request.removeprefix("phrase:").strip()
        try:
            return self._phrases[key]
        except KeyError as exc:
            raise ValueError(f"Unknown reception phrase: {key}") from exc
