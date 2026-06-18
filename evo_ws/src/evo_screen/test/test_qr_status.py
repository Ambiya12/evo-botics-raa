from evo_screen.qr_status import parse


def test_waiting_maps_to_welcome():
    cmd = parse('{"state":"waiting","message":"x","reservation":null,'
                '"error_code":null,"source":"robot_camera"}')
    assert cmd is not None
    assert cmd.screen == "welcome"
    assert cmd.terminal is False
    assert cmd.reservation == {}


def test_scanned_and_validating_map_to_validating():
    assert parse('{"state":"scanned"}').screen == "validating"
    assert parse('{"state":"validating"}').screen == "validating"


def test_success_is_terminal_and_extracts_reservation():
    cmd = parse('{"state":"success","reservation":{"customer_name":"Jules",'
                '"date":"2026-06-18","start_at":"14:00","end_at":"15:00"}}')
    assert cmd.screen == "success"
    assert cmd.terminal is True
    assert cmd.reservation["customer_name"] == "Jules"


def test_success_without_reservation_gives_empty_dict():
    cmd = parse('{"state":"success","reservation":null}')
    assert cmd.screen == "success"
    assert cmd.reservation == {}


def test_error_is_terminal():
    cmd = parse('{"state":"error","reservation":null}')
    assert cmd.screen == "error"
    assert cmd.terminal is True


def test_guide_maps_to_guide_non_terminal():
    cmd = parse('{"state":"guide"}')
    assert cmd.screen == "guide"
    assert cmd.terminal is False


def test_invalid_json_returns_none():
    assert parse("not json at all") is None


def test_unknown_state_returns_none():
    assert parse('{"state":"dancing"}') is None


def test_missing_state_returns_none():
    assert parse('{"message":"no state here"}') is None
