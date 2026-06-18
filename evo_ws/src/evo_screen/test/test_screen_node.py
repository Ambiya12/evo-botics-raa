from evo_screen.screen_controller import ScreenController


class FakeAdapter:
    def __init__(self):
        self.shown = []
        self.pumps = 0
        self.cleared = 0

    def show(self, image):
        self.shown.append(image)

    def pump(self):
        self.pumps += 1

    def clear(self):
        self.cleared += 1


def _make():
    adapter = FakeAdapter()
    ctrl = ScreenController(adapter, width=200, height=100,
                            font_path="", font_size=20, duration=10.0)
    return ctrl, adapter


SUCCESS = ('{"state":"success","message":"ok","reservation":'
           '{"customer_name":"Jules","date":"2026-06-18",'
           '"start_at":"14:00","end_at":"15:00"},'
           '"error_code":null,"source":"robot_camera"}')


def test_show_welcome_displays_once():
    ctrl, adapter = _make()
    ctrl.show_welcome()
    assert len(adapter.shown) == 1


def test_success_shows_and_arms_then_returns_to_welcome():
    ctrl, adapter = _make()
    assert ctrl.on_status(SUCCESS, now=100.0) is True
    assert len(adapter.shown) == 1          # écran success affiché
    ctrl.tick(now=105.0)                    # avant deadline -> pump, pas de nouvel affichage
    assert adapter.pumps == 1
    assert len(adapter.shown) == 1
    ctrl.tick(now=110.0)                    # deadline atteinte -> welcome redessiné
    assert len(adapter.shown) == 2
    assert adapter.cleared == 0             # jamais de clear() (pas d'écran noir)


def test_non_terminal_state_is_persistent():
    ctrl, adapter = _make()
    assert ctrl.on_status('{"state":"validating"}', now=100.0) is True
    ctrl.tick(now=99999.0)                  # jamais de retour auto à welcome
    assert len(adapter.shown) == 1
    assert adapter.pumps == 1


def test_invalid_message_is_ignored():
    ctrl, adapter = _make()
    assert ctrl.on_status("not json", now=100.0) is False
    assert adapter.shown == []


def test_unknown_state_is_ignored():
    ctrl, adapter = _make()
    assert ctrl.on_status('{"state":"dancing"}', now=100.0) is False
    assert adapter.shown == []


def test_terminal_then_non_terminal_disarms():
    ctrl, adapter = _make()
    ctrl.on_status(SUCCESS, now=100.0)               # arme la deadline
    ctrl.on_status('{"state":"waiting"}', now=101.0)  # non-terminal -> désarme
    ctrl.tick(now=200.0)                              # ne doit PAS redessiner welcome
    assert len(adapter.shown) == 2                    # success + waiting, rien de plus


def test_none_adapter_does_not_crash():
    ctrl = ScreenController(None, width=200, height=100, font_path="", font_size=20)
    ctrl.show_welcome()
    assert ctrl.on_status(SUCCESS, now=100.0) is True
    ctrl.tick(now=110.0)
    ctrl.shutdown()


def test_shutdown_clears_adapter():
    ctrl, adapter = _make()
    ctrl.shutdown()
    assert adapter.cleared == 1
