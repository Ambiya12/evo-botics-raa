"""Rendu pur d'une image 'Welcome' centrée (fond blanc, texte noir). Sans ROS ni matériel."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _load_font(font_path: str, font_size: int):
    if font_path:
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            pass  # TTF absente -> fallback police bitmap par défaut (petite)
    return ImageFont.load_default()


def render_welcome(width: int = 1024, height: int = 600, text: str = "Welcome",
                   font_path: str = DEFAULT_FONT_PATH, font_size: int = 120) -> Image.Image:
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = _load_font(font_path, font_size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w = right - left
    text_h = bottom - top
    x = (width - text_w) / 2 - left
    y = (height - text_h) / 2 - top
    draw.text((x, y), text, font=font, fill=(0, 0, 0))
    return image
