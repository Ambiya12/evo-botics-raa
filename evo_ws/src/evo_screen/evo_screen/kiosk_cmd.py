"""Construction pure de la commande chromium pour le kiosk.

Aucune dépendance ROS ni effet de bord : testable sans matériel ni rclpy.
"""

from __future__ import annotations

import shutil

CHROME_CANDIDATES = (
    "chromium-browser",
    "chromium",
    "google-chrome",
    "google-chrome-stable",
)


def find_chromium(candidates=CHROME_CANDIDATES, which=shutil.which):
    """Retourne le chemin du premier binaire chromium/chrome trouvé, sinon None."""
    for name in candidates:
        path = which(name)
        if path:
            return path
    return None


def build_origin(host, port=80):
    """Origine HTTP (sans chemin) — sert au flag --unsafely-treat-insecure-origin-as-secure."""
    return f"http://{host}:{port}"


def build_url(host, port=80, path="/kiosk"):
    """URL complète de la page kiosk."""
    if not path.startswith("/"):
        path = "/" + path
    return f"{build_origin(host, port)}{path}"


def build_chromium_args(chrome, url, *, profile="/tmp/kiosk-chrome", origin=None, disable_gpu=False):
    """Liste d'arguments chromium pour un kiosk plein écran.

    - profil neuf obligatoire pour que --unsafely-treat-insecure-origin-as-secure s'applique
    - --use-fake-ui-for-media-stream auto-accepte la vraie caméra (pas de prompt en kiosk)
    """
    args = [
        chrome,
        "--kiosk",
        "--start-fullscreen",
        "--noerrordialogs",
        "--disable-infobars",
        "--disable-session-crashed-bubble",
        "--disable-features=TranslateUI",
        "--no-first-run",
        "--check-for-update-interval=31536000",
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-ui-for-media-stream",
    ]
    if origin:
        args.append(f"--unsafely-treat-insecure-origin-as-secure={origin}")
    if disable_gpu:
        args.append("--disable-gpu")
    args.append(f"--user-data-dir={profile}")
    args.append(url)
    return args
