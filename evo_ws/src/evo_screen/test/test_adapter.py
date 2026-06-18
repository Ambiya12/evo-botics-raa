from PIL import Image

from evo_screen.lcd_adapter import pil_to_bgr


def test_pil_to_bgr_shape():
    img = Image.new("RGB", (4, 3), (255, 255, 255))
    arr = pil_to_bgr(img)
    assert arr.shape == (3, 4, 3)  # (H, W, C)


def test_pil_to_bgr_channel_order():
    # Rouge pur en RGB -> en BGR le 255 doit être sur le DERNIER canal.
    img = Image.new("RGB", (2, 2), (255, 0, 0))
    arr = pil_to_bgr(img)
    assert int(arr[0, 0, 0]) == 0    # B
    assert int(arr[0, 0, 1]) == 0    # G
    assert int(arr[0, 0, 2]) == 255  # R
