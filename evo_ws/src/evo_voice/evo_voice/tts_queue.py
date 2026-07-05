from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from queue import Queue
import subprocess
from threading import Lock, Thread
import time
from typing import Callable, Protocol


IDLE = "idle"
SPEAKING = "speaking"
COMPLETED = "completed"
FAILED = "failed"


@dataclass(frozen=True)
class SpeakRequest:
    text: str


class SpeechPlayer(Protocol):
    def play(self, text: str) -> None:
        """Render and play one utterance, blocking until playback finishes."""


class MockSpeechPlayer:
    """Hardware-free player used by laptop development and tests."""

    def __init__(self) -> None:
        self.played_texts: list[str] = []

    def play(self, text: str) -> None:
        self.played_texts.append(text)


class PiperSpeechPlayer:
    """Sequential Piper renderer and command-line audio player."""

    def __init__(
        self,
        model_path: Path,
        output_path: Path,
        piper_executable: str,
        audio_player_executable: str,
        audio_output_device: str = "",
        cache_directory: Path | None = None,
        prewarm_texts: tuple[str, ...] = (),
        latency_callback: Callable[[str, float], None] | None = None,
    ) -> None:
        self.model_path = model_path
        self.output_path = output_path
        self.piper_executable = piper_executable
        self.audio_player_executable = audio_player_executable
        self.audio_output_device = audio_output_device
        self.cache_directory = cache_directory
        self.latency_callback = latency_callback
        if self.cache_directory is not None:
            self.cache_directory.mkdir(parents=True, exist_ok=True)
            for text in prewarm_texts:
                self._cached_audio_path(text)

    def play(self, text: str) -> None:
        audio_path = (
            self._cached_audio_path(text)
            if self.cache_directory is not None
            else self._render(text, self.output_path)
        )
        playback_started = time.monotonic()
        command = [
            self.audio_player_executable,
            "--no-video",
            "--really-quiet",
        ]
        if self.audio_output_device:
            command.append(f"--audio-device={self.audio_output_device}")
        command.append(str(audio_path))
        subprocess.run(command, check=True)
        self._report_latency(
            "playback_sec", time.monotonic() - playback_started
        )

    def _cached_audio_path(self, text: str) -> Path:
        assert self.cache_directory is not None
        model_stat = self.model_path.stat()
        fingerprint = (
            f"{self.model_path.resolve()}:{model_stat.st_size}:"
            f"{model_stat.st_mtime_ns}:{text}"
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        audio_path = self.cache_directory / f"{digest}.wav"
        if audio_path.is_file() and audio_path.stat().st_size > 0:
            self._report_latency("cache_hit_sec", 0.0)
            return audio_path

        temporary_path = audio_path.with_suffix(".tmp.wav")
        self._render(text, temporary_path)
        temporary_path.replace(audio_path)
        return audio_path

    def _render(self, text: str, output_path: Path) -> Path:
        synthesis_started = time.monotonic()
        subprocess.run(
            [
                self.piper_executable,
                "--model",
                str(self.model_path),
                "--output_file",
                str(output_path),
            ],
            input=text,
            text=True,
            check=True,
        )
        self._report_latency(
            "synthesis_sec", time.monotonic() - synthesis_started
        )
        return output_path

    def _report_latency(self, phase: str, duration: float) -> None:
        if self.latency_callback is not None:
            self.latency_callback(phase, duration)


class QueuedTts:
    """Single-worker speech queue that guarantees non-overlapping playback."""

    def __init__(
        self,
        player: SpeechPlayer,
        status_callback: Callable[[str], None],
    ) -> None:
        self._player = player
        self._status_callback = status_callback
        self._queue: Queue[SpeakRequest | object] = Queue()
        self._stop_token = object()
        self._state_lock = Lock()
        self._stopped = False
        self._worker = Thread(target=self._run, name="evo-tts-worker", daemon=True)
        self._worker.start()
        self._publish_status(IDLE)

    def enqueue(self, request: SpeakRequest) -> None:
        if not request.text.strip():
            raise ValueError("Speak request text must not be empty")
        with self._state_lock:
            if self._stopped:
                raise RuntimeError("TTS queue has stopped")
            self._queue.put(request)

    def wait_until_empty(self) -> None:
        """Wait for queued playback; intended for tests and orderly shutdown."""
        self._queue.join()

    def shutdown(self) -> None:
        with self._state_lock:
            if self._stopped:
                return
            self._stopped = True
            self._queue.put(self._stop_token)
        self._worker.join()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is self._stop_token:
                self._queue.task_done()
                return

            request = item
            try:
                self._publish_status(SPEAKING)
                try:
                    self._player.play(request.text)
                except Exception:
                    self._publish_status(FAILED)
                else:
                    self._publish_status(COMPLETED)
                if self._queue.empty():
                    self._publish_status(IDLE)
            finally:
                self._queue.task_done()

    def _publish_status(self, status: str) -> None:
        self._status_callback(status)
