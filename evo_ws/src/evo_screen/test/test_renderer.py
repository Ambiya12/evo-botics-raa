from evo_screen.lcd_renderer import (
    render_welcome, render_validating, render_success, render_error, render_guide,
    WHITE, GREEN_BG, RED_BG,
)


def _count_non_bg(img, bg):
    px = img.load()
    n = 0
    for yy in range(img.height):
        for xx in range(img.width):
            if px[xx, yy] != bg:
                n += 1
    return n


# --- welcome (fond blanc) ---
def test_welcome_size_and_white_bg():
    img = render_welcome(1024, 600, font_path="")
    assert img.size == (1024, 600)
    assert img.getpixel((0, 0)) == WHITE


def test_welcome_draws_content():
    img = render_welcome(1024, 600, font_path="")
    assert _count_non_bg(img, WHITE) > 0


# --- validating (fond blanc) ---
def test_validating_white_bg_and_content():
    img = render_validating(1024, 600, font_path="")
    assert img.size == (1024, 600)
    assert img.getpixel((0, 0)) == WHITE
    assert _count_non_bg(img, WHITE) > 0


# --- success (fond vert) ---
def test_success_green_bg_and_content():
    img = render_success(
        {"customer_name": "Jules", "date": "2026-06-18",
         "start_at": "14:00", "end_at": "15:00"},
        1024, 600, font_path="",
    )
    assert img.size == (1024, 600)
    assert img.getpixel((0, 0)) == GREEN_BG
    assert _count_non_bg(img, GREEN_BG) > 0


def test_success_partial_reservation_no_exception():
    img = render_success({"customer_name": "Jules"}, 1024, 600, font_path="")
    assert img.size == (1024, 600)


def test_success_empty_reservation_no_exception():
    img = render_success({}, 1024, 600, font_path="")
    assert img.size == (1024, 600)


# --- error (fond rouge) ---
def test_error_red_bg_and_content():
    img = render_error(1024, 600, font_path="")
    assert img.size == (1024, 600)
    assert img.getpixel((0, 0)) == RED_BG
    assert _count_non_bg(img, RED_BG) > 0


# --- guide (fond blanc) ---
def test_guide_white_bg_and_content():
    img = render_guide(1024, 600, font_path="")
    assert img.size == (1024, 600)
    assert img.getpixel((0, 0)) == WHITE
    assert _count_non_bg(img, WHITE) > 0
