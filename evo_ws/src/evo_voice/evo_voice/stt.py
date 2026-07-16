from __future__ import annotations

from array import array
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
import math
from pathlib import Path
import sys
from threading import Event, Lock
import time
from typing import Callable, Protocol
import wave


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    confidence: float | None = None


class ListeningMode(str, Enum):
    DISABLED = "disabled"
    WAKE = "wake"
    ANSWER = "answer"
    QR = "qr"


@dataclass(frozen=True)
class CaptureToken:
    dialogue_epoch: int
    tts_epoch: int


class Transcriber(Protocol):
    def transcribe(self, wav_data: bytes) -> TranscriptionResult:
        """Transcribe one complete WAV recording."""


class CaptureGate:
    """Rejects audio across TTS cycles and dialogue-state transitions."""

    def __init__(
        self,
        initial_mode: ListeningMode = ListeningMode.ANSWER,
    ) -> None:
        self._tts_speaking = Event()
        self._lock = Lock()
        self._tts_epoch = 0
        self._dialogue_epoch = 0
        self._listening_mode = initial_mode
        self._last_completed_at: float | None = None

    @property
    def paused(self) -> bool:
        with self._lock:
            return (
                self._tts_speaking.is_set()
                or self._listening_mode == ListeningMode.DISABLED
            )

    @property
    def listening_mode(self) -> ListeningMode:
        with self._lock:
            return self._listening_mode

    def capture_token(self) -> CaptureToken:
        with self._lock:
            return CaptureToken(self._dialogue_epoch, self._tts_epoch)

    def allows(self, capture_token: CaptureToken) -> bool:
        with self._lock:
            return (
                not self._tts_speaking.is_set()
                and self._listening_mode != ListeningMode.DISABLED
                and capture_token.dialogue_epoch == self._dialogue_epoch
                and capture_token.tts_epoch == self._tts_epoch
            )

    def recoverable_audio_offset(
        self,
        capture_token: CaptureToken,
        capture_started_at: float,
    ) -> float | None:
        """Return the human-only suffix offset for one TTS-overlapped capture.

        A blocking microphone read may begin just before TTS starts and finish
        after the visitor answers. In that case the prefix contains robot
        speech, but audio after TTS completion is safe to transcribe.
        """
        with self._lock:
            if (
                self._tts_speaking.is_set()
                or self._listening_mode == ListeningMode.DISABLED
                or capture_token.dialogue_epoch != self._dialogue_epoch
            ):
                return None
            if capture_token.tts_epoch == self._tts_epoch:
                return 0.0
            if (
                capture_token.tts_epoch == self._tts_epoch - 1
                and self._last_completed_at is not None
            ):
                return max(0.0, self._last_completed_at - capture_started_at)
            return None

    def update_dialogue_state(self, state: str) -> ListeningMode:
        normalized = state.strip().upper()
        mode = {
            "PRESENCE_ARMED": ListeningMode.WAKE,
            "WAITING_FOR_INTENT": ListeningMode.ANSWER,
            "WAITING_FOR_QR": ListeningMode.QR,
        }.get(normalized, ListeningMode.DISABLED)
        with self._lock:
            if mode != self._listening_mode:
                self._dialogue_epoch += 1
                self._listening_mode = mode
        return mode

    def rejection_reason(self, capture_token: CaptureToken) -> str | None:
        with self._lock:
            if self._tts_speaking.is_set():
                return "tts_suppressed"
            if self._listening_mode == ListeningMode.DISABLED:
                return "dialogue_disabled"
            if capture_token.dialogue_epoch != self._dialogue_epoch:
                return "stale_dialogue_state"
            if capture_token.tts_epoch != self._tts_epoch:
                return "stale_tts_cycle"
            return None

    def update_tts_status(self, status: str) -> None:
        normalized = status.strip().lower()
        if normalized == "speaking":
            with self._lock:
                if not self._tts_speaking.is_set():
                    self._tts_epoch += 1
                self._tts_speaking.set()
        elif normalized in {"idle", "completed", "failed"}:
            with self._lock:
                self._tts_speaking.clear()
                self._last_completed_at = time.monotonic()


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
    """VAD/transcription pipeline with TTS capture gating."""

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

    def process(
        self,
        wav_data: bytes,
        capture_token: CaptureToken | None = None,
        capture_started_at: float | None = None,
    ) -> TranscriptionResult | None:
        token = (
            self.capture_gate.capture_token()
            if capture_token is None
            else capture_token
        )
        if capture_started_at is None:
            if not self.capture_gate.allows(token):
                return None
        else:
            offset = self.capture_gate.recoverable_audio_offset(
                token, capture_started_at
            )
            if offset is None:
                return None
            if offset > 0.0:
                wav_data = trim_wav_prefix(wav_data, offset)
        if not self.vad.contains_speech(wav_data):
            return None

        try:
            result = self.transcriber.transcribe(wav_data)
        except Exception as exc:
            if self.error_callback is not None:
                self.error_callback(exc)
            return None

        # TTS may have started while transcription was running. A recovered
        # one-epoch overlap remains valid; any newer speech invalidates it.
        if capture_started_at is None:
            capture_still_valid = self.capture_gate.allows(token)
        else:
            capture_still_valid = (
                self.capture_gate.recoverable_audio_offset(
                    token, capture_started_at
                )
                is not None
            )
        if not capture_still_valid:
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


def trim_wav_prefix(wav_data: bytes, seconds: float) -> bytes:
    """Remove a duration from a PCM WAV while preserving its format."""
    if seconds <= 0.0:
        return wav_data
    try:
        with wave.open(BytesIO(wav_data), "rb") as source:
            parameters = source.getparams()
            frames_to_skip = min(
                source.getnframes(),
                int(seconds * source.getframerate()),
            )
            source.setpos(frames_to_skip)
            remaining = source.readframes(source.getnframes() - frames_to_skip)
    except (EOFError, wave.Error):
        return b""

    output = BytesIO()
    with wave.open(output, "wb") as target:
        target.setparams(parameters)
        target.writeframes(remaining)
    return output.getvalue()
