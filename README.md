## Evo-Botics - Autonomous Reception Robot (RAA)

Evo-Botics is a robotics and AI group project developed at HETIC (Web3).
Mission: build an autonomous reception robot for indoor business centers.



## Team Evo-Botics

A multidisciplinary robotics team:

- Ambiya Dimas Galystan

- Anatole Dupuis

- Antoine TU

- Jules Bourrin


## Project Context

The project targets reception and visitor guidance in business centers.
The robot improves visitor flow and reduces front-desk load.

The solution is an autonomous service robot capable of:

- Navigating safely on one floor
- Scanning QR reservations
- Guiding visitors to room waypoints
- Providing a web admin interface and notifications

* * *

## Objectives

### Autonomous Navigation

- SLAM mapping
- Obstacle avoidance
- Optimized path planning

### Voice and Vision

- QR detection and reservation validation
- Speech pipeline (STT -> translation -> TTS)

### Web Interface

- Touchscreen visitor feedback flow
- Admin dashboard via rosbridge
- Monitoring and emergency stop

### Communication

- ROS2 DDS for robot nodes
- WebSocket bridge for UI
- Email/webhook alert pipeline


## Tech Stack

| Layer | Technologies |
| --- | --- |
| Robot OS | ROS2 Humble (Nav2, MoveIt2) |
| Mapping | SLAM Toolbox + LiDAR |
| Vision | OpenCV, YOLOv8 |
| Voice | Whisper, Piper |
| Backend | Python (FastAPI), Webhooks |
| Frontend | React (via Laravel/Inertia) |
| Communication | DDS, rosbridge, Foxglove |
| Hardware | ROSMASTER M3 Pro + Jetson Orin NX |

## Admin Dashboard

The admin dashboard is served via Laravel/Inertia at `/admin`. It runs in mock
mode without a connected robot, providing the operator layout for robot status,
current visitor session, event logs, incidents, and safety actions.

Robot status data goes through a service abstraction in
`apps/frontend/src/services/robotStatusService.ts`. The default
provider uses mock data; swap to a rosbridge provider when the real robot is
available via `setRobotStatusProvider()`.

## Web App — Frontend / Backend

The web app is split into:

| App | Path | Role |
|---|---|---|
| Backend | `apps/backend` | Laravel 12 API, auth, Inertia routes, database |
| Frontend | `apps/frontend` | React, TypeScript, Vite, Tailwind assets |

The frontend and backend are still connected through Laravel Inertia and the Vite manifest. Laravel serves the page shell, while Vite builds `apps/frontend/src/app.tsx` into `apps/backend/public/build`.

## Web App — Dev Docker

L'application web tourne sous Docker via Laravel Sail avec une configuration custom allégée.

**Architecture des services :**

| Service | Image | URL |
|---|---|---|
| `laravel.test` | php:8.5-cli-bookworm (custom) | http://localhost |
| `vite` | node:24-alpine | http://localhost:5173 |
| `mysql` | mysql:8.4 | localhost:3306 |

Open the app through Laravel, not through Vite:

- Dashboard with Docker/Sail: `http://localhost/admin`
- Dashboard with `php artisan serve`: `http://localhost:8000/admin`
- `http://localhost:5173` is only the Vite hot-reload asset server.

**Démarrage :**

```bash
cd apps/backend
./vendor/bin/sail up -d

# Premier démarrage uniquement
./vendor/bin/sail composer install
docker compose exec vite npm install
```

**Commandes npm** (node absent du conteneur PHP) :

```bash
docker compose exec vite npm install <package>
docker compose exec vite npm run build
```

Sans Docker, lancez Laravel depuis `apps/backend` et Vite depuis `apps/frontend`.