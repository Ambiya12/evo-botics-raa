from array import array
from io import BytesIO
import wave

from evo_voice.stt import (
    CaptureGate,
    MockTranscriber,
    SttPipeline,
    TranscriptionResult,
    WavEnergyVad,
)


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
    transcriber: MockTranscriber,
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
    transcriber = MockTranscriber(
        TranscriptionResult("Hello reception", "en", 0.91)
    )

    result = make_pipeline(transcriber).process(wav_fixture(amplitude=4000))

    assert result == TranscriptionResult("Hello reception", "en", 0.91)
    assert transcriber.calls == 1


def test_empty_audio_is_rejected_before_transcription() -> None:
    transcriber = MockTranscriber(TranscriptionResult("should not publish", "en", 1.0))

    result = make_pipeline(transcriber).process(b"")

    assert result is None
    assert transcriber.calls == 0


def test_quiet_noise_is_not_a_usable_transcript() -> None:
    transcriber = MockTranscriber(TranscriptionResult("noise", "en", 1.0))

    result = make_pipeline(transcriber).process(wav_fixture(amplitude=20))

    assert result is None
    assert transcriber.calls == 0


def test_empty_transcription_is_not_published() -> None:
    transcriber = MockTranscriber(TranscriptionResult("   ", "en", 0.9))

    result = make_pipeline(transcriber).process(wav_fixture(amplitude=4000))

    assert result is None
    assert transcriber.calls == 1


def test_transcription_failure_is_handled_without_result() -> None:
    errors: list[Exception] = []
    transcriber = MockTranscriber(
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
    transcriber = MockTranscriber(TranscriptionResult("robot voice", "en", 1.0))
    pipeline = make_pipeline(transcriber, gate=gate)

    gate.update_tts_status("speaking")
    paused_result = pipeline.process(wav_fixture(amplitude=4000))
    gate.update_tts_status("completed")
    resumed_result = pipeline.process(wav_fixture(amplitude=4000))

    assert paused_result is None
    assert resumed_result == TranscriptionResult("robot voice", "en", 1.0)
    assert transcriber.calls == 1


def test_unknown_tts_status_does_not_resume_capture() -> None:
    gate = CaptureGate()
    gate.update_tts_status("speaking")

    gate.update_tts_status("unexpected")

    assert gate.paused
