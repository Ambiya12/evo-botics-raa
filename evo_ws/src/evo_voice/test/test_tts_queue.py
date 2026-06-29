from threading import Event, Lock

from evo_voice.tts_queue import (
    COMPLETED,
    FAILED,
    IDLE,
    SPEAKING,
    MockSpeechPlayer,
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
        raise RuntimeError("mock playback failed")


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


def test_mock_player_publishes_completed_statuses() -> None:
    player = MockSpeechPlayer()
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
