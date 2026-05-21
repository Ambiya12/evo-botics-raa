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
`reservationApp/resources/js/services/robotStatusService.ts`. The default
provider uses mock data; swap to a rosbridge provider when the real robot is
available via `setRobotStatusProvider()`.

## Sprint 0 Quickstart

Use the full guide in `docs/SPRINT0_FULL_GUIDE.md`.

First commands:

```bash
chmod +x scripts/sprint0_bootstrap.sh
./scripts/sprint0_bootstrap.sh
docker compose -f ops/compose/compose.simulation.yml exec -T vnc-gui bash -lc 'source /opt/ros/humble/setup.bash && cd /workspace/evo_ws && colcon build --symlink-install'
```

## RViz and Gazebo (Docker + Exposed Port)

The GUI is exposed through the web VNC desktop on port `6080`.

- Open desktop: `http://localhost:6080`
- Service port mapping is defined in `ops/compose/compose.simulation.yml` as `6080:80`.

Best-practice flow:

```bash
docker compose -f ops/compose/compose.simulation.yml up -d --build
docker compose -f ops/compose/compose.simulation.yml exec -T --user ubuntu vnc-gui bash -lc 'source /opt/ros/humble/setup.bash && cd /workspace/evo_ws && colcon build --symlink-install'
```

Launch M3 Pro in RViz (opens in `localhost:6080` desktop):

```bash
docker compose -f ops/compose/compose.simulation.yml exec -T --user ubuntu vnc-gui bash -lc 'cd /workspace && ./scripts/dev/open_m3pro_display.sh'
```

Launch Gazebo Sim (Fortress, opens in `localhost:6080` desktop):

```bash
docker compose -f ops/compose/compose.simulation.yml exec -T --user ubuntu vnc-gui bash -lc 'cd /workspace && ./scripts/dev/open_gazebo_fortress.sh'
```

Notes:

- RViz/Gazebo are desktop apps, so they do not expose their own HTTP ports here.
- You interact with both applications through the VNC web desktop on `localhost:6080`.
