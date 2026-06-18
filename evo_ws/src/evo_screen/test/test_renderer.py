from evo_screen.lcd_renderer import render_welcome


def _dark_pixels(img):
    px = img.load()
    xs, ys = [], []
    for yy in range(img.height):
        for xx in range(img.width):
            if sum(px[xx, yy]) < 60:
                xs.append(xx)
                ys.append(yy)
    return xs, ys


def test_render_welcome_size():
    img = render_welcome(1024, 600, font_path="")
    assert img.size == (1024, 600)


def test_render_welcome_white_background():
    img = render_welcome(1024, 600, font_path="")
    assert img.getpixel((0, 0)) == (255, 255, 255)


def test_render_welcome_draws_dark_text():
    img = render_welcome(1024, 600, font_path="")
    xs, ys = _dark_pixels(img)
    assert xs, "aucun pixel sombre : le texte n'a pas été dessiné"


def test_render_welcome_text_centered():
    img = render_welcome(200, 100, font_path="")
    xs, ys = _dark_pixels(img)
    assert xs and ys
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    assert abs(cx - img.width / 2) <= 12
    assert abs(cy - img.height / 2) <= 12
