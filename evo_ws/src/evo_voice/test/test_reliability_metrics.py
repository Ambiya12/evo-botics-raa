import json

import pytest

from evo_voice.reliability_metrics import (
    load_jsonl,
    percentile,
    summarize,
    word_error_rate,
)


def test_word_error_rate_normalizes_case_and_punctuation() -> None:
    assert word_error_rate(
        "I have a reservation.",
        "i HAVE a reservation",
    ) == 0.0


def test_summary_reports_recognition_and_latency_p95() -> None:
    summary = summarize([
        {
            "expected_transcript": "I have a reservation",
            "actual_transcript": "I have a reservation",
            "audio_started_at": 1.0,
            "transcript_published_at": 2.0,
            "approach_at": 0.0,
            "navigation_requested_at": 4.0,
        },
        {
            "expected_transcript": "I need help",
            "actual_transcript": "",
            "audio_started_at": 10.0,
            "transcript_published_at": 12.5,
            "approach_at": 9.0,
            "navigation_requested_at": 15.0,
        },
    ])

    assert summary["samples"] == 2
    assert summary["recognition_success_rate"] == 0.5
    assert summary["stt_latency_p95_sec"] == 2.5
    assert summary["end_to_end_latency_p95_sec"] == 6.0


def test_empty_percentile_is_not_reported() -> None:
    assert percentile([], 0.95) is None


def test_measurement_records_require_transcripts(tmp_path) -> None:
    path = tmp_path / "measurements.jsonl"
    path.write_text(json.dumps({"environment": "test"}), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required field"):
        load_jsonl(path)
