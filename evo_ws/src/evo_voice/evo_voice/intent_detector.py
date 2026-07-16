from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import unicodedata

import yaml


SUPPORTED_INTENTS = frozenset(
    {
        "reservation",
        "affirmative",
        "negative",
        "repeat",
        "cancel",
        "greeting",
    }
)
UNKNOWN = "unknown"


class IntentConfigurationError(ValueError):
    """Raised when deterministic intent phrases are missing or ambiguous."""


@dataclass(frozen=True)
class IntentMatch:
    intent: str
    confidence: float
    source_transcript: str
    normalized_transcript: str
    matched_phrase: str = ""


@dataclass(frozen=True)
class _PhraseRule:
    intent: str
    phrase: str
    tokens: tuple[str, ...]
    priority: int


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    characters = [
        character
        if unicodedata.category(character)[0] in {"L", "N"}
        else " "
        for character in normalized
    ]
    return " ".join("".join(characters).split())


class IntentDetector:
    def __init__(self, rules: list[_PhraseRule]) -> None:
        self._rules = rules

    @classmethod
    def from_yaml(cls, path: Path) -> "IntentDetector":
        try:
            with path.open(encoding="utf-8") as stream:
                document = yaml.safe_load(stream)
        except (OSError, yaml.YAMLError) as exc:
            raise IntentConfigurationError(
                f"Could not load intent configuration {path}: {exc}"
            ) from exc

        if not isinstance(document, dict):
            raise IntentConfigurationError("Intent configuration must be a YAML map")
        priority = document.get("priority")
        intents = document.get("intents")
        if (
            not isinstance(priority, list)
            or not all(isinstance(value, str) for value in priority)
            or len(priority) != len(SUPPORTED_INTENTS)
            or frozenset(priority) != SUPPORTED_INTENTS
        ):
            raise IntentConfigurationError(
                "'priority' must list each supported intent exactly once"
            )
        if (
            not isinstance(intents, dict)
            or not all(isinstance(value, str) for value in intents)
            or frozenset(intents) != SUPPORTED_INTENTS
        ):
            raise IntentConfigurationError(
                "'intents' must define phrases for every supported intent"
            )

        rules: list[_PhraseRule] = []
        phrase_owners: dict[tuple[str, ...], str] = {}
        for priority_index, intent in enumerate(priority):
            phrases = intents[intent]
            if not isinstance(phrases, list) or not phrases:
                raise IntentConfigurationError(
                    f"Intent '{intent}' must contain at least one phrase"
                )
            for value in phrases:
                if not isinstance(value, str):
                    raise IntentConfigurationError(
                        f"Intent '{intent}' phrases must be strings"
                    )
                phrase = normalize_text(value)
                tokens = tuple(phrase.split())
                if not tokens:
                    raise IntentConfigurationError(
                        f"Intent '{intent}' contains an empty phrase"
                    )
                owner = phrase_owners.get(tokens)
                if owner is not None and owner != intent:
                    raise IntentConfigurationError(
                        f"Phrase '{phrase}' belongs to both '{owner}' and '{intent}'"
                    )
                if owner == intent:
                    continue
                phrase_owners[tokens] = intent
                rules.append(
                    _PhraseRule(intent, phrase, tokens, priority_index)
                )
        return cls(rules)

    def detect(self, transcript: str) -> IntentMatch:
        normalized = normalize_text(transcript)
        transcript_tokens = tuple(normalized.split())
        candidates = [
            rule
            for rule in self._rules
            if _contains_token_sequence(transcript_tokens, rule.tokens)
        ]
        if not candidates:
            return IntentMatch(UNKNOWN, 0.0, transcript, normalized)

        winner = min(
            candidates,
            key=lambda rule: (-len(rule.tokens), rule.priority, rule.phrase),
        )
        if winner.tokens == transcript_tokens:
            confidence = 1.0
        elif len(winner.tokens) > 1:
            confidence = 0.9
        else:
            confidence = 0.8
        return IntentMatch(
            intent=winner.intent,
            confidence=confidence,
            source_transcript=transcript,
            normalized_transcript=normalized,
            matched_phrase=winner.phrase,
        )


def _contains_token_sequence(
    transcript_tokens: tuple[str, ...],
    phrase_tokens: tuple[str, ...],
) -> bool:
    phrase_length = len(phrase_tokens)
    if phrase_length > len(transcript_tokens):
        return False
    return any(
        transcript_tokens[index:index + phrase_length] == phrase_tokens
        for index in range(len(transcript_tokens) - phrase_length + 1)
    )
