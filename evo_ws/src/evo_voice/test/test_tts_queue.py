from pathlib import Path
from threading import Event, Lock
from unittest.mock import call, patch

from evo_voice.tts_queue import (
    COMPLETED,
    FAILED,
    IDLE,
    SPEAKING,
    PiperSpeechPlayer,
    QueuedTts,
    SpeakRequest,
)


class BlockingPlayer:
    def __init__(self) -> None:
        self.first_started = Event()
        self.release_first = Event()
        self.played_texts: list[str] = []
        self.active = 0
        self.maximum_active = 0
        self._lock = Lock()

    def play(self, text: str) -> None:
        with self._lock:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            self.played_texts.append(text)
        if text == "first":
            self.first_started.set()
            assert self.release_first.wait(timeout=1.0)
        with self._lock:
            self.active -= 1


class FailingPlayer:
    def play(self, text: str) -> None:
        raise RuntimeError("playback failed")


class RecordingPlayer:
    def __init__(self) -> None:
        self.played_texts: list[str] = []

    def play(self, text: str) -> None:
        self.played_texts.append(text)


def test_requests_play_in_order_without_overlap() -> None:
    player = BlockingPlayer()
    statuses: list[str] = []
    queue = QueuedTts(player, statuses.append)
    try:
        queue.enqueue(SpeakRequest("first"))
        assert player.first_started.wait(timeout=1.0)
        queue.enqueue(SpeakRequest("second"))
        player.release_first.set()
        queue.wait_until_empty()

        assert player.played_texts == ["first", "second"]
        assert player.maximum_active == 1
        assert statuses == [
            IDLE,
            SPEAKING,
            COMPLETED,
            SPEAKING,
            COMPLETED,
            IDLE,
        ]
    finally:
        player.release_first.set()
        queue.shutdown()


def test_player_publishes_completed_statuses() -> None:
    player = RecordingPlayer()
    statuses: list[str] = []
    queue = QueuedTts(player, statuses.append)
    try:
        queue.enqueue(SpeakRequest("hello"))
        queue.wait_until_empty()

        assert player.played_texts == ["hello"]
        assert statuses == [IDLE, SPEAKING, COMPLETED, IDLE]
    finally:
        queue.shutdown()


def test_playback_failure_publishes_failed_then_idle() -> None:
    statuses: list[str] = []
    queue = QueuedTts(FailingPlayer(), statuses.append)
    try:
        queue.enqueue(SpeakRequest("failure"))
        queue.wait_until_empty()

        assert statuses == [IDLE, SPEAKING, FAILED, IDLE]
    finally:
        queue.shutdown()


def test_piper_player_uses_configured_audio_output_without_hardware() -> None:
    player = PiperSpeechPlayer(
        model_path=Path("/models/voice.onnx"),
        output_path=Path("/tmp/evo_voice_tts.wav"),
        piper_executable="piper",
        audio_player_executable="mpv",
        audio_output_device="alsa/default",
    )

    with patch("evo_voice.tts_queue.subprocess.run") as run:
        player.play("Hello")

    assert run.call_args_list == [
        call(
            [
                "piper",
                "--model",
                "/models/voice.onnx",
                "--output_file",
                "/tmp/evo_voice_tts.wav",
            ],
            input="Hello",
            text=True,
            check=True,
            timeout=30.0,
        ),
        call(
            [
                "mpv",
                "--no-video",
                "--really-quiet",
                "--audio-device=alsa/default",
                "/tmp/evo_voice_tts.wav",
            ],
            check=True,
            timeout=30.0,
        ),
    ]


def test_playback_timeout_is_reported_and_next_request_still_runs() -> None:
    player = RecordingPlayer()
    errors: list[tuple[SpeakRequest, Exception]] = []
    statuses: list[str] = []

    class TimeoutOncePlayer:
        def __init__(self) -> None:
            self.calls = 0

        def play(self, text: str) -> None:
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("playback timed out")
            player.play(text)

    queue = QueuedTts(
        TimeoutOncePlayer(),
        statuses.append,
        lambda request, error: errors.append((request, error)),
    )
    try:
        queue.enqueue(SpeakRequest("first", "tts-1"))
        queue.enqueue(SpeakRequest("second", "tts-2"))
        queue.wait_until_empty()
    finally:
        queue.shutdown()

    assert len(errors) == 1
    assert errors[0][0].request_id == "tts-1"
    assert player.played_texts == ["second"]
    assert FAILED in statuses
    assert statuses[-1] == IDLE


def test_piper_player_prewarms_and_reuses_cached_phrase(tmp_path: Path) -> None:
    model_path = tmp_path / "voice.onnx"
    model_path.write_bytes(b"model")
    cache_directory = tmp_path / "cache"

    def fake_run(command, **kwargs):
        if command[0] == "piper":
            Path(command[-1]).write_bytes(b"wav")

    with patch(
        "evo_voice.tts_queue.subprocess.run", side_effect=fake_run
    ) as run:
        player = PiperSpeechPlayer(
            model_path=model_path,
            output_path=tmp_path / "fallback.wav",
            piper_executable="piper",
            audio_player_executable="mpv",
            cache_directory=cache_directory,
            prewarm_texts=("Hello",),
        )
        player.play("Hello")
        player.play("Hello")

    piper_calls = [
        item for item in run.call_args_list if item.args[0][0] == "piper"
    ]
    mpv_calls = [
        item for item in run.call_args_list if item.args[0][0] == "mpv"
    ]
    assert len(piper_calls) == 1
    assert len(mpv_calls) == 2
