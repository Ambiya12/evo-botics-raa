"""Pilotage du LCD HDMI via une fenêtre OpenCV plein écran. Seul point de contact avec cv2."""
from __future__ import annotations

import numpy as np
from PIL import Image

WINDOW_NAME = "evo_screen"


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    """Convertit une image PIL en tableau NumPy BGR (ordre attendu par cv2.imshow). NumPy pur."""
    rgb = np.array(image.convert("RGB"))
    return rgb[:, :, ::-1].copy()  # RGB -> BGR, contigu pour cv2


class HdmiCvAdapter:
    """Fenêtre OpenCV plein écran sur DISPLAY=:0. cv2 importé en lazy."""

    def __init__(self, window_name: str = WINDOW_NAME):
        import cv2  # lazy : garde le module importable sans cv2 pour les tests unitaires
        self._cv2 = cv2
        self._window_name = window_name
        self._open = False

    def show(self, image: Image.Image) -> None:
        cv2 = self._cv2
        if not self._open:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(self._window_name, cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN)
            self._open = True
        cv2.imshow(self._window_name, pil_to_bgr(image))
        cv2.waitKey(1)

    def pump(self) -> None:
        if self._open:
            self._cv2.waitKey(1)

    def clear(self) -> None:
        if self._open:
            self._cv2.destroyWindow(self._window_name)
            self._cv2.waitKey(1)
            self._open = False
