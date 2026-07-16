# Présentation QR Code — 10 Minutes
## Fichiers, Communication & Dépendances

---

## PLAN DE PRÉSENTATION (10 min)

| Timing | Sujet |
|--------|-------|
| 0:00-0:30 | Vue d'ensemble : les 3 couches |
| 0:30-2:00 | La réservation (Backend → QR code) |
| 2:00-4:00 | Le scan robot (Python) |
| 4:00-6:00 | La validation HTTP (Python → Backend → Python) |
| 6:00-8:00 | Le guidage + dashboard temps réel (Python → Frontend) |
| 8:00-9:00 | Dépendances : pourquoi celles-là |
| 9:00-10:00 | Fichiers de config clés |

---

## VUE D'ENSEMBLE : LES 3 COUCHES

```
┌──────────────────────┐     HTTP POST      ┌──────────────────────┐
│     COUCHE 1         │◄─────────────────►│     COUCHE 2          │
│   ROBOT (Python)     │  /api/reservations │   BACKEND (Laravel)   │
│   ROS2 sur Jetson    │     /validate      │   API REST + MySQL    │
│   Port 9090, 8080    │                    │   Port 8000           │
└──────┬───────────────┘                    └──────────────────────┘
       │
       │ WebSocket (rosbridge)
       │ + HTTP MJPEG (caméra)
       ▼
┌──────────────────────┐
│     COUCHE 3         │
│  FRONTEND (Navigateur)│
│  Dashboard Admin     │  → /admin/robot (React/Inertia)
│  Kiosk Accueil       │  → /kiosk (Livewire/Blade)
│  Réservation         │  → /reservation (Livewire)
└──────────────────────┘
```

---

## ÉTAPE 1 : LA RÉSERVATION (Backend génère le QR)

### Flux

```
Utilisateur (navigateur)
  │
  ▼
/reservation (Livewire)
  │  Remplit formulaire : nom, date, créneau, nb personnes
  ▼
POST /sessions/book → BookingSessionController
  │  Trouve un créneau disponible → crée Reservation (statut: pending)
  ▼
ReservationQrPayload::forReservation($reservation)
  │  Construit le payload JSON : {type, uuid, customer, room, date, times}
  │  Signe avec HMAC-SHA256 (clé = APP_KEY Laravel)
  │  Encode le tout → string JSON signée
  ▼
QrCode::generate() → SVG (QR code visuel)
  │
  ▼
Affiché à l'écran + envoyé par email
```

### Fichiers Backend concernés

| # | Fichier | Rôle |
|---|---------|------|
| 1 | `reservationApp/app/Livewire/Reservation.php` | Formulaire de réservation, appelle `checkAvailability()` |
| 2 | `reservationApp/app/Http/Controllers/BookingSessionController.php` | `bookSession()` → crée la réservation en DB |
| 3 | `reservationApp/app/Models/Reservation.php` | Modèle Eloquent : uuid, statut, room_id, customer_name, validated_at |
| 4 | `reservationApp/app/Models/BookingSession.php` | Créneau horaire d'une salle (date, start_at, end_at) |
| 5 | `reservationApp/app/Models/Room.php` | Salle (name, max_capacity) |
| 6 | `reservationApp/app/Support/ReservationQrPayload.php` | **CRITIQUE** — `forReservation()`, `encode()`, `verify()` |
| 7 | `reservationApp/app/Mail/ReservationConfirmed.php` | Email de confirmation avec QR code |
| 8 | `reservationApp/routes/web.php` | Route `POST /sessions/book` |
| 9 | `reservationApp/resources/views/livewire/reservation.blade.php` | Interface utilisateur (formulaire + QR affiché) |
| 10 | `reservationApp/config/evo.php` | `navigable_room_ids` → salles où le robot peut aller |
| 11 | `reservationApp/.env` | `APP_KEY`, `APP_URL`, `EVO_NAVIGABLE_ROOM_IDS` |

### Ce que contient le QR (format JSON signé)

```json
{
  "type": "reservation",
  "version": 1,
  "uuid": "a1b2c3d4-...",
  "customer": {
    "name": "Jean Dupont",
    "email": "jean@example.com"
  },
  "reservation": {
    "date": "2026-07-08",
    "startTime": "14:00",
    "endTime": "15:00",
    "attendeeCount": 4,
    "room": "Salle 1"
  },
  "signature": "abc123..."  ← HMAC-SHA256 avec APP_KEY
}
```

---

## ÉTAPE 2 : LE ROBOT SCANNE LE QR (Python)

### Flux

```
Caméra physique (Jetson)
  │  Topic ROS2 : /camera/color/image_raw (~30 FPS)
  ▼
qr_scanner_node.py (:90 subscription)
  │  on_image() → décode avec pyzbar ou OpenCV QUIRC
  │  Rate-limiting : max 4 scans/sec, cooldown 2s même QR
  ▼
Publie JSON sur /vision/qr/detections
  │  {
  │    "decoded_text": "eyJ0eXBlIjoicmVzZXJ2YXRpb24i...",
  │    "stamp": {"sec": ..., "nanosec": ...},
  │    "decoder_backend": "pyzbar",
  │    "is_json": true,
  │    "has_uuid": true
  │  }
  ▼
dialogue_manager_node.py (:126 subscription)
  │  on_qr_detection()
  │    → QrScanGate.accept() : vérifie état + anti-doublon + anti-concurrence
  │    → handle_event(QR_DETECTED) : transition vers VERIFYING_QR
  │    → Appel service ValidateQr (call_async, non-bloquant)
  ▼
qr_reservation_bridge_node.py (:114 on_validate_qr)
  │  Reçoit l'appel service → perform_validation()
```

### Fichiers Python concernés

| # | Fichier | Rôle |
|---|---------|------|
| 1 | `evo_vision/evo_vision/qr_scanner_node.py` | Capture caméra → décode QR → publie détection JSON |
| 2 | `evo_vision/evo_vision/image_utils.py` | Utilitaire : ROS2 Image → numpy BGR (format OpenCV) |
| 3 | `evo_reception/evo_reception/dialogue_manager_node.py` | Reçoit /vision/qr/detections → déclenche validation |
| 4 | `evo_reception/evo_reception/dialogue_manager.py` | Machine d'état : transition WAITING_FOR_QR → VERIFYING_QR |
| 5 | `evo_reception/evo_reception/qr_integration.py` | QrScanGate (anti-doublon), extract_decoded_text |
| 6 | `evo_reception/evo_reception/qr_reservation_bridge_node.py` | Service ValidateQr → appel HTTP vers backend |
| 7 | `evo_reception/launch/reception.launch.py` | Paramètre `validation_url` (URL du backend Laravel) |
| 8 | `evo_reception_interfaces/srv/ValidateQr.srv` | Définition du service ROS2 (requête/réponse) |
| 9 | `evo_reception_interfaces/msg/WorkflowStatus.msg` | Message dashboard (session_id, state, outcome) |

---

## ÉTAPE 3 : LA VALIDATION HTTP (Python → Backend → Python)

### Flux

```
qr_reservation_bridge_node.py
  │  perform_validation(qr_payload)
  │    → post_json(validation_url, {"qr_payload": "..."})
  │
  │  ═══════ HTTP POST ═══════
  ▼
Laravel: POST /api/reservations/validate
  │  ReservationController@validateQRCode()
  │    1. ReservationQrPayload::verify() → vérifie signature HMAC
  │    2. Vérifie statut = "pending" (pas déjà utilisé, pas expiré)
  │    3. Vérifie que la room est dans evo.navigable_room_ids (config/evo.php)
  │    4. Marque validated_at = now(), sauvegarde
  │    5. ActivityLog : "reservation.validated"
  │
  │  ═══════ Réponse JSON ═══════
  ▼
qr_reservation_bridge_node.py
  │  Parse la réponse → BridgeValidation
  │  Réponse service ValidateQr → dialogue_manager_node
  │
dialogue_manager_node.py
  │  _on_qr_validation()
  │    → Vérifie request_token (anti-stale callback)
  │    → Vérifie destination_id ∈ allowed_destination_ids
  │    → handle_qr_result(VALID, destination_id="1")
  │      → state = READY_TO_GUIDE
```

### Fichiers Backend concernés

| # | Fichier | Rôle |
|---|---------|------|
| 1 | `reservationApp/routes/api.php` | Route `POST /api/reservations/validate` |
| 2 | `reservationApp/app/Http/Controllers/ReservationController.php` | `validateQRCode()` — la logique de validation |
| 3 | `reservationApp/app/Support/ReservationQrPayload.php` | `verify()` — vérifie signature HMAC-SHA256 |
| 4 | `reservationApp/app/Models/Reservation.php` | Modèle DB : statut (pending→validated), room, customer |
| 5 | `reservationApp/config/evo.php` | `navigable_room_ids` — salles autorisées pour le robot |
| 6 | `reservationApp/app/Models/ActivityLog.php` | Log chaque validation ("reservation.validated") |
| 7 | `reservationApp/.env` | `APP_KEY` (clé HMAC), `APP_URL`, `EVO_NAVIGABLE_ROOM_IDS` |

---

## ÉTAPE 4 : LE GUIDAGE + DASHBOARD TEMPS RÉEL

### Flux

```
dialogue_manager_node.py
  │  state = READY_TO_GUIDE
  │  → TTS dit : "Je vous emmène à la Salle 1"
  │  → TTS terminé → NavigationDriver.request("1")
  │  → Envoie action GuideToDestination
  ▼
navigation_orchestrator_node.py
  │  accept_goal() → ACCEPT
  │  execute_goal() → gates check + Nav2Navigator.navigate()
  │  Nav2 planifie → contrôle → le robot avance
  ▼
Pendant tout le processus, le dialogue_manager_node publie :
  │  /reception/dialogue/state   : "IDLE" → "WAITING_FOR_QR" → "VERIFYING_QR" → "NAVIGATING" → "ARRIVED"
  │  /reception/workflow/status  : {session_id, state, outcome, destination_id}
  │  /reception/qr/status        : "waiting" → "scanned" → "validating" → "success"
  │
  │  ═══════ rosbridge WebSocket :9090 ═══════
  ▼
Frontend (Navigateur)
  │
  ├─► Dashboard Admin (/admin/robot)
  │     useRosBridge.ts → connexion WebSocket ws://ROBOT_IP:9090
  │     useRobotTelemetry.ts → subscribe /reception/dialogue/state
  │                          → subscribe /amcl_pose, /map, /battery...
  │     RobotContext.tsx → état global, sendGoal(), waypoints
  │     Overview.tsx → affiche caméra + carte + état dialogue + diagnostics
  │
  └─► Kiosk Accueil (/kiosk)
        kiosk-manager.blade.php → connexion WebSocket ws://ROBOT_IP:9090
        KioskManager.php → subscribe /reception/qr/status
        Écrans : welcome → validating → success → guide
```

### Fichiers Python concernés (suite)

| # | Fichier | Rôle |
|---|---------|------|
| 10 | `evo_reception/evo_reception/_navigation_driver.py` | Wrapper ActionClient GuideToDestination |
| 11 | `evo_navigation/evo_navigation/navigation_orchestrator_node.py` | Serveur d'action GuideToDestination |
| 12 | `evo_navigation/evo_navigation/navigation_orchestrator.py` | Logique pure : gates → waypoint → Nav2Navigator |
| 13 | `evo_navigation/config/reception_waypoints.yaml` | Waypoints (salle 1, salle 2, réception) |
| 14 | `evo_navigation/evo_navigation/waypoints.py` | WaypointRegistry (charge YAML) |
| 15 | `evo_web/launch/web_dashboard.launch.py` | Lance rosbridge (9090) + web_server (8080) + arm_relay |
| 16 | `evo_web/evo_web/web_server_node.py` | Sert flux caméra MJPEG sur /camera/stream |
| 17 | `evo_web/evo_web/arm_command_relay_node.py` | Relaie commandes bras du dashboard → driver |

### Fichiers Frontend concernés

| # | Fichier | Rôle |
|---|---------|------|
| 1 | `resources/js/hooks/useRosBridge.ts` | **CRITIQUE** — connexion WebSocket rosbridge, publish/subscribe |
| 2 | `resources/js/hooks/useRobotTelemetry.ts` | Subscribe à tous les topics robot (map, pose, path...) |
| 3 | `resources/js/Components/Robot/RobotContext.tsx` | État React global du robot, config, waypoints, sendGoal() |
| 4 | `resources/js/Components/Robot/CameraPanel.tsx` | Affiche flux MJPEG |
| 5 | `resources/js/Components/Robot/MapCanvas.tsx` | Carte SLAM + pose robot |
| 6 | `resources/js/Layouts/RobotLayout.tsx` | Layout admin avec RobotProvider |
| 7 | `resources/js/Pages/Admin/Robot/Overview.tsx` | Page dashboard admin |
| 8 | `resources/views/livewire/kiosk-manager.blade.php` | **CRITIQUE** — le kiosk d'accueil, WebSocket vers robot |
| 9 | `app/Livewire/KioskManager.php` | Logique Livewire du kiosk |
| 10 | `resources/js/Components/Robot/ConnectionSettings.tsx` | UI admin pour configurer IP/ports robot |

### Fichiers de configuration

| # | Fichier | Contenu clé |
|---|---------|-------------|
| 1 | `reservationApp/.env` | `APP_URL`, `APP_KEY`, `ROBOT_ROSBRIDGE_URL`, `ROBOT_CAMERA_STREAM_URL`, `EVO_NAVIGABLE_ROOM_IDS` |
| 2 | `reservationApp/config/evo.php` | `navigable_room_ids` → quelles salles le robot peut rejoindre |
| 3 | `reservationApp/config/services.php` | `robot.rosbridge_url` (fallback ws://127.0.0.1:9090) |
| 4 | `evo_reception/launch/reception.launch.py:12` | `validation_url` → URL du backend Laravel |
| 5 | `evo_navigation/config/reception_waypoints.yaml` | Coordonnées (x,y,yaw) de chaque salle |
| 6 | `evo_reception_interfaces/srv/ValidateQr.srv` | Contrat du service de validation QR |
| 7 | `evo_reception_interfaces/action/GuideToDestination.action` | Contrat de l'action de navigation |
| 8 | `evo_reception_interfaces/msg/WorkflowStatus.msg` | Contrat du statut dashboard |
| 9 | `evo_web/launch/web_dashboard.launch.py` | Ports rosbridge (9090) et HTTP (8080) |

---

## RÉSUMÉ : 33 FICHIERS IMPLIQUÉS DANS LE FLUX QR

### Python (17 fichiers)
```
evo_vision/qr_scanner_node.py
evo_vision/image_utils.py
evo_reception/dialogue_manager_node.py
evo_reception/dialogue_manager.py
evo_reception/qr_integration.py
evo_reception/qr_reservation_bridge_node.py
evo_reception/_navigation_driver.py
evo_reception/launch/reception.launch.py
evo_reception_interfaces/srv/ValidateQr.srv
evo_reception_interfaces/msg/WorkflowStatus.msg
evo_reception_interfaces/action/GuideToDestination.action
evo_navigation/navigation_orchestrator_node.py
evo_navigation/navigation_orchestrator.py
evo_navigation/waypoints.py
evo_navigation/config/reception_waypoints.yaml
evo_web/web_server_node.py
evo_web/launch/web_dashboard.launch.py
```

### Backend Laravel (11 fichiers)
```
routes/api.php
routes/web.php
app/Http/Controllers/ReservationController.php
app/Http/Controllers/BookingSessionController.php
app/Models/Reservation.php
app/Models/BookingSession.php
app/Models/Room.php
app/Models/ActivityLog.php
app/Support/ReservationQrPayload.php
app/Livewire/Reservation.php
app/Livewire/KioskManager.php
```

### Frontend (6 fichiers)
```
resources/js/hooks/useRosBridge.ts
resources/js/hooks/useRobotTelemetry.ts
resources/js/Components/Robot/RobotContext.tsx
resources/js/Components/Robot/CameraPanel.tsx
resources/js/Pages/Admin/Robot/Overview.tsx
resources/views/livewire/kiosk-manager.blade.php
```

### Configuration (7 fichiers)
```
reservationApp/.env
reservationApp/config/evo.php
reservationApp/config/services.php
evo_reception/launch/reception.launch.py
evo_navigation/config/reception_waypoints.yaml
evo_web/launch/web_dashboard.launch.py
evo_reception_interfaces/srv/ValidateQr.srv
```

---

## TABLEAU DES COMMUNICATIONS

| Qui → Qui | Protocole | Port | Fichier Python | Fichier Externe |
|-----------|-----------|------|----------------|-----------------|
| Robot → Backend | HTTP POST | 8000 | `qr_reservation_bridge_node.py:136` | `ReservationController.php` |
| Robot → Dashboard | WebSocket (rosbridge) | 9090 | topics ROS2 → rosbridge | `useRosBridge.ts` (subscribe) |
| Robot → Navigateur | HTTP MJPEG | 8080 | `web_server_node.py:39` | `CameraPanel.tsx` / `<img>` |
| Dashboard → Robot | WebSocket (rosbridge) | 9090 | `arm_command_relay_node.py:34` | `ArmControlPanel.tsx` (publish) |
| Dashboard → Robot | WebSocket (rosbridge) | 9090 | `navigation_orchestrator_node.py:131` | `RobotContext.tsx:sendGoal()` |
| Kiosk → Robot | WebSocket (rosbridge) | 9090 | `/reception/qr/status` topic | `kiosk-manager.blade.php` (subscribe) |

---

## POURQUOI CES DÉPENDANCES — DÉFENSE

### 1. Pourquoi `pyzbar` plutôt que `zxing-cpp` ?

```
pyzbar (utilisé)          vs    zxing-cpp (alternative)
────────────────────            ──────────────────────
pip install pyzbar              pip install zxing-cpp
Wrapper Python de libzbar       Binding Python de la lib C++ ZXing
Installation : 1 commande       Installation : nécessite cmake + compilateur C++
Taille : ~200 Ko                Taille : ~5 Mo (bibliothèque compilée)
Fonctionne sur ARM (Jetson)     Compilation croisée complexe sur ARM
```

**Pourquoi pyzbar :** La Jetson est une carte ARM avec un espace disque limité (carte SD). `pyzbar` est un pur wrapper Python de `libzbar` — pas de compilation nécessaire. `zxing-cpp` nécessite cmake et un compilateur C++, ce qui complique le déploiement Docker sur ARM. Et OpenCV QUIRC est le fallback intégré "gratuit" si pyzbar n'est pas installé.

### 2. Pourquoi `urllib` (stdlib) plutôt que `requests` ?

```python
# urllib (utilisé) — 0 dépendance
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# requests (alternative) — 1 dépendance + 4 sous-dépendances
import requests  # → urllib3, certifi, charset-normalizer, idna
```

**Pourquoi urllib :** On fait UN SEUL appel HTTP (POST vers `/api/reservations/validate`). `requests` est une bibliothèque de 5000 lignes qui dépend de 4 autres packages. Sur une Jetson avec une image Docker minimale, chaque dépendance compte. `urllib` est dans la stdlib Python — zéro installation, zéro conflit de version. Pour un seul endpoint POST, `requests` n'apporte rien que `urllib` ne fasse déjà.

### 3. Pourquoi `http.server` (stdlib) plutôt que Flask/FastAPI ?

```
http.server (utilisé)       vs    Flask (alternative)     vs    FastAPI
───────────────────              ──────────────                ───────
stdlib Python                    pip install flask             pip install fastapi
0 dépendance                     ~5 dépendances                ~10 dépendances
2 routes (snapshot, stream)      Routing, templates, etc.      Async, validation, docs
ThreadingHTTPServer intégré      Nécessite WSGI (gunicorn)     Nécessite ASGI (uvicorn)
```

**Pourquoi http.server :** Le serveur web du robot sert 2 routes : `/camera/snapshot` (JPEG) et `/camera/stream` (MJPEG). Pas de routing complexe, pas d'API REST, pas d'auth. `http.server` fait exactement ce dont on a besoin en 50 lignes. Flask ajouterait 5 dépendances pour... servir 2 routes. FastAPI ajouterait 10 dépendances + un serveur ASGI. C'est du YAGNI : on n'a pas besoin d'un framework web pour servir des images.

### 4. Pourquoi `faster-whisper` plutôt que Google Speech-to-Text API ?

```
faster-whisper (utilisé)    vs    Google STT API (alternative)
───────────────────────           ─────────────────────────
Local, offline                   Cloud, nécessite Internet
Gratuit                          Payant par requête
Latence : ~200ms                 Latence : ~500ms + réseau
Respecte la vie privée           Données audio envoyées à Google
```

**Pourquoi faster-whisper :** Le robot doit fonctionner même sans Internet (site isolé, panne réseau). faster-whisper tourne en local sur la Jetson. Pas de latence réseau, pas de coût par requête, et les données vocales restent sur le robot (RGPD). L'inconvénient : précision légèrement inférieure à l'API Google, mais suffisante pour un accueil (intentions simples : oui/non/réservation/annuler).

### 5. Pourquoi `Piper TTS` plutôt que ElevenLabs API ?

```
Piper TTS (utilisé)         vs    ElevenLabs (alternative)
──────────────────                ────────────────────
Local, offline                    Cloud, nécessite Internet
Gratuit                           Payant par caractère
Latence : ~50ms                   Latence : ~500ms + réseau
Voix moins naturelles             Voix ultra-réalistes
```

**Pourquoi Piper TTS :** Même raison que faster-whisper — fonctionnement hors-ligne obligatoire. Pour dire "Bonjour, montrez votre QR code", une voix synthétique locale est amplement suffisante. On n'a pas besoin d'une voix de narrateur de documentaire. Piper fait 50 Mo sur disque, ElevenLabs coûte par requête et nécessite Internet.

### 6. Pourquoi ROS2 Humble plutôt que ROS1 ?

```
ROS2 Humble (utilisé)       vs    ROS1 Noetic (alternative)
────────────────────              ────────────────────
Supporté jusqu'en 2027            Fin de vie : 2025
QoS configurable                  QoS fixe
Multi-plateforme (Linux/Mac/Win)  Linux uniquement
Sécurité (DDS-Security)           Pas de sécurité native
Python 3                          Python 2 (ROS1) ou 3
```

**Pourquoi ROS2 :** ROS1 est en fin de vie (EOL mai 2025). ROS2 Humble a un support long-terme jusqu'en 2027. Les QoS configurables sont critiques : on utilise `BEST_EFFORT` pour la caméra (perte acceptable) et `RELIABLE + TRANSIENT_LOCAL` pour les états du dialogue (le dashboard doit recevoir le dernier état même en se connectant en retard). Impossible en ROS1.

---

## RÉPONSE TYPE POUR L'ORAL (10 min)

**0:00 — Introduction (30 sec) :**
> « Je vais vous présenter le flux QR code complet, qui traverse les trois couches de l'architecture : le robot en Python/ROS2, le backend Laravel, et le frontend navigateur. Voici les 41 fichiers impliqués. »

**0:30 — La réservation (1 min 30) :**
> « Tout commence quand un utilisateur réserve une salle sur /reservation. Le Livewire component appelle BookingSessionController qui crée une Reservation en base avec statut 'pending'. ReservationQrPayload génère un payload JSON signé en HMAC-SHA256 avec la clé APP_KEY de Laravel. Ce payload est encodé en QR code SVG et affiché à l'écran. Le fichier clé ici c'est ReservationQrPayload.php — c'est lui qui crée le contrat de confiance entre le backend et le robot. »

**2:00 — Le scan robot (2 min) :**
> « Le visiteur arrive au kiosk et montre son QR. Le qr_scanner_node sur le robot capture les images de la caméra à 30 FPS via le topic /camera/color/image_raw. Il décode avec pyzbar — choisi plutôt que zxing-cpp parce que pyzbar est un pur wrapper Python sans compilation, critique sur architecture ARM Jetson. Le QR décodé est publié en JSON sur /vision/qr/detections. Le dialogue_manager_node le reçoit, vérifie via QrScanGate qu'on est bien en état WAITING_FOR_QR et que ce n'est pas un doublon, puis appelle le service ValidateQr de manière asynchrone. »

**4:00 — La validation HTTP (2 min) :**
> « Le qr_reservation_bridge_node reçoit l'appel service et fait un HTTP POST vers le backend Laravel. J'utilise urllib de la stdlib plutôt que requests parce qu'on fait un seul appel — requests ajouterait 4 dépendances inutiles. Côté Laravel, le ReservationController vérifie la signature HMAC, le statut pending, et que la salle est dans evo.navigable_room_ids défini dans config/evo.php. Si tout est bon, il marque la réservation comme 'validated' et retourne le destination_id. Le robot reçoit la réponse, vérifie que le destination_id est dans sa liste autorisée, et passe en état READY_TO_GUIDE. »

**6:00 — Guidage + Dashboard (2 min) :**
> « Le dialogue manager dit 'Je vous emmène à la Salle 1' via Piper TTS — choisi plutôt qu'ElevenLabs parce que le robot doit fonctionner hors-ligne. Puis il envoie un goal de navigation via l'action GuideToDestination vers navigation_orchestrator_node qui vérifie l'e-stop, la localisation AMCL, et lance Nav2. Pendant tout ce temps, le dialogue manager publie l'état sur /reception/dialogue/state et le statut workflow. Le frontend reçoit tout ça en temps réel via rosbridge sur le port 9090. Le dashboard admin en React/Inertia utilise le hook useRosBridge.ts pour le WebSocket et affiche la position du robot sur une carte SLAM. Le kiosk en Livewire reçoit /reception/qr/status et affiche les écrans successifs : accueil → validation → succès → suivez-moi. »

**8:00 — Dépendances (1 min) :**
> « Chaque dépendance a été choisie pour une raison précise. urllib plutôt que requests : zéro dépendance, un seul endpoint. pyzbar plutôt que zxing-cpp : pas de compilation sur ARM. http.server plutôt que Flask : 2 routes, pas besoin d'un framework. faster-whisper et Piper TTS plutôt que des API cloud : le robot doit fonctionner hors-ligne, sans latence réseau, et dans le respect du RGPD. ROS2 Humble plutôt que ROS1 : support LTS jusqu'en 2027 et QoS configurables essentiels pour le dashboard temps réel. »

**9:00 — Config (1 min) :**
> « Enfin, les 7 fichiers de configuration qui font le lien entre les couches : le .env Laravel avec APP_URL, APP_KEY, ROBOT_ROSBRIDGE_URL ; config/evo.php pour les salles navigables ; reception.launch.py pour l'URL du backend côté robot ; reception_waypoints.yaml pour les coordonnées physiques des salles. Ces fichiers sont le 'câblage' qui permet aux trois couches de se parler sans être couplées en dur dans le code. »
