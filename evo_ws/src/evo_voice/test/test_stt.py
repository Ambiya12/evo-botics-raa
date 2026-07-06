from array import array
from io import BytesIO
import wave

from evo_voice.stt import (
    CaptureGate,
    ListeningMode,
    SttPipeline,
    TranscriptionResult,
    WavEnergyVad,
    trim_wav_prefix,
)

class StubTranscriber:
    def __init__(self, result: TranscriptionResult, fail: bool = False) -> None:
        self.result = result
        self.fail = fail
        self.calls = 0

    def transcribe(self, wav_data: bytes) -> TranscriptionResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("Configured transcription failure")
        return self.result


def wav_fixture(amplitude: int, frame_count: int = 1600) -> bytes:
    samples = array("h", [amplitude, -amplitude] * (frame_count // 2))
    output = BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(samples.tobytes())
    return output.getvalue()


def make_pipeline(
    transcriber: StubTranscriber,
    gate: CaptureGate | None = None,
    errors: list[Exception] | None = None,
) -> SttPipeline:
    return SttPipeline(
        transcriber=transcriber,
        vad=WavEnergyVad(rms_threshold=0.01),
        capture_gate=gate or CaptureGate(),
        minimum_confidence=0.4,
        error_callback=None if errors is None else errors.append,
    )


def test_valid_fixture_produces_typed_transcription_data() -> None:
    transcriber = StubTranscriber(
        TranscriptionResult("Hello reception", "en", 0.91)
    )

    result = make_pipeline(transcriber).process(wav_fixture(amplitude=4000))

    assert result == TranscriptionResult("Hello reception", "en", 0.91)
    assert transcriber.calls == 1


def test_empty_audio_is_rejected_before_transcription() -> None:
    transcriber = StubTranscriber(TranscriptionResult("should not publish", "en", 1.0))

    result = make_pipeline(transcriber).process(b"")

    assert result is None
    assert transcriber.calls == 0


def test_quiet_noise_is_not_a_usable_transcript() -> None:
    transcriber = StubTranscriber(TranscriptionResult("noise", "en", 1.0))

    result = make_pipeline(transcriber).process(wav_fixture(amplitude=20))

    assert result is None
    assert transcriber.calls == 0


def test_empty_transcription_is_not_published() -> None:
    transcriber = StubTranscriber(TranscriptionResult("   ", "en", 0.9))

    result = make_pipeline(transcriber).process(wav_fixture(amplitude=4000))

    assert result is None
    assert transcriber.calls == 1


def test_transcription_failure_is_handled_without_result() -> None:
    errors: list[Exception] = []
    transcriber = StubTranscriber(
        TranscriptionResult("", "", None),
        fail=True,
    )

    result = make_pipeline(transcriber, errors=errors).process(
        wav_fixture(amplitude=4000)
    )

    assert result is None
    assert len(errors) == 1


def test_capture_pauses_while_tts_is_speaking() -> None:
    gate = CaptureGate()
    transcriber = StubTranscriber(TranscriptionResult("robot voice", "en", 1.0))
    pipeline = make_pipeline(transcriber, gate=gate)

    gate.update_tts_status("speaking")
    paused_result = pipeline.process(wav_fixture(amplitude=4000))
    gate.update_tts_status("completed")
    resumed_result = pipeline.process(wav_fixture(amplitude=4000))

    assert paused_result is None
    assert resumed_result == TranscriptionResult("robot voice", "en", 1.0)
    assert transcriber.calls == 1


def test_capture_is_disabled_until_dialogue_arms_listening() -> None:
    gate = CaptureGate(initial_mode=ListeningMode.DISABLED)
    transcriber = StubTranscriber(TranscriptionResult("hello", "en", 1.0))
    pipeline = make_pipeline(transcriber, gate=gate)

    disabled = pipeline.process(wav_fixture(amplitude=4000))
    gate.update_dialogue_state("PRESENCE_ARMED")
    armed = pipeline.process(wav_fixture(amplitude=4000))

    assert disabled is None
    assert armed == TranscriptionResult("hello", "en", 1.0)


def test_capture_started_in_previous_dialogue_state_is_rejected() -> None:
    gate = CaptureGate(initial_mode=ListeningMode.WAKE)
    transcriber = StubTranscriber(TranscriptionResult("hello", "en", 1.0))
    pipeline = make_pipeline(transcriber, gate=gate)
    token = gate.capture_token()

    gate.update_dialogue_state("GREETING")
    gate.update_dialogue_state("WAITING_FOR_INTENT")
    result = pipeline.process(
        wav_fixture(amplitude=4000),
        capture_token=token,
    )

    assert result is None
    assert transcriber.calls == 0


def test_unknown_tts_status_does_not_resume_capture() -> None:
    gate = CaptureGate()
    gate.update_tts_status("speaking")

    gate.update_tts_status("unexpected")

    assert gate.paused


def test_audio_overlapping_completed_tts_is_discarded() -> None:
    gate = CaptureGate()
    transcriber = StubTranscriber(TranscriptionResult("robot voice", "en", 1.0))
    pipeline = make_pipeline(transcriber, gate=gate)
    capture_token = gate.capture_token()

    gate.update_tts_status("speaking")
    gate.update_tts_status("completed")
    result = pipeline.process(
        wav_fixture(amplitude=4000),
        capture_token=capture_token,
    )

    assert result is None
    assert transcriber.calls == 0


def test_human_suffix_after_completed_tts_is_recovered(monkeypatch) -> None:
    monkeypatch.setattr("evo_voice.stt.time.monotonic", lambda: 10.5)
    gate = CaptureGate()
    transcriber = StubTranscriber(TranscriptionResult("yes", "en", 0.99))
    pipeline = make_pipeline(transcriber, gate=gate)
    capture_token = gate.capture_token()

    gate.update_tts_status("speaking")
    gate.update_tts_status("completed")
    result = pipeline.process(
        wav_fixture(amplitude=4000, frame_count=32000),
        capture_token=capture_token,
        capture_started_at=10.0,
    )

    assert result == TranscriptionResult("yes", "en", 0.99)
    assert transcriber.calls == 1


def test_overlapped_capture_is_rejected_after_another_tts_cycle(
    monkeypatch,
) -> None:
    timestamps = iter((10.5, 11.0))
    monkeypatch.setattr(
        "evo_voice.stt.time.monotonic",
        lambda: next(timestamps),
    )
    gate = CaptureGate()
    transcriber = StubTranscriber(TranscriptionResult("yes", "en", 0.99))
    pipeline = make_pipeline(transcriber, gate=gate)
    capture_token = gate.capture_token()

    gate.update_tts_status("speaking")
    gate.update_tts_status("completed")
    gate.update_tts_status("speaking")
    gate.update_tts_status("completed")
    result = pipeline.process(
        wav_fixture(amplitude=4000, frame_count=32000),
        capture_token=capture_token,
        capture_started_at=10.0,
    )

    assert result is None
    assert transcriber.calls == 0


def test_low_confidence_human_suffix_is_not_published(monkeypatch) -> None:
    monkeypatch.setattr("evo_voice.stt.time.monotonic", lambda: 10.5)
    gate = CaptureGate()
    transcriber = StubTranscriber(TranscriptionResult("yes", "en", 0.39))
    pipeline = make_pipeline(transcriber, gate=gate)
    capture_token = gate.capture_token()

    gate.update_tts_status("speaking")
    gate.update_tts_status("completed")
    result = pipeline.process(
        wav_fixture(amplitude=4000, frame_count=32000),
        capture_token=capture_token,
        capture_started_at=10.0,
    )

    assert result is None
    assert transcriber.calls == 1


def test_wav_prefix_trim_preserves_only_remaining_audio() -> None:
    original = wav_fixture(amplitude=4000, frame_count=32000)

    trimmed = trim_wav_prefix(original, 0.5)

    with wave.open(BytesIO(trimmed), "rb") as wav_file:
        assert wav_file.getframerate() == 16000
        assert wav_file.getnframes() == 24000
