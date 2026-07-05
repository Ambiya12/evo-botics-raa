from pathlib import Path

import pytest

from evo_voice.phrases import PhraseBook


RECEPTION_PHRASES = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "reception_phrases.yaml"
)


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


def test_reception_workflow_uses_required_visitor_messages() -> None:
    phrase_book = PhraseBook.from_yaml(RECEPTION_PHRASES)

    assert phrase_book.resolve_request("phrase:greeting") == (
        "Hi, I’m Evo. Welcome to HETIC. Do you already have a room "
        "reservation? Please say yes or no."
    )
    assert phrase_book.resolve_request("phrase:no_reservation") == (
        "No problem. Please speak with reception if you need help."
    )
    assert phrase_book.resolve_request("phrase:request_qr") == (
        "Please provide the QR code and scan it on my camera."
    )
    assert phrase_book.resolve_request("phrase:invalid_qr") == (
        "Sorry, your QR code is invalid. Please try again."
    )
    assert phrase_book.resolve_request("phrase:guidance_start") == (
        "Thanks, your reservation is validated. Follow me."
    )
    assert phrase_book.resolve_request("phrase:arrived") == "Have a nice day."
