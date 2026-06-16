# Evo-Botics Robot Launch Guide

This is the normal workflow for the Jetson robot.

The `m3pro_teacher_ws` workspace already exists on the Jetson host, so do not deploy it from the Mac every time. Copy the Jetson host workspace into the Docker container, build it there, then launch ROS from Docker.

## Robot Values

```text
Jetson IP: 10.10.221.115
Jetson user: jetson
Docker container: m3pro
Host workspace: /home/jetson/m3pro_teacher_ws
Docker workspace: /root/m3pro_teacher_ws
ROS_DOMAIN_ID: 30
ROS bridge: ws://10.10.221.115:9090
Camera stream: http://10.10.221.115:8080/camera/stream
Dashboard: http://127.0.0.1:8000/admin/robot
```

If the container name is not `m3pro`, check it on the Jetson:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

## 1. Copy The Jetson Workspace Into Docker

Run this on the Jetson, not on the Mac:

```bash
ssh jetson@10.10.221.115
```

```bash
CONTAINER=m3pro
HOST_WS=/home/jetson/m3pro_teacher_ws
DOCKER_WS=/root/m3pro_teacher_ws

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
    cd /root/m3pro_teacher_ws
    colcon build --symlink-install
  '
```

Use this again only when the Jetson host copy of `m3pro_teacher_ws` changes.

## 2. Open A ROS Shell

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
source /root/m3pro_teacher_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

Quick check:

```bash
ros2 pkg list | grep m3pro_teacher
```

## 3. Start Robot Bringup

Terminal 1, inside Docker:

```bash
ros2 launch slam_mapping bringup.launch.py
```

Leave it running. This should provide the base robot, lidar, odometry, TF, arm topics, and `/cmd_vel`.

Check in another ROS shell:

```bash
ros2 topic list -t | grep -E '/scan0|/scan1|/odom|/cmd_vel'
```

## 4. Start The Camera Correctly

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

## 5. Start Rosbridge And The Camera Web Server

Terminal 3, inside Docker:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py \
  port:=8080 \
  camera_topic:=/camera/color/image_raw
```

If port `9090` is already used, keep the existing rosbridge and start only the web server:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py \
  rosbridge:=false \
  port:=8080 \
  camera_topic:=/camera/color/image_raw
```

Check:

```bash
ss -ltnp | grep -E ':8080|:9090'
curl -I http://127.0.0.1:8080/camera/stream
```

## 6. Start The Admin Dashboard

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

## 7. Create A New Map

Use this when you want to drive the robot and build a map.

Terminal 1:

```bash
ros2 launch slam_mapping bringup.launch.py
```

Terminal 2:

```bash
ros2 launch m3pro_teacher_nav slam_online.launch.py rviz:=false
```

Terminal 3:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py \
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

## 8. Navigate With A Saved Map

Use this when `/root/maps/admin_map.yaml` already exists in Docker.

Terminal 1:

```bash
ros2 launch slam_mapping bringup.launch.py
```

Terminal 2:

```bash
ros2 launch m3pro_teacher_nav navigation.launch.py \
  map:=/root/maps/admin_map.yaml \
  rviz:=false
```

Terminal 3:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py \
  port:=8080 \
  camera_topic:=/camera/color/image_raw
```

Before sending Nav2 goals, set the initial pose in the dashboard so the robot marker matches the real robot.

## 9. Copy An Existing Map Into Docker

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
ros2 launch m3pro_teacher_nav navigation.launch.py \
  map:=/root/maps/demo_map.yaml \
  rviz:=false
```

## 10. Minimal Debug Checklist

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

## Important Notes

- Keep each ROS launch running in its own terminal.
- If you stop the camera launch, `/camera/color/image_raw` disappears and `/camera/stream` has no frames.
- If the Jetson host sees `/dev/video*` but Docker does not, the container was started without access to the camera device. Restart the robot Docker stack with USB/video device access, then launch the camera again.
- If rosbridge is already running on `9090`, use `rosbridge:=false` for `web_dashboard.launch.py`.
- The old Mac-to-Jetson deploy script is only needed when you changed the workspace on the Mac and want to send those changes to the Jetson host.
