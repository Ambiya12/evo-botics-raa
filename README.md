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

## Reception demo

The maintained one-command reception demo is:

```bash
./scripts/robot.sh demo
```

The shared default is the School deployment. The current robot's ignored
`scripts/robot/config.local.sh` selects Home, so the same command currently
starts the Home demo. An explicit selection is also available:

```bash
./scripts/robot.sh demo home
./scripts/robot.sh demo school
```

The command cleanly stops stale services, starts real camera/person detection,
real WebRTC microphone/STT, Piper TTS, real QR decoding, real Laravel
validation, dialogue, the kiosk, and navigation. On the accepted controlled-site
Home configuration it starts `/root/maps/home.yaml`, AMCL, Nav2, and the
hardware-authorized reception orchestrator. Valid room IDs physically guide to
Mante Inc Room or Bayer Inc Room. Automatic physical return remains gated off
for B4 and can be enabled for B5 after B4 acceptance. Startup remains
fail-closed until the private, hardware-validated map and waypoint paths are
configured.

See [scripts/README.md](scripts/README.md) for configuration, deployment,
verification, and rollback instructions.

---

## Objectives

### Autonomous Navigation

- SLAM mapping
- Obstacle avoidance
- Optimized path planning

### Voice and Vision

- QR detection and reservation validation
- Speech pipeline (STT -> intent detection -> queued TTS)

### Web Interface

- Touchscreen visitor feedback flow
- Admin dashboard via rosbridge
- Monitoring and emergency stop

### Communication

- ROS2 DDS for robot nodes
- WebSocket bridge for UI
- Email/webhook alert pipeline

## Tech Stack

| Layer         | Technologies                      |
| ------------- | --------------------------------- |
| Robot OS      | ROS2 Humble (Nav2)                |
| Mapping       | SLAM Toolbox + LiDAR              |
| Vision        | OpenCV, YOLOv8                    |
| Voice         | Whisper, Piper                    |
| Backend       | Laravel, webhooks                 |
| Frontend      | React                             |
| Communication | DDS, rosbridge, Foxglove          |
| Hardware      | ROSMASTER M3 Pro + Jetson Orin NX |
