# Robot scripts

Run every command from the repository root on the Mac:

```bash
./scripts/robot.sh <command>
```

`scripts/robot.sh` is the public entry point. The files under `scripts/robot/`
are its implementation and configuration; do not run them directly.

## What the script supports

The script has five separate workflows:

1. Run the one-command real-data reception demo and kiosk.
2. Launch the robot with an existing saved map.
3. Create and save a new map with SLAM and RViz (or Foxglove).
4. Launch `evo_voice` by itself for voice development.
5. Launch reception components separately for diagnosis.

## One-time configuration

Configure the Jetson address:

```bash
./scripts/robot.sh config ip <jetson-ip>
./scripts/robot.sh config show
```

If the kiosk or reservation backend cannot automatically find the Mac, set the
Mac address reachable from the Jetson:

```bash
ipconfig getifaddr en0
./scripts/robot.sh config app-host <mac-ip>
```

Values are stored in the ignored `scripts/robot/config.local.sh`.

Keep the E-stop reachable whenever bringup, mapping, or Nav2 is running.

## One-command reception demo

For the current Home deployment:

```bash
./scripts/robot.sh demo
```

The ignored robot configuration sets:

```bash
DEFAULT_DEMO_MAP=home
DEMO_START_LARAVEL=true
HOME_MAP_PATH=/root/maps/home.yaml
HOME_RECEPTION_WAYPOINT_CONFIG_PATH=/root/evo_ws/install/evo_navigation/share/evo_navigation/config/home_reception_waypoints.yaml
```

The explicit equivalent is:

```bash
./scripts/robot.sh demo home
```

The shared repository default remains `school`. School startup is deliberately
blocked until its measured waypoint registry is configured:

```bash
SCHOOL_RECEPTION_WAYPOINT_CONFIG_PATH=/absolute/path/to/school_reception_waypoints.yaml
```

The demo command performs a clean stop and then starts:

```text
camera
robot bringup, Home map, AMCL, and Nav2
vision/person detection
real Laravel reservation bridge
WebRTC microphone, STT, and Piper TTS
dialogue manager
human approach detection
hardware-authorized reception navigation orchestrator
web dashboard/rosbridge
kiosk browser
```

When `DEMO_START_LARAVEL=true`, it first runs the idempotent
`reservationApp/vendor/bin/sail up -d` command and waits for the configured
application URL. It never runs migrations or seeders. `stop demo` stops the
robot/kiosk stack but deliberately leaves Laravel running so it cannot
interrupt another browser or administrator session.

The expected workflow is:

```text
Human detected
→ automatic greeting and reservation question
→ affirmative answer (or reservation/booking fallback)
→ QR request
→ 20-second QR window
→ real Laravel validation
→ room ID 1 (Mante Inc Room) or 2 (Bayer Inc Room)
→ physical Nav2 guidance and arrival
→ “Have a nice day”
→ remain stopped at the destination for B4 acceptance
```

Required configuration includes:

```bash
RECEPTION_VALIDATION_URL=http://<mac-ip>:8000/api/reservations/validate
RECEPTION_ALLOWED_DESTINATION_IDS=1,2
KIOSK_URL=http://<mac-ip>:8000/kiosk?scan=robot
```

Laravel must use:

```dotenv
EVO_NAVIGABLE_ROOM_IDS=1,2
```

Stop the complete demo and kiosk with:

```bash
./scripts/robot.sh stop demo
```

Startup refuses to continue until the reviewed map, AMCL pose, inactive
E-stop, Nav2, and real reception action are available. The orchestrator
requires `allow_real_navigation=true`, a `map`-frame localization with bounded
covariance, and a registry marked `hardware_validated: true`.

For the first B4 run, keep:

```bash
REAL_AUTOMATIC_RETURN_ENABLED=false
```

After B4 is recorded as passed, begin B5 by changing only that value to
`true`. The existing dialogue sequence will then request the reviewed
Reception waypoint after “Have a nice day” and return to `IDLE` only after
Nav2 reports arrival.

There is no simulated reception-navigation profile. A fresh deployment remains
fail-closed until its private controlled-site map and waypoint paths are
configured.

## Deploy ROS changes

After changing files under `evo_ws/src/`, deploy and build them on the robot:

```bash
./scripts/robot.sh stop all
./scripts/robot.sh setup
```

`setup` copies `evo_ws/src` from the Mac to the Jetson, copies it into the
`evo-ros` container, removes the previous `build`, `install`, and `log`
directories, and performs a clean workspace build there. Run `stop all` first;
if the clean build fails, the previous install is intentionally unavailable.

## Workflow 1: launch with a saved map

The default map is `school_v1`:

```text
/root/evo_ws/src/evo_navigation/maps/school_v1.yaml
```

Start the complete saved-map robot workflow:

```bash
./scripts/robot.sh launch
```

This starts robot bringup, the camera, Nav2 with `school_v1`, vision, the real
reservation-validation bridge, the web bridge, and the kiosk. It also checks
the MCU and waits for Nav2 lifecycle nodes and velocity routing to become
ready.

To use another map already saved on the Jetson:

```bash
./scripts/robot.sh sync-maps my_map
./scripts/robot.sh launch my_map
```

To start only bringup, camera, saved-map navigation, and the web bridge:

```bash
./scripts/robot.sh start navigate
```

Nav2 costmaps and controller collision checking remain enabled. The additional
collision-monitor stop polygon is disabled by default because it blocks all
manual Twist directions, including reverse recovery. Enable it only after its
scan geometry and recovery behavior pass the controlled-site review:

```bash
NAV_USE_COLLISION_MONITOR=true ./scripts/robot.sh start navigate
```

You can select a map name or an absolute YAML path:

```bash
./scripts/robot.sh start navigate my_map
./scripts/robot.sh nav my_map
./scripts/robot.sh nav /root/maps/my_map.yaml
```

Stop the robot workflow:

```bash
./scripts/robot.sh stop launch
```

Use `./scripts/robot.sh stop all` if you want to stop every service managed by
the script.

### Dashboard readiness failure with ports already listening

If a failure report shows both `0.0.0.0:8080` and `0.0.0.0:9090` in `LISTEN`,
the dashboard itself started successfully. Older launcher versions used
`urllib` for the loopback HTTP probe; proxy settings inherited by the container
could make that probe fail even while the local server was healthy. The
launcher now uses a direct TCP/HTTP probe and reports the exact failing check.

Recover from a partial attempt with:

```bash
./scripts/robot.sh stop all
./scripts/robot.sh nav home
```

If the failure instead shows live dashboard processes but
`ConnectionRefusedError` and no listeners, the Jetson was still cold-starting
the Python processes while Nav2 and local ML models consumed startup resources.
The real demo profile now starts and validates the web bridge immediately after
the camera, before starting Nav2, YOLO, and Whisper. A failed demo startup also
stops the partial profile instead of leaving competing services alive.

During Nav2 startup, the command prints the pending lifecycle, map, costmap,
goal-validator, and velocity-routing gates every ten seconds. The readiness
window is a real 120-second wall-clock deadline. The costmap probe reads only
its transient-local header instead of repeatedly printing the complete
occupancy grid; this prevents a valid initial pose from appearing to hang the
launcher for several minutes.

Every ROS graph probe also has its own short timeout, so a stalled ROS CLI or
DDS discovery request cannot freeze the outer deadline before diagnostics are
printed. The kiosk opens before Nav2 initialization and may briefly show a
connecting state; QR input and navigation remain ignored until the reception
state machine reaches their explicitly allowed states.

The launcher establishes one multiplexed SSH control connection before
starting the demo and reuses it for service probes, tmux launches, and
readiness checks. This avoids dozens of simultaneous SSH handshakes while the
Jetson is loading Nav2 and local vision models. The default keepalive tolerates
up to roughly 60 seconds of temporary Jetson load before treating the
connection as lost.

## Workflow 2: create and save a map

Mapping moves the real robot. Use it only in the reviewed mapping area with the
E-stop reachable and an operator beside the robot.

Start robot bringup, camera, online SLAM, the web bridge, and RViz on the robot
display:

```bash
./scripts/robot.sh map rviz
```

The command now verifies the Jetson X11 display, the container X11 socket
mount, X authorization, the `rviz2` executable, and the running RViz process
before reporting success. The default display is `:0`. If the Jetson desktop
uses another display, configure it first:

```bash
: "${KIOSK_DISPLAY:=:1}"
```

RViz is an image-level dependency. The maintained
`scripts/robot/image/Dockerfile` installs `ros-humble-rviz2`. If the command
reports that `rviz2` is missing, build and provision a new `evo-ros` image from
that Dockerfile using the robot image deployment procedure. Running
`./scripts/robot.sh setup` only deploys and builds the ROS workspace; it does
not add Ubuntu or ROS binary packages to an existing container.

The image explicitly installs the workspace runtime dependencies: Nav2
bringup, SLAM Toolbox, rosbridge, OpenCV/cv_bridge, NumPy, YAML, QR decoding
with pyzbar/zbar, Foxglove, RViz, and the robot-description tools used by the
vendor bringup. Its build-time checks catch an incomplete image before it is
provisioned on the robot.

If mapping is already running, stop it before changing between RViz and
Foxglove modes:

```bash
./scripts/robot.sh map stop
```

Drive the robot through the mapping area using the approved teleoperation
method. Dashboard teleop remains behind the latched E-stop gate and the
0.5-second output watchdog. The Nav2 collision-monitor polygon is disabled for
manual mapping by default because its stop action blocks every direction,
including the reverse command needed to leave an occupied stop zone.

Enable it only after validating the polygon and merged scan on the physical
robot:

```bash
SLAM_USE_COLLISION_MONITOR=true ./scripts/robot.sh map rviz
```

If the robot display is not available, use the optional Foxglove mode:

```bash
./scripts/robot.sh map foxglove
```

That command prints the Foxglove WebSocket URL.

Check mapping sessions:

```bash
./scripts/robot.sh map status
```

Save the completed map with a unique name:

```bash
./scripts/robot.sh save-map school_v2
```

The map is saved as YAML and PGM files in both locations:

```text
evo-ros container: /root/maps/school_v2.yaml
Jetson host:       /home/jetson/maps/school_v2.yaml
```

Stop mapping:

```bash
./scripts/robot.sh map stop
```

Launch the saved map later:

```bash
./scripts/robot.sh nav school_v2
```

## Workflow 3: voice development

The maintained `evo_voice` stack separates speech-to-text, deterministic intent
detection, and queued text-to-speech. The complete reception demo starts it
automatically; this command runs the voice stack alone for development and
diagnosis.

Start only the voice stack:

```bash
./scripts/robot.sh start voice
```

TTS and STT require real local devices and models configured in the ignored
`scripts/robot/config.local.sh`:

```bash
: "${PIPER_MODEL_PATH:=/absolute/path/to/local/model.onnx}"
: "${AUDIO_OUTPUT_DEVICE:=}"

: "${STT_MODEL_PATH:=/absolute/path/to/local/whisper/model}"
: "${STT_DEVICE:=cpu}"
: "${STT_COMPUTE_TYPE:=int8}"
: "${VOICE_LANGUAGE:=en}"
: "${MICROPHONE_DEVICE:=-1}"
```

Stop voice before changing audio configuration:

```bash
./scripts/robot.sh stop voice
```

An isolated voice launch validates audio and intent processing only, not the
complete reception workflow.

## Workflow 4: reception component diagnosis

Start real camera input, QR scanning, Laravel validation, and the web bridge:

```bash
./scripts/robot.sh start camera-qr
```

This requires `RECEPTION_VALIDATION_URL` (or a resolvable app host). It does
not start voice, dialogue, Nav2, teleop, or any velocity pipeline. Stop it with:

```bash
./scripts/robot.sh stop camera-qr
```

## Operations

```bash
./scripts/robot.sh status
./scripts/robot.sh health
./scripts/robot.sh mcu
./scripts/robot.sh logs nav
./scripts/robot.sh stop <service-or-profile>
./scripts/robot.sh stop all
```

Use `Ctrl-b`, then `d`, to detach from tmux logs without stopping a service.
Service output is also retained under `/home/jetson/evo_logs` on the Jetson.
If a ROS launch exits during startup, `start` reports the captured error and
`logs <service>` shows the last output even though its tmux session is gone.

The expected runtime is:

- ROS container: `evo-ros`
- micro-ROS supervisor: `evo-micro-ros-agent.service`
- ROS domain: `30`

After every robot reboot, check the runtime before launching:

```bash
./scripts/robot.sh status
./scripts/robot.sh mcu
```

### Recover missing LiDAR and odometry topics

`/scan0`, `/scan1`, `/odom_raw`, and `/battery` come from the base MCU through
the systemd-managed `evo-micro-ros-agent` container. The robot bringup then
merges and filters the raw scans:

```text
MCU -> /scan0 + /scan1 -> /scan_multi -> /scan
```

If `/scan0` and `/scan1` disappear together with `/battery` or `/odom_raw`, do
not change Nav2 topics and do not start mapping or navigation. The likely fault
is the micro-ROS session, not the laser filter. Keep the wheels disabled and
the E-stop reachable, then run from the Mac:

```bash
./scripts/robot.sh mcu --force
./scripts/robot.sh start bringup
./scripts/robot.sh status
```

Verify real messages rather than topic names alone:

```bash
ssh jetson@<jetson-ip>
sudo systemctl is-active evo-micro-ros-agent.service
docker exec evo-ros bash -lc \
  'source /opt/ros/humble/setup.bash &&
   timeout 10s ros2 topic echo /battery --once --qos-reliability best_effort'
docker exec -it evo-ros bash
ros2 topic hz /scan0
ros2 topic hz /scan1
ros2 topic hz /scan_multi
ros2 topic hz /scan
```

Run each `hz` command long enough to print several samples, then stop it with
`Ctrl-C`. On the current M3 Pro, the scan topics are normally about 7 Hz. Topic
discovery without messages is not a successful check.

The micro-ROS service should be enabled and configured to restart:

```bash
sudo systemctl is-enabled evo-micro-ros-agent.service
sudo systemctl show evo-micro-ros-agent.service -p Restart -p RestartUSec
```

Expected values are `enabled`, `Restart=always`, and `RestartUSec=5s`. If the
installed unit is older, missing `/etc/default/evo-micro-ros-agent`, or lacks
that restart policy, provision the maintained files from
`scripts/robot/jetson/`. That installer creates a dated backup and does not
restart the service automatically:

```bash
# Mac, from the repository root
ssh jetson@<jetson-ip> 'mkdir -p /home/jetson/evo-robot-installer'
scp scripts/robot/jetson/* \
  jetson@<jetson-ip>:/home/jetson/evo-robot-installer/

# Jetson
cd /home/jetson/evo-robot-installer
bash install.sh
sudo systemctl daemon-reload
sudo systemctl enable evo-micro-ros-agent.service
sudo systemctl restart evo-micro-ros-agent.service
```

After provisioning, perform one movement-disabled reboot check. `/scan0` and
`/scan1` should return automatically with the MCU agent. `/scan_multi` and
`/scan` require robot bringup, which remains an explicit operator action:

```bash
./scripts/robot.sh start bringup
```

If recovery fails, stop there and collect:

```bash
sudo journalctl -u evo-micro-ros-agent.service -n 100 --no-pager
docker logs --tail 100 evo-micro-ros-agent
```

## Important limits

- `school_v1` is the default saved map, but its presence does not prove that
  localization, waypoint poses, clearances, or Nav2 behavior are accepted.
- Mapping and navigation require real-robot checks and an operator-controlled
  site.
- The isolated voice command does not start the rest of the reception workflow.
- Commands in this README are operational robot commands; run them manually
  only in the appropriate robot environment.
