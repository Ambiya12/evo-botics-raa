from evo_screen.display_state import DisplayState


def test_initially_inactive():
    s = DisplayState()
    assert not s.active
    assert not s.should_clear(100.0)


def test_request_activates_with_deadline():
    s = DisplayState()
    s.request(now=100.0, duration=10.0)
    assert s.active
    assert not s.should_clear(105.0)
    assert s.should_clear(110.0)


def test_request_extends_deadline():
    s = DisplayState()
    s.request(now=100.0, duration=10.0)
    s.request(now=105.0, duration=10.0)  # un 2e appel prolonge
    assert not s.should_clear(110.0)
    assert s.should_clear(115.0)


def test_mark_cleared_deactivates():
    s = DisplayState()
    s.request(now=100.0, duration=10.0)
    s.mark_cleared()
    assert not s.active
    assert not s.should_clear(200.0)
