from __future__ import annotations

from array import array
from dataclasses import dataclass
from io import BytesIO
import math
from pathlib import Path
import sys
from threading import Event
from typing import Callable, Protocol
import wave


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    confidence: float | None = None


class Transcriber(Protocol):
    def transcribe(self, wav_data: bytes) -> TranscriptionResult:
        """Transcribe one complete WAV recording."""


class CaptureGate:
    """Tracks whether TTS is speaking and capture results must be discarded."""

    def __init__(self) -> None:
        self._tts_speaking = Event()

    @property
    def paused(self) -> bool:
        return self._tts_speaking.is_set()

    def update_tts_status(self, status: str) -> None:
        normalized = status.strip().lower()
        if normalized == "speaking":
            self._tts_speaking.set()
        elif normalized in {"idle", "completed", "failed"}:
            self._tts_speaking.clear()


class WavEnergyVad:
    """Small offline energy gate; Faster Whisper performs its own VAD as well."""

    def __init__(self, rms_threshold: float) -> None:
        if not 0.0 <= rms_threshold <= 1.0:
            raise ValueError("VAD RMS threshold must be between 0.0 and 1.0")
        self.rms_threshold = rms_threshold

    def contains_speech(self, wav_data: bytes) -> bool:
        try:
            with wave.open(BytesIO(wav_data), "rb") as wav_file:
                if wav_file.getsampwidth() != 2 or wav_file.getnframes() == 0:
                    return False
                samples = array("h", wav_file.readframes(wav_file.getnframes()))
        except (EOFError, wave.Error):
            return False

        if sys.byteorder != "little":
            samples.byteswap()
        if not samples:
            return False
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
        return rms / 32768.0 >= self.rms_threshold


class MockTranscriber:
    def __init__(
        self,
        result: TranscriptionResult,
        fail: bool = False,
    ) -> None:
        self.result = result
        self.fail = fail
        self.calls = 0

    def transcribe(self, wav_data: bytes) -> TranscriptionResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("Configured mock transcription failure")
        return self.result


class FasterWhisperTranscriber:
    def __init__(
        self,
        model_path: Path,
        capture_path: Path,
        device: str,
        compute_type: str,
        language: str,
    ) -> None:
        from faster_whisper import WhisperModel

        self.capture_path = capture_path
        self.language = None if language == "auto" else language
        self.model = WhisperModel(
            str(model_path),
            device=device,
            compute_type=compute_type,
            local_files_only=True,
        )

    def transcribe(self, wav_data: bytes) -> TranscriptionResult:
        self.capture_path.write_bytes(wav_data)
        segments, info = self.model.transcribe(
            str(self.capture_path),
            language=self.language,
            vad_filter=True,
        )
        text = "".join(segment.text for segment in segments).strip()
        confidence = getattr(info, "language_probability", None)
        return TranscriptionResult(
            text=text,
            language=str(getattr(info, "language", "") or ""),
            confidence=float(confidence) if confidence is not None else None,
        )


class SttPipeline:
    """Hardware-free VAD/transcription pipeline with TTS capture gating."""

    def __init__(
        self,
        transcriber: Transcriber,
        vad: WavEnergyVad,
        capture_gate: CaptureGate,
        minimum_confidence: float = 0.0,
        error_callback: Callable[[Exception], None] | None = None,
    ) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("Minimum confidence must be between 0.0 and 1.0")
        self.transcriber = transcriber
        self.vad = vad
        self.capture_gate = capture_gate
        self.minimum_confidence = minimum_confidence
        self.error_callback = error_callback

    def process(self, wav_data: bytes) -> TranscriptionResult | None:
        if self.capture_gate.paused or not self.vad.contains_speech(wav_data):
            return None

        try:
            result = self.transcriber.transcribe(wav_data)
        except Exception as exc:
            if self.error_callback is not None:
                self.error_callback(exc)
            return None

        # TTS may have started while transcription was running.
        if self.capture_gate.paused:
            return None

        text = result.text.strip()
        if not text:
            return None
        if (
            result.confidence is not None
            and result.confidence < self.minimum_confidence
        ):
            return None
        return TranscriptionResult(text, result.language.strip(), result.confidence)
