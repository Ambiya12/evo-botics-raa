"""Rendus purs des écrans du kiosk (statiques, anglais en dur). Sans ROS ni matériel."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

WHITE = (255, 255, 255)
GREEN_BG = (240, 253, 244)
RED_BG = (254, 242, 242)
BLACK = (17, 24, 39)
GREEN_FG = (22, 163, 74)
RED_FG = (220, 38, 38)


def _load_font(font_path: str, font_size: int):
    if font_path:
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            pass  # TTF absente -> fallback police bitmap par défaut
    return ImageFont.load_default()


def _draw_centered_text(draw, text, font, fill, cx, cy):
    """Dessine `text` centré sur (cx, cy)."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    w, h = right - left, bottom - top
    draw.text((cx - w / 2 - left, cy - h / 2 - top), text, font=font, fill=fill)


def _draw_lines(draw, lines, width, y_start, fill):
    """Dessine une pile de lignes (texte, police) centrées horizontalement, empilées depuis y_start.
    Retourne le y du bas du bloc."""
    y = y_start
    for text, font in lines:
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        h = bottom - top
        _draw_centered_text(draw, text, font, fill, width / 2, y + h / 2)
        y += h + max(8, h // 4)
    return y


def _check(draw, cx, cy, size, fill):
    """Coche ✓ dessinée en primitives (indépendant de la police)."""
    w = max(4, int(size // 8))
    draw.line([(int(cx - size * 0.4), int(cy)), (int(cx - size * 0.1), int(cy + size * 0.35)),
               (int(cx + size * 0.45), int(cy - size * 0.4))], fill=fill, width=w, joint="curve")


def _cross(draw, cx, cy, size, fill):
    """Croix ✗ dessinée en primitives."""
    w = max(4, int(size // 8))
    d = size * 0.4
    draw.line([(int(cx - d), int(cy - d)), (int(cx + d), int(cy + d))], fill=fill, width=w)
    draw.line([(int(cx - d), int(cy + d)), (int(cx + d), int(cy - d))], fill=fill, width=w)


def _arrow(draw, cx, cy, size, fill):
    """Flèche statique vers la droite, en primitives."""
    w = max(4, int(size // 8))
    draw.line([(int(cx - size * 0.5), int(cy)), (int(cx + size * 0.4), int(cy))], fill=fill, width=w)
    draw.line([(int(cx + size * 0.4), int(cy)), (int(cx + size * 0.1), int(cy - size * 0.3))], fill=fill, width=w)
    draw.line([(int(cx + size * 0.4), int(cy)), (int(cx + size * 0.1), int(cy + size * 0.3))], fill=fill, width=w)


def render_welcome(width: int = 1024, height: int = 600, *,
                   font_path: str = DEFAULT_FONT_PATH, font_size: int = 96) -> Image.Image:
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)
    small = _load_font(font_path, max(12, font_size // 2))
    big = _load_font(font_path, font_size)
    lines = [
        ("Welcome to", small),
        ("EVOBOTICS", big),
        ("Please show me your reservation QR code...", small),
    ]
    _draw_lines(draw, lines, width, height * 0.32, BLACK)
    return image


def render_validating(width: int = 1024, height: int = 600, *,
                      font_path: str = DEFAULT_FONT_PATH, font_size: int = 96) -> Image.Image:
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)
    big = _load_font(font_path, max(24, font_size // 2))
    small = _load_font(font_path, max(12, font_size // 3))
    _draw_lines(draw, [("Validation in progress...", big), ("Please wait...", small)],
                width, height * 0.4, BLACK)
    return image


def render_success(reservation: dict, width: int = 1024, height: int = 600, *,
                   font_path: str = DEFAULT_FONT_PATH, font_size: int = 96) -> Image.Image:
    image = Image.new("RGB", (width, height), GREEN_BG)
    draw = ImageDraw.Draw(image)
    sym = min(width, height) * 0.18
    _check(draw, width / 2, height * 0.28, sym, GREEN_FG)
    big = _load_font(font_path, max(24, font_size // 2))
    small = _load_font(font_path, max(12, font_size // 3))
    y = _draw_lines(
        draw,
        [("Success", big),
         ("Your reservation has been successfully validated!", small)],
        width, height * 0.45, BLACK,
    )
    fields = [reservation.get(k) for k in ("customer_name", "date", "start_at", "end_at")]
    fields = [str(f) for f in fields if f]
    if fields:
        info = " • ".join(fields[:2])
        if len(fields) > 2:
            info += "  " + " — ".join(fields[2:])
        _draw_centered_text(draw, info, small, BLACK, width / 2, y + 20)
    return image


def render_error(width: int = 1024, height: int = 600, *,
                 font_path: str = DEFAULT_FONT_PATH, font_size: int = 96) -> Image.Image:
    image = Image.new("RGB", (width, height), RED_BG)
    draw = ImageDraw.Draw(image)
    sym = min(width, height) * 0.18
    _cross(draw, width / 2, height * 0.28, sym, RED_FG)
    big = _load_font(font_path, max(24, font_size // 2))
    small = _load_font(font_path, max(12, font_size // 3))
    _draw_lines(
        draw,
        [("Error", big),
         ("Your QR code is invalid or expired.", small),
         ("Please verify with my colleagues!", small)],
        width, height * 0.45, BLACK,
    )
    return image


def render_guide(width: int = 1024, height: int = 600, *,
                 font_path: str = DEFAULT_FONT_PATH, font_size: int = 96) -> Image.Image:
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)
    sym = min(width, height) * 0.18
    _arrow(draw, width / 2, height * 0.3, sym, BLACK)
    big = _load_font(font_path, max(24, font_size // 2))
    small = _load_font(font_path, max(12, font_size // 3))
    _draw_lines(draw, [("Please follow me!", big), ("I will drive you to your room", small)],
                width, height * 0.48, BLACK)
    return image
