from pathlib import Path

import pytest

from evo_voice.phrases import PhraseBook


def test_phrase_key_resolves_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "phrases.yaml"
    config_path.write_text(
        "phrases:\n  greeting: Hello from configuration.\n",
        encoding="utf-8",
    )

    phrase_book = PhraseBook.from_yaml(config_path)

    assert phrase_book.resolve_request("phrase:greeting") == "Hello from configuration."


def test_plain_text_request_is_preserved(tmp_path: Path) -> None:
    config_path = tmp_path / "phrases.yaml"
    config_path.write_text("phrases:\n  greeting: Hello.\n", encoding="utf-8")

    phrase_book = PhraseBook.from_yaml(config_path)

    assert phrase_book.resolve_request("Speak this text.") == "Speak this text."


def test_unknown_phrase_key_fails_clearly(tmp_path: Path) -> None:
    config_path = tmp_path / "phrases.yaml"
    config_path.write_text("phrases:\n  greeting: Hello.\n", encoding="utf-8")
    phrase_book = PhraseBook.from_yaml(config_path)

    with pytest.raises(ValueError, match="Unknown reception phrase"):
        phrase_book.resolve_request("phrase:missing")
