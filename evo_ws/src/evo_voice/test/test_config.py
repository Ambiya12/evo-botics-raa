from pathlib import Path

import pytest

from evo_voice.config import (
    DEFAULT_CAPTURE_PATH,
    DEFAULT_PLAYBACK_PATH,
    ConfigurationError,
    VoiceConfig,
)


def make_config(**overrides) -> VoiceConfig:
    values = {
        "model_path": Path(),
        "device": "cpu",
        "language": "auto",
        "audio_device": -1,
        "french_voice_path": Path(),
        "english_voice_path": Path(),
        "capture_path": DEFAULT_CAPTURE_PATH,
        "playback_path": DEFAULT_PLAYBACK_PATH,
        "mock_audio": True,
    }
    values.update(overrides)
    return VoiceConfig(**values)


def test_mock_audio_does_not_require_models_or_audio_executables() -> None:
    make_config().validate()


@pytest.mark.parametrize("language", ["auto", "fr", "en"])
def test_supported_languages_are_valid(language: str) -> None:
    make_config(language=language).validate()


def test_invalid_language_has_actionable_error() -> None:
    with pytest.raises(ConfigurationError, match="'language' must be one of"):
        make_config(language="de").validate()


def test_invalid_audio_device_has_actionable_error() -> None:
    with pytest.raises(ConfigurationError, match="'audio_device'"):
        make_config(audio_device=-2).validate()


def test_hardware_mode_requires_local_model_and_voice_paths() -> None:
    with pytest.raises(ConfigurationError) as error:
        make_config(mock_audio=False).validate()

    message = str(error.value)
    assert "'model_path' is required" in message
    assert "'french_voice_path' is required" in message
    assert "'english_voice_path' is required" in message
