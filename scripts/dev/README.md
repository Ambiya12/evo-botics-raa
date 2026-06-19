# Evo-Botics Robot Launch Guide

## Foxglove map creation

For the easiest supported workflow to create, visualize, drive, and save a new map with
Foxglove:

```bash
./scripts/dev/foxglove_map.sh start
./scripts/dev/foxglove_map.sh save ground_floor
./scripts/dev/foxglove_map.sh stop
```

This starts both WebSocket connections:

- Foxglove native bridge: `ws://<jetson-ip>:8765`
- Admin dashboard rosbridge: `ws://<jetson-ip>:9090`

See the full step-by-step guide in
[`FOXGLOVE_MAP_TUTORIAL.md`](./FOXGLOVE_MAP_TUTORIAL.md).

This is the normal workflow for the Jetson robot.

The Evo-Botics ROS workspace is now `evo_ws`. It is our first-party workspace and should be deployed from this repository. The teacher workspace under `docs/m3pro_teacher_ws ` is kept only as reference material.

## Quick Start (recommended)

The scripts in `scripts/robot/` wrap the whole procedure below. Each ROS service runs
in a **detached tmux session on the Jetson**, so it survives closing your Mac terminals
(no more keeping 3 terminals open). All commands run from the repo on the Mac.

```bash
# 1. One-time : set your Jetson IP if it changed (DHCP). Container name is auto-detected.
./scripts/robot/config.sh        # (sourced by robot.sh ; nothing to run directly)
./scripts/robot/robot.sh config ip 10.10.221.115

# 2. Deploy + build into Docker (steps 1-2 below)
./scripts/robot/robot.sh setup

# 3. Start a full stack (choose a profile)
./scripts/robot/robot.sh start map        # bringup + camera + slam + web  (create a map, §8)
./scripts/robot/robot.sh start navigate   # bringup + camera + nav  + web  (saved map, §9)
./scripts/robot/robot.sh start base       # bringup + camera + web

# 4. Inspect / operate
./scripts/robot/robot.sh status           # tmux sessions + ROS topics + ports
./scripts/robot/robot.sh logs slam        # attach a service (Ctrl-b d to detach)
./scripts/robot/robot.sh restart          # services killed after ~6h ? relaunch the last profile
./scripts/robot/robot.sh stop all
```

The dashboard side (Laravel) stays as-is: run `composer dev` in `reservationApp/`.

The sections below document the **manual** procedure each script automates — keep them as
reference for debugging.

## Robot Values

```text
Jetson IP: 10.10.221.115
Jetson user: jetson
Docker container: m3pro
Host workspace: /home/jetson/evo_ws
Docker workspace: /root/evo_ws
ROS_DOMAIN_ID: 30
ROS bridge: ws://10.10.221.115:9090
Camera stream: http://10.10.221.115:8080/camera/stream
Dashboard: http://127.0.0.1:8000/admin/robot
```

If the container name is not `m3pro`, check it on the Jetson:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

## Evo Package Roadmap

Current owned packages:

- `evo_navigation`: SLAM, Nav2, exploration, RViz config, and command safety gate.
- `evo_web`: rosbridge launch and camera HTTP bridge for `/camera/stream` and `/camera/snapshot`.
- `evo_vision`: robot-camera QR scanning, depth obstacle scan publishing, and object detection scaffold.

Likely future packages:

- `evo_interfaces`: custom messages/actions/services for reservations, guide state, and safety status.
- `evo_reception`: visitor flow, reservation validation bridge, and waypoint orchestration.
- `evo_voice`: STT/TTS/translation pipeline.
- `evo_bringup`: one-command launch composition once nav, web, vision, and reception are stable.
- `evo_description`: robot URDF/RViz assets only if we need to own the model instead of relying on Yahboom bringup.

## 1. Deploy The Evo Workspace To The Jetson

Run this from the repository on the Mac:

```bash
JETSON_IP=10.10.221.115 JETSON_USER=jetson JETSON_WS=/home/jetson/evo_ws ./scripts/deploy.sh
```

This syncs `evo_ws/src` to the Jetson host and builds the host workspace.

## 2. Copy The Jetson Workspace Into Docker

Run this on the Jetson, not on the Mac:

```bash
ssh jetson@10.10.221.115
```

```bash
CONTAINER=blissful_ellis
HOST_WS=/home/jetson/evo_ws
DOCKER_WS=/root/evo_ws

test -d "$HOST_WS"
docker exec "$CONTAINER" rm -rf "$DOCKER_WS"
docker cp "$HOST_WS" "$CONTAINER:$DOCKER_WS"
docker exec -it \
  -e ROS_DOMAIN_ID=30 \
  -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 \
  "$CONTAINER" \
  bash -lc '
    source /opt/ros/humble/setup.bash
    source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
    source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
    cd /root/evo_ws
    colcon build --symlink-install
  '
```

Use this again whenever `evo_ws/src` changes.

If QR scanning reports that OpenCV was built without QUIRC, install the zbar decoder dependency inside Docker once:

```bash
docker exec -it m3pro bash -lc '
  apt-get update
  apt-get install -y libzbar0 python3-pyzbar
'
```

## Optional: Start The Repeated Terminals With Tmux

For normal development and demos, use tmux so you do not have to open every terminal manually.
Each long-running process still gets its own tmux window, so logs stay readable.

Install tmux once if needed:

```bash
# Mac
brew install tmux

# Jetson
sudo apt-get install -y tmux
```

Start the robot-side ROS processes from the Mac:

```bash
./scripts/dev/start_robot_tmux.sh
```

This creates a remote Jetson tmux session named `evo-robot` with windows for:

- `bringup`
- `camera`
- `vision`
- `web`

For mapping mode:

```bash
./scripts/dev/start_create_map_tmux.sh
```

This creates a remote Jetson tmux session named `evo-create-map` with windows for:

- `bringup`
- `camera`
- `slam`
- `web`

For saved-map navigation:

```bash
./scripts/dev/start_saved_map_tmux.sh
```

This creates a remote Jetson tmux session named `evo-saved-map` with windows for:

- `bringup`
- `camera`
- `nav`
- `web`

The saved-map script uses `/root/maps/admin_map.yaml` by default. To use another map:

```bash
MAP_PATH=/root/maps/demo_map.yaml ./scripts/dev/start_saved_map_tmux.sh
```

Every Docker tmux window sources the ROS setup first:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/evo_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

Start the admin dashboard processes on the Mac:

```bash
./scripts/dev/start_dashboard_tmux.sh
```

This creates a local tmux session named `evo-dashboard` with windows for:

- `laravel`
- `vite`

Useful tmux keys:

```text
Ctrl-b then n  next window
Ctrl-b then p  previous window
Ctrl-b then d  detach without stopping processes
```

Reattach later:

```bash
ssh jetson@10.10.221.115 -t tmux attach-session -t evo-robot
tmux attach-session -t evo-dashboard
```

## 3. Open A ROS Shell

Open a new terminal whenever you need to launch a ROS process:

```bash
ssh jetson@10.10.221.115
docker exec -it \
  -e ROS_DOMAIN_ID=30 \
  -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 \
  -e DISPLAY=:0 \
  m3pro \
  bash
```

Inside Docker, run:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/evo_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

Quick check:

```bash
ros2 pkg list | grep -E 'evo_|explore_lite'
```

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

## 6. Start Vision Perception

Terminal 3, inside Docker:

```bash
ros2 launch evo_vision vision.launch.py \
  camera_topic:=/camera/color/image_raw \
  depth_topic:=/camera/depth/image_raw \
  qr_decoder_backend:=auto
```

This starts QR scanning and publishes a conservative depth-camera scan. It does not change Nav2 behavior by default.

If `/vision/qr/status` shows `"selected_backend": null`, the robot container is missing a QR decoder. Install `libzbar0 python3-pyzbar` in Docker, rebuild/source `evo_ws`, then launch vision again.

QR smoke test:

```bash
ros2 topic echo /vision/qr/detections
```

Show a reservation QR code to the robot camera. The topic should publish decoded JSON. `reservationApp` owns QR generation and validation; `evo_vision` only scans and publishes what it sees.

Depth smoke test:

```bash
ros2 topic echo /vision/obstacles/scan --once
```

Move an object in front of the depth camera and re-run the command. Some ranges should become shorter.

Object detection is scaffolded but disabled until a model is selected:

```bash
ros2 launch evo_vision vision.launch.py enable_object_detection:=true
```

## 7. Start Rosbridge And The Camera Web Server

Terminal 4, inside Docker:

```bash
ros2 launch evo_web web_dashboard.launch.py \
  port:=8080 \
  camera_topic:=/camera/color/image_raw \
  camera_max_fps:=8.0 \
  camera_max_width:=640 \
  camera_jpeg_quality:=60
```

If port `9090` is already used, keep the existing rosbridge and start only the web server:

```bash
ros2 launch evo_web web_dashboard.launch.py \
  rosbridge:=false \
  port:=8080 \
  camera_topic:=/camera/color/image_raw \
  camera_max_fps:=8.0 \
  camera_max_width:=640 \
  camera_jpeg_quality:=60
```

Check:

```bash
ss -ltnp | grep -E ':8080|:9090'
curl -I http://127.0.0.1:8080/camera/stream
```

## 8. Start The Admin Dashboard

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

## 9. Create A New Map

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

## 10. Navigate With A Saved Map

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

## 11. Copy An Existing Map Into Docker

If the map is on the Jetson host in `~/maps_backup`, copy it into Docker:

```bash
ssh jetson@10.10.220.225
CONTAINER=blissful_goldstine
docker exec "$CONTAINER" mkdir -p /root/maps
docker cp ~/maps_backup/admin_map.yaml "$CONTAINER":/root/maps/admin_map.yaml
docker cp ~/maps_backup/admin_map.pgm "$CONTAINER":/root/maps/admin_map.pgm
docker exec "$CONTAINER" sh -lc "cd /root/maps && sed -i 's#^image:.*#image: admin_map.pgm#' admin_map.yaml"
docker exec "$CONTAINER" ls -la /root/maps/admin_map.*
```

Then launch navigation with:

```bash
ros2 launch evo_navigation navigation.launch.py \
  map:=/root/maps/demo_map.yaml \
  rviz:=false
```

## 12. Minimal Debug Checklist

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

Camera and vision:

```bash
ros2 topic list -t | grep -E '/camera/(color|depth)'
ros2 topic hz /camera/color/image_raw
ros2 topic echo /vision/qr/status --once
ros2 topic echo /vision/obstacles/scan --once
curl -I http://127.0.0.1:8080/camera/stream
```

Ports:

```bash
ss -ltnp | grep -E ':8080|:9090'
```

## Important Notes

- Keep each ROS launch running in its own terminal or tmux window.
- Treat `docs/m3pro_teacher_ws ` as reference material only. Do not launch `m3pro_teacher_*` packages for the Evo-Botics workflow.
- If you stop the camera launch, `/camera/color/image_raw` disappears and `/camera/stream` has no frames.
- If the Jetson host sees `/dev/video*` but Docker does not, the container was started without access to the camera device. Restart the robot Docker stack with USB/video device access, then launch the camera again.
- If the camera stream is delayed, keep the HTTP bridge at `camera_max_width:=640`, `camera_max_fps:=8.0`, and `camera_jpeg_quality:=60`; native-resolution MJPEG is much heavier on the Jetson.
- If `evo_vision` logs `Library QUIRC is not linked`, install `libzbar0 python3-pyzbar` in Docker and use the default `qr_decoder_backend:=auto`.
- If rosbridge is already running on `9090`, use `rosbridge:=false` for `web_dashboard.launch.py`.
- The deploy script syncs `evo_ws/src` from this repository to the Jetson host workspace.
