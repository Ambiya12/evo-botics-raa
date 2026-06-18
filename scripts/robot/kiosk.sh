#!/usr/bin/env bash
#
# kiosk.sh — Affiche la page /kiosk de l'app Laravel en plein écran sur le LCD
# HDMI du robot, à la place du node ROS evo_screen.
#
# À exécuter sur l'HÔTE Jetson (pas dans le conteneur m3pro) : l'hôte possède
# nativement X (:0) et l'accès au /dev/video* de la caméra.
#
# Usage :
#   ./kiosk.sh <ip-laptop>            # ex. ./kiosk.sh 10.10.220.40
#   LAPTOP_IP=10.10.220.40 ./kiosk.sh
#   LAPTOP_IP=... PORT=8000 ./kiosk.sh
#
# Prérequis côté laptop (hôte Laravel) :
#   npm run build                          # build prod (NE PAS lancer `npm run dev`)
#   php artisan serve --host=0.0.0.0 --port=8000
#   + pare-feu ouvert sur le port, laptop et Jetson sur le même réseau.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# config.local.sh peut définir LAPTOP_IP / PORT (non versionné).
# shellcheck source=/dev/null
[ -f "$HERE/config.local.sh" ] && . "$HERE/config.local.sh"

LAPTOP_IP="${1:-${LAPTOP_IP:-}}"
PORT="${PORT:-80}"   # Sail sert l'app sur le port 80 (php artisan serve = 8000)

if [ -z "$LAPTOP_IP" ]; then
  echo "Erreur : IP du laptop manquante." >&2
  echo "Usage : $0 <ip-laptop>   (ou LAPTOP_IP=... $0)" >&2
  exit 1
fi

ORIGIN="http://${LAPTOP_IP}:${PORT}"
URL="${ORIGIN}/kiosk"

export DISPLAY="${DISPLAY:-:0}"

# Trouve un binaire chromium (les noms varient selon les distros).
CHROME=""
for c in chromium-browser chromium google-chrome google-chrome-stable; do
  if command -v "$c" >/dev/null 2>&1; then CHROME="$c"; break; fi
done
if [ -z "$CHROME" ]; then
  echo "Erreur : aucun binaire chromium/chrome trouvé sur l'hôte Jetson." >&2
  echo "Installer : sudo apt-get install -y chromium-browser" >&2
  exit 1
fi

# Autorise les clients X locaux (au cas où) et ferme une éventuelle instance.
xhost +local: >/dev/null 2>&1 || true
pkill -f "user-data-dir=/tmp/kiosk-chrome" >/dev/null 2>&1 || true

# Profil dédié et neuf : --unsafely-treat-insecure-origin-as-secure n'est pris en
# compte qu'avec un --user-data-dir propre.
PROFILE="/tmp/kiosk-chrome"
rm -rf "$PROFILE"

echo "Lancement du kiosk → ${URL} (DISPLAY=${DISPLAY}, ${CHROME})"

exec "$CHROME" \
  --kiosk \
  --start-fullscreen \
  --noerrordialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --no-first-run \
  --check-for-update-interval=31536000 \
  --autoplay-policy=no-user-gesture-required \
  --use-fake-ui-for-media-stream \
  --unsafely-treat-insecure-origin-as-secure="${ORIGIN}" \
  --user-data-dir="${PROFILE}" \
  "${URL}"
