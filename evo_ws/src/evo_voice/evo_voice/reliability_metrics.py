from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import unicodedata


WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def normalized_words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return WORD_RE.findall(normalized)


def word_error_rate(expected: str, actual: str) -> float:
    reference = normalized_words(expected)
    hypothesis = normalized_words(actual)
    if not reference:
        return 0.0 if not hypothesis else 1.0

    previous = list(range(len(hypothesis) + 1))
    for row, reference_word in enumerate(reference, start=1):
        current = [row]
        for column, hypothesis_word in enumerate(hypothesis, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1]
                + (reference_word != hypothesis_word),
            ))
        previous = current
    return previous[-1] / len(reference)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            int(len(ordered) * fraction + 0.999) - 1,
        ),
    )
    return ordered[index]


def summarize(records: list[dict], max_wer: float = 0.2) -> dict:
    recognized = []
    stt_latencies = []
    end_to_end_latencies = []

    for record in records:
        wer = word_error_rate(
            str(record.get("expected_transcript", "")),
            str(record.get("actual_transcript", "")),
        )
        recognized.append(wer <= max_wer)
        if "audio_started_at" in record and "transcript_published_at" in record:
            stt_latencies.append(
                float(record["transcript_published_at"])
                - float(record["audio_started_at"])
            )
        if "approach_at" in record and "navigation_requested_at" in record:
            end_to_end_latencies.append(
                float(record["navigation_requested_at"])
                - float(record["approach_at"])
            )

    return {
        "samples": len(records),
        "recognition_success_rate": (
            sum(recognized) / len(recognized) if recognized else None
        ),
        "stt_latency_p95_sec": percentile(stt_latencies, 0.95),
        "end_to_end_latency_p95_sec": percentile(
            end_to_end_latencies, 0.95
        ),
    }


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"{path}:{line_number}: each record must be an object"
                )
            missing = {
                "expected_transcript",
                "actual_transcript",
            } - value.keys()
            if missing:
                names = ", ".join(sorted(missing))
                raise ValueError(
                    f"{path}:{line_number}: missing required field(s): {names}"
                )
            records.append(value)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize offline reception recognition and latency records."
    )
    parser.add_argument("records", type=Path, help="JSON Lines measurement file")
    parser.add_argument("--max-wer", type=float, default=0.2)
    arguments = parser.parse_args()
    if not 0.0 <= arguments.max_wer <= 1.0:
        parser.error("--max-wer must be between 0 and 1")
    print(json.dumps(
        summarize(load_jsonl(arguments.records), arguments.max_wer),
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
