from pathlib import Path

import pytest

from evo_voice.intent_detector import UNKNOWN, IntentDetector, normalize_text


CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "reception_intents.yaml"
)


@pytest.fixture
def detector() -> IntentDetector:
    return IntentDetector.from_yaml(CONFIG_PATH)


@pytest.mark.parametrize(
    ("transcript", "expected"),
    [
        ("Hi Evo!", "greeting"),
        ("Hi", "greeting"),
        ("Hello", "greeting"),
        ("Yes", "affirmative"),
        ("Yes, I do", "affirmative"),
        ("I have one", "affirmative"),
        ("No", "negative"),
        ("No, thank you", "negative"),
        ("Not yet", "negative"),
        ("I have a reservation.", "reservation"),
        ("I have a booking", "reservation"),
        ("Could you say that again?", "repeat"),
        ("Never mind, thank you", "cancel"),
    ],
)
def test_synonyms(detector: IntentDetector, transcript: str, expected: str) -> None:
    assert detector.detect(transcript).intent == expected


def test_normalization_handles_punctuation_and_casing(
    detector: IntentDetector,
) -> None:
    match = detector.detect("YES, I DO!")

    assert match.intent == "affirmative"
    assert match.normalized_transcript == "yes i do"


def test_normalization_collapses_symbols_and_whitespace() -> None:
    assert normalize_text("  Meeting—ROOM...   ") == "meeting room"


def test_word_boundaries_prevent_substring_false_positives(
    detector: IntentDetector,
) -> None:
    transcript = "A helpful reservationist is checking inventory in the newsroom."

    assert detector.detect(transcript).intent == UNKNOWN


def test_unrelated_stop_phrase_is_not_cancelled(detector: IntentDetector) -> None:
    assert detector.detect("Where is the nearest bus stop?").intent == UNKNOWN


def test_longest_affirmative_phrase_wins(detector: IntentDetector) -> None:
    match = detector.detect("Yes, I do have one")

    assert match.intent == "affirmative"
    assert match.matched_phrase == "yes i do"


def test_unknown_input(detector: IntentDetector) -> None:
    match = detector.detect("The weather is pleasant today.")

    assert match.intent == UNKNOWN
    assert match.confidence == 0.0


def test_source_transcript_is_preserved(detector: IntentDetector) -> None:
    source = "  I HAVE a Reservation!  "

    match = detector.detect(source)

    assert match.intent == "reservation"
    assert match.source_transcript == source
