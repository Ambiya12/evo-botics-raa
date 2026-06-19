# Evo-Botics Robot Launch Guide

Normal workflow for the Jetson robot, driven from the Mac with the helper scripts in
`scripts/robot/`. Each ROS service runs in a **detached tmux session on the Jetson**, so
it survives closing your Mac terminals — no more keeping 3 terminals open.

> The ROS workspace `evo_ws` is **gitignored**: the real code lives in the Jetson Docker
> container, and your local copy may be stale. The robot is the source of truth — see
> `setup` / `pull` below.

## Quick Start

```bash
# 1. One-time per session: set the Jetson IP if it changed (DHCP). Container is auto-detected.
./scripts/robot/robot.sh config ip 10.10.220.251
./scripts/robot/robot.sh config show          # check effective config

# 2. Sync evo_ws FROM the robot (source of truth) and rebuild in Docker.
./scripts/robot/robot.sh setup
./scripts/robot/robot.sh pull                 # pull only, no rebuild
./scripts/robot/robot.sh setup --push         # push your LOCAL evo_ws to the robot (asks confirmation)

# 3. Start a stack (profile)
./scripts/robot/robot.sh start base           # bringup + camera + vision + web
./scripts/robot/robot.sh start map            # bringup + camera + slam + web   (build a map)
./scripts/robot/robot.sh start navigate       # bringup + camera + nav  + web   (saved map)
./scripts/robot/robot.sh start web            # a single service also works

# 4. Inspect / operate
./scripts/robot/robot.sh status               # tmux sessions + ROS topics + MCU + ports
./scripts/robot/robot.sh mcu                   # wake the base board if its micro-ROS feed is frozen
./scripts/robot/robot.sh health               # Jetson specs + CPU/RAM load (read-only)
./scripts/robot/robot.sh logs slam            # attach a service (Ctrl-b d to detach)
./scripts/robot/robot.sh restart              # killed after ~6h ? relaunch the last profile
./scripts/robot/robot.sh stop all
```

The dashboard (Laravel) stays separate: run `composer dev` in `reservationApp/`, then open
<http://127.0.0.1:8000/admin/robot>. Set Robot IP to the Jetson IP, ROS Port `9090`,
Camera Port `8080`, Camera Path `/camera/stream`.

## After a Jetson reboot

A reboot **recreates the Docker containers from scratch**: `/root/evo_ws` is lost (it is not
a volume) and the base board's micro-ROS session goes silent (no `/odom_raw`, `/cmd_vel` has
no consumer → the robot won't move). One command puts everything back:

```bash
./scripts/robot/robot.sh config ip <new-ip>   # DHCP: the IP almost always changed
./scripts/robot/robot.sh recover map           # evo_ws + stack + wake MCU + status
```

`recover [profile]` chains the full recovery (profile defaults to the last one used, else `map`):

1. **evo_ws** — if the container lost it, re-seed from the Jetson host copy
   (`/home/jetson/evo_ws`, persistent across reboots) and `colcon build` (skipped when
   already built). `setup` now applies the same host fallback.
2. **stack** — `start <profile>`. Use `map` or `navigate`: only those carry the
   `cmd_vel_safety_gate` that relays `/cmd_vel_teleop` → `/cmd_vel` for browser teleop —
   `base` alone never drives from the dashboard.
3. **MCU** — `mcu` restarts the micro-ROS agent if the board's feed is frozen, then waits
   for `/odom_raw` to resume. If it still reports the board silent, press the physical reset
   button on the expansion board.

Everything must stay on `ROS_DOMAIN_ID=30` — the scripts force it; the micro-ROS agent
ships on 30 too.

## Reference values

```text
Jetson user      : jetson         (SSH key installed, no password)
Jetson IP        : DHCP — changes often. Set with `robot.sh config ip <ip>`
Docker container : auto-detected (name changes on each relaunch — never hardcode it)
Docker workspace : /root/evo_ws
ROS_DOMAIN_ID    : 30
rosbridge        : ws://<jetson-ip>:9090
Camera stream    : http://<jetson-ip>:8080/camera/stream
```

The camera stream is throttled for the Jetson Nano (defaults `CAMERA_MAX_FPS=8.0`,
`CAMERA_MAX_WIDTH=640`, `CAMERA_JPEG_QUALITY=60`). Override via env or `config.local.sh`;
native-resolution MJPEG is far heavier on the Nano.

## Saving a map (not automated)

`start map` runs SLAM and lets you drive from the dashboard, but **saving** the map is a
manual step. Once the map looks good, save it inside the container:

```bash
C=$(ssh jetson@<jetson-ip> 'docker ps --format "{{.Names}}" | head -n1')
ssh jetson@<jetson-ip> "docker exec $C bash -lc '
  source /opt/ros/humble/setup.bash && source /root/evo_ws/install/setup.bash
  mkdir -p /root/maps
  ros2 run nav2_map_server map_saver_cli -f /root/maps/admin_map
'"
# -> /root/maps/admin_map.yaml + admin_map.pgm  (used by `start navigate`)
```

To reuse a map kept on the Jetson host (`~/maps_backup`):

```bash
ssh jetson@<jetson-ip>
C=$(docker ps --format '{{.Names}}' | head -n1)
docker exec "$C" mkdir -p /root/maps
docker cp ~/maps_backup/admin_map.yaml "$C":/root/maps/admin_map.yaml
docker cp ~/maps_backup/admin_map.pgm  "$C":/root/maps/admin_map.pgm
docker exec "$C" sh -lc "cd /root/maps && sed -i 's#^image:.*#image: admin_map.pgm#' admin_map.yaml"
```

## Manual ROS shell (debugging)

When you need to poke around by hand instead of using the scripts:

```bash
ssh jetson@<jetson-ip>
C=$(docker ps --format '{{.Names}}' | head -n1)
docker exec -it -e ROS_DOMAIN_ID=30 -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 -e DISPLAY=:0 "$C" bash
# inside the container:
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/evo_ws/install/setup.bash
export ROS_DOMAIN_ID=30 FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

Quick health checks (run inside that shell):

```bash
ros2 topic list -t | grep -E '/scan|/odom|/cmd_vel'        # robot base alive ?
ros2 topic hz /scan0                                        # lidar publishing ?
ros2 topic list -t | grep -E '/camera/(color|depth)'       # camera alive ?
ros2 node list | grep slam                                 # SLAM running ?
ros2 topic echo /map --once                                # map being built ?
ros2 topic echo /vision/qr/detections                      # QR scanner output
curl -I http://127.0.0.1:8080/camera/stream                # web bridge serving frames ?
```

## Troubleshooting

- **No `/scan` or `/odom`** → the base MCU isn't reachable. Bringup can't feed SLAM/Nav.
  Check the container was started with the serial device passthrough.
- **Robot won't move / no `/odom_raw` feed** (the board's micro-ROS session is frozen, often
  after a reboot) → `./scripts/robot/robot.sh mcu` restarts the agent and waits for the feed.
  `robot.sh status` flags this as `MCU … MUET`. Still silent after a restart → physical reset
  of the expansion board.
- **`setup` fails / `evo_ws` missing after a reboot** → the recreated container lost
  `/root/evo_ws`. `recover` (and `setup`) now re-seed it from the host `/home/jetson/evo_ws`;
  if the host has no copy either, push your local with `setup --push`.
- **`Camera stream unavailable`** → the web server is up but no camera driver is publishing.
  Make sure the `camera` service is running and the container can see the camera device
  (`ls -la /dev/video* /dev/bus/usb`). If the host sees `/dev/video*` but Docker doesn't,
  the container was started without camera device access.
- **QR scanner: `selected_backend: null` / `Library QUIRC is not linked`** → install the
  decoder once in the container, then rebuild/source `evo_ws`:
  ```bash
  docker exec -it "$C" bash -lc 'apt-get update && apt-get install -y libzbar0 python3-pyzbar'
  ```
- **rosbridge already on `9090`** → start the web service with `ROSBRIDGE=false`
  (`ROSBRIDGE=false ./scripts/robot/robot.sh start web`).
- **Jetson Nano saturated** (services dying after a while) → check `robot.sh health`; the
  Nano (4 GB) runs near its limit. `robot.sh restart` relaunches the last profile.

## Evo package roadmap

Owned packages:

- `evo_navigation` — SLAM, Nav2, exploration, RViz config, command safety gate.
- `evo_web` — rosbridge launch + camera HTTP bridge (`/camera/stream`, `/camera/snapshot`).
- `evo_vision` — QR scanning, depth obstacle scan, object-detection scaffold.

Likely future: `evo_interfaces`, `evo_reception`, `evo_voice`, `evo_bringup`,
`evo_description`.

Reference only: `docs/m3pro_teacher_ws` (teacher workspace) — do not launch its packages.

## 4. Start Robot Bringup

Terminal 1, inside Docker:

```bash
ros2 launch slam_mapping bringup.launch.py
```

Leave it running. This should provide the base robot, lidar, odometry, TF, arm topics, and `/cmd_vel`.

Check in another ROS shell:

```bash
ros2 topic list -t | grep -E '/scan0|/scan1|/odom|/cmd_vel'
```

## 5. Start The Camera Correctly

The dashboard camera stream depends on a real ROS image topic. If the dashboard says `Camera stream unavailable` and the sensor status shows `RGB camera` or `Depth camera` as waiting, the web server is running but the camera driver is not publishing.

First check that Docker can see the camera device:

```bash
ls -la /dev/video* /dev/bus/usb 2>/dev/null || true
```

Then check that the Yahboom camera launch file exists:

```bash
ros2 launch slam_mapping app_camera.launch.py --show-args
```

If that command prints launch arguments, start the camera in its own Docker terminal:

```bash
ros2 launch slam_mapping app_camera.launch.py
```

Leave it running.

Expected camera topics:

```bash
ros2 topic list -t | grep -E '/camera/(color|depth)'
ros2 topic hz /camera/color/image_raw
```

Expected result:

```text
/camera/color/image_raw [sensor_msgs/msg/Image]
/camera/depth/image_raw [sensor_msgs/msg/Image]
```

If `app_camera.launch.py` does not exist, find the actual camera launch installed in the Yahboom workspaces:

```bash
find /root/yahboomcar_ws /root/M3Pro_ws -path '*launch*' -iname '*camera*.launch.py' 2>/dev/null
```

Launch the camera file found there, then re-check `/camera/color/image_raw`. Do not change the dashboard camera URL; the dashboard must stay on:

```text
Camera Port: 8080
Camera Path: /camera/stream
```

## 6. Start Rosbridge And The Camera Web Server

Terminal 3, inside Docker:

```bash
ros2 launch evo_web web_dashboard.launch.py \
  port:=8080 \
  camera_topic:=/camera/color/image_raw
```

If port `9090` is already used, keep the existing rosbridge and start only the web server:

```bash
ros2 launch evo_web web_dashboard.launch.py \
  rosbridge:=false \
  port:=8080 \
  camera_topic:=/camera/color/image_raw
```

Check:

```bash
ss -ltnp | grep -E ':8080|:9090'
curl -I http://127.0.0.1:8080/camera/stream
```

## 7. Start The Admin Dashboard

On the Mac:

```bash
cd "/Users/galystan/Documents/HETIC - WEB 3/RAA/evo-botics-raa/reservationApp"
php artisan serve --host=127.0.0.1 --port=8000
```

In another Mac terminal:

```bash
cd "/Users/galystan/Documents/HETIC - WEB 3/RAA/evo-botics-raa/reservationApp"
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:8000/admin/robot
```

Dashboard values:

```text
Robot IP: 10.10.221.115
ROS Port: 9090
Camera Port: 8080
Camera Path: /camera/stream
Save Map Path: /root/maps/admin_map
```

## 8. Create A New Map

Use this when you want to drive the robot and build a map.

Terminal 1:

```bash
ros2 launch slam_mapping bringup.launch.py
```

Terminal 2:

```bash
ros2 launch evo_navigation slam_online.launch.py rviz:=false
```

Terminal 3:

```bash
ros2 launch evo_web web_dashboard.launch.py \
  port:=8080 \
  camera_topic:=/camera/color/image_raw
```

Drive slowly from the dashboard. Watch the map panel while driving.

When the map looks correct, save it inside Docker:

```bash
mkdir -p /root/maps
ros2 run nav2_map_server map_saver_cli -f /root/maps/admin_map
ls -la /root/maps/admin_map.*
```

Expected files:

```text
/root/maps/admin_map.yaml
/root/maps/admin_map.pgm
```

## 9. Navigate With A Saved Map

Use this when `/root/maps/admin_map.yaml` already exists in Docker.

Terminal 1:

```bash
ros2 launch slam_mapping bringup.launch.py
```

Terminal 2:

```bash
ros2 launch evo_navigation navigation.launch.py \
  map:=/root/maps/admin_map.yaml \
  rviz:=false
```

Terminal 3:

```bash
ros2 launch evo_web web_dashboard.launch.py \
  port:=8080 \
  camera_topic:=/camera/color/image_raw
```

Before sending Nav2 goals, set the initial pose in the dashboard so the robot marker matches the real robot.

## 10. Copy An Existing Map Into Docker

If the map is on the Jetson host in `~/maps_backup`, copy it into Docker:

```bash
ssh jetson@10.10.221.115
CONTAINER=m3pro
docker exec "$CONTAINER" mkdir -p /root/maps
docker cp ~/maps_backup/demo_map.yaml "$CONTAINER":/root/maps/demo_map.yaml
docker cp ~/maps_backup/demo_map.pgm "$CONTAINER":/root/maps/demo_map.pgm
docker exec "$CONTAINER" sh -lc "cd /root/maps && sed -i 's#^image:.*#image: demo_map.pgm#' demo_map.yaml"
docker exec "$CONTAINER" ls -la /root/maps/demo_map.*
```

Then launch navigation with:

```bash
ros2 launch evo_navigation navigation.launch.py \
  map:=/root/maps/demo_map.yaml \
  rviz:=false
```

## 11. Minimal Debug Checklist

Run these inside Docker after sourcing the ROS setup.

Robot base:

```bash
ros2 topic list -t | grep -E '/scan0|/scan1|/scan_multi|/odom|/cmd_vel'
ros2 topic hz /scan0
ros2 topic hz /scan1
```

Map:

```bash
ros2 node list | grep slam
ros2 topic echo /map --once
```

Navigation:

```bash
ros2 topic echo /amcl_pose --once
ros2 run tf2_ros tf2_echo map base_footprint
```

Camera:

```bash
ros2 topic list -t | grep -E '/camera/(color|depth)'
ros2 topic hz /camera/color/image_raw
curl -I http://127.0.0.1:8080/camera/stream
```

Ports:

```bash
ss -ltnp | grep -E ':8080|:9090'
```

## 12. Display The Kiosk Screen On The Robot

Show the Laravel `/kiosk` page fullscreen on the robot's HDMI screen. No ROS, no Docker:
Chromium runs directly on the Jetson host and loads the page from the laptop serving the app.

Prerequisites on the laptop:

- Sail is up (`./vendor/bin/sail up -d`) — the app is served on **port 80**.
- Assets are reachable from the robot: either `npm run build`, or set `VITE_HMR_HOST` to the
  laptop IP in `reservationApp/.env` and run `sail npm run dev`.
- Laptop and robot on the **same network**.

`IP_ROBOT` is the Jetson IP (it can change — never hardcode it). `LAPTOP_IP` is the laptop IP.

1. Get the laptop IP on the LAN (this is `LAPTOP_IP`; try `en1` if `en0` is empty):

```bash
ipconfig getifaddr en0
```

2. Open the kiosk fullscreen on the robot screen over SSH:

```bash
ssh jetson@IP_ROBOT "DISPLAY=:0 chromium-browser --kiosk --noerrdialogs --disable-infobars --incognito --disable-gpu --use-gl=swiftshader http://LAPTOP_IP/kiosk"
```

Stop the kiosk:

```bash
ssh jetson@IP_ROBOT 'pkill -f chromium'
```

## Important Notes

- Keep each ROS launch running in its own terminal.
- Treat `docs/m3pro_teacher_ws ` as reference material only. Do not launch `m3pro_teacher_*` packages for the Evo-Botics workflow.
- If you stop the camera launch, `/camera/color/image_raw` disappears and `/camera/stream` has no frames.
- If the Jetson host sees `/dev/video*` but Docker does not, the container was started without access to the camera device. Restart the robot Docker stack with USB/video device access, then launch the camera again.
- If rosbridge is already running on `9090`, use `rosbridge:=false` for `web_dashboard.launch.py`.
- The deploy script syncs `evo_ws/src` from this repository to the Jetson host workspace.
