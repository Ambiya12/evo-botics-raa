"""Tests purs de la construction de commande kiosk (sans ROS ni matériel)."""

from evo_screen.kiosk_cmd import build_chromium_args, build_origin, build_url, find_chromium


def test_build_url_default():
    assert build_url("10.0.0.5") == "http://10.0.0.5:80/kiosk"


def test_build_url_custom_port_and_path():
    assert build_url("host", 8000, "/x") == "http://host:8000/x"


def test_build_url_adds_leading_slash():
    assert build_url("h", 80, "kiosk") == "http://h:80/kiosk"


def test_build_origin():
    assert build_origin("h", 8000) == "http://h:8000"


def test_args_contain_kiosk_origin_and_url_last():
    args = build_chromium_args("/usr/bin/chromium", "http://h/kiosk", origin="http://h")
    assert args[0] == "/usr/bin/chromium"
    assert "--kiosk" in args
    assert "--use-fake-ui-for-media-stream" in args
    assert "--unsafely-treat-insecure-origin-as-secure=http://h" in args
    assert args[-1] == "http://h/kiosk"


def test_args_no_origin_when_none():
    args = build_chromium_args("c", "u")
    assert not any(a.startswith("--unsafely-treat-insecure-origin-as-secure") for a in args)


def test_args_disable_gpu_optional():
    assert "--disable-gpu" not in build_chromium_args("c", "u")
    assert "--disable-gpu" in build_chromium_args("c", "u", disable_gpu=True)


def test_find_chromium_picks_first_available():
    found = find_chromium(("a", "b", "c"), which=lambda n: "/bin/b" if n == "b" else None)
    assert found == "/bin/b"


def test_find_chromium_none_when_absent():
    assert find_chromium(("a", "b"), which=lambda n: None) is None
