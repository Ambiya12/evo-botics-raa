# Evo-Botics Robot Launch Guide

This guide gives two complete launch cases for the admin robot dashboard.

- Case 1: start from zero, create a new map, save it, then use it for navigation.
- Case 2: start from zero, use an existing map already saved on the Jetson host.

Robot values used in this guide:

```text
Jetson IP: 10.10.221.115
Jetson user: jetson
Expected Docker container: m3pro
ROS bridge port: 9090
Camera web port: 8080
Laravel app: http://127.0.0.1:8000/admin/robot
```

If your Docker container is not named `m3pro`, replace `m3pro` in every command with the real name from:

```bash
ssh jetson@10.10.221.115
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

Before starting a case, stop old ROS launch terminals if they are already running. Use `Ctrl+C` in each ROS terminal.

## Common Dashboard Values

Use these values in the Laravel admin dashboard:

```text
Robot IP: 10.10.221.115
ROS Port: 9090
Camera Port: 8080
Camera Path: /camera/stream
Save Map Path: /root/maps/admin_map
```

## Common ROS Shell Setup

Each time you enter the Docker container, run this setup before ROS commands:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

## Case 1: Create A New Map From The Beginning

Use this case when you do not have a finished map yet, or when you want to create a new map by driving the robot around.

### Terminal 1: Check The Robot And Container

On your Mac:

```bash
ssh jetson@10.10.221.115
```

On the Jetson:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

Check that the container exists:

```bash
docker exec m3pro ls /root
```

### Terminal 2: Start Robot Bringup

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 launch slam_mapping bringup.launch.py
```

Leave this terminal running.

### Terminal 3: Start SLAM Mapping

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 launch m3pro_teacher_nav slam_online.launch.py rviz:=false
```

Leave this terminal running.

### Terminal 4: Start Camera Topic

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ls -la /dev/video*
ros2 launch slam_mapping app_camera.launch.py
```

Leave this terminal running.

If `ls -la /dev/video*` does not show a camera device, the Docker container cannot see the camera. The dashboard cannot fix that; the container must be started with camera device access.

### Terminal 5: Start Rosbridge And Camera Web Server

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 launch m3pro_teacher_web web_dashboard.launch.py port:=8080 camera_topic:=/camera/color/image_raw
```

Leave this terminal running.

If you get an error because port `9090` is already used, run this instead:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py rosbridge:=false port:=8080 camera_topic:=/camera/color/image_raw
```

### Terminal 6: Verify Mapping Topics

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 topic list | grep -Ei 'map|scan|odom|cmd_vel|camera|image|depth|rgb|color'
```

Check the map topic:

```bash
ros2 topic echo /map --once
```

Check the camera topic:

```bash
ros2 topic hz /camera/color/image_raw
```

If `/camera/color/image_raw` does not exist, find the real camera topic:

```bash
ros2 topic list | grep -Ei 'camera|image|depth|rgb|color'
```

Then restart the web server command with the real topic:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py rosbridge:=false port:=8080 camera_topic:=/REAL/CAMERA/TOPIC
```

### Terminal 7: Open The Admin Dashboard

On your Mac, start Laravel:

```bash
cd "/Users/galystan/Documents/HETIC - WEB 3/RAA/evo-botics-raa/reservationApp"
php artisan serve --host=127.0.0.1 --port=8000
```

Leave this terminal running.

Open another terminal on your Mac and start Vite:

```bash
cd "/Users/galystan/Documents/HETIC - WEB 3/RAA/evo-botics-raa/reservationApp"
npm run dev -- --host 127.0.0.1
```

Open this URL in your browser:

```text
http://127.0.0.1:8000/admin/robot
```

Use the dashboard to drive the robot slowly and build the map. When the map looks good, save it.

### Terminal 8: Save The New Map

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
mkdir -p /root/maps
ros2 run nav2_map_server map_saver_cli -f /root/maps/admin_map
ls -la /root/maps
cat /root/maps/admin_map.yaml
```

You should see:

```text
/root/maps/admin_map.yaml
/root/maps/admin_map.pgm
```

### Terminal 9: Restart Into Navigation Mode With The New Map

Stop the SLAM terminal with `Ctrl+C`. Keep robot bringup running.

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 launch m3pro_teacher_nav navigation.launch.py map:=/root/maps/admin_map.yaml rviz:=false
```

Now the dashboard map click should send Nav2 goals to the robot.

## Case 2: Use An Existing Map From The Beginning

Use this case when the map already exists on the Jetson host in:

```text
~/maps_backup/demo_map.pgm
~/maps_backup/demo_map.yaml
```

### Terminal 1: Check Existing Map And Copy It Into Docker

On your Mac:

```bash
ssh jetson@10.10.221.115
```

On the Jetson:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
ls -la ~/maps_backup
docker exec m3pro mkdir -p /root/maps
docker cp ~/maps_backup/demo_map.yaml m3pro:/root/maps/demo_map.yaml
docker cp ~/maps_backup/demo_map.pgm m3pro:/root/maps/demo_map.pgm
docker exec m3pro sh -lc "cd /root/maps && sed -i 's#^image:.*#image: demo_map.pgm#' demo_map.yaml"
docker exec m3pro ls -la /root/maps
docker exec m3pro cat /root/maps/demo_map.yaml
```

You should see:

```text
/root/maps/demo_map.yaml
/root/maps/demo_map.pgm
```

### Terminal 2: Start Robot Bringup

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 launch slam_mapping bringup.launch.py
```

Leave this terminal running.

### Terminal 3: Start Navigation With Existing Map

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 launch m3pro_teacher_nav navigation.launch.py map:=/root/maps/demo_map.yaml rviz:=false
```

Leave this terminal running.

### Terminal 4: Start Camera Topic

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ls -la /dev/video*
ros2 launch slam_mapping app_camera.launch.py
```

Leave this terminal running.

### Terminal 5: Start Rosbridge And Camera Web Server

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 launch m3pro_teacher_web web_dashboard.launch.py port:=8080 camera_topic:=/camera/color/image_raw
```

Leave this terminal running.

If you get an error because port `9090` is already used, run this instead:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py rosbridge:=false port:=8080 camera_topic:=/camera/color/image_raw
```

### Terminal 6: Verify Navigation And Camera Topics

Open a new terminal on your Mac:

```bash
ssh jetson@10.10.221.115
docker exec -it m3pro bash
```

Inside Docker:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/m3pro_teacher_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
ros2 topic list | grep -Ei 'map|odom|cmd_vel|goal|camera|image|depth|rgb|color'
```

Check the map:

```bash
ros2 topic echo /map --once
```

Check odometry:

```bash
ros2 topic echo /odom --once
```

Check the camera:

```bash
ros2 topic hz /camera/color/image_raw
```

If `/camera/color/image_raw` does not exist, find the real camera topic:

```bash
ros2 topic list | grep -Ei 'camera|image|depth|rgb|color'
```

Then restart the web server command with the real topic:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py rosbridge:=false port:=8080 camera_topic:=/REAL/CAMERA/TOPIC
```

### Terminal 7: Start Laravel Backend

On your Mac:

```bash
cd "/Users/galystan/Documents/HETIC - WEB 3/RAA/evo-botics-raa/reservationApp"
php artisan serve --host=127.0.0.1 --port=8000
```

Leave this terminal running.

### Terminal 8: Start Vite Frontend

On your Mac, open another terminal:

```bash
cd "/Users/galystan/Documents/HETIC - WEB 3/RAA/evo-botics-raa/reservationApp"
npm run dev -- --host 127.0.0.1
```

Leave this terminal running.

### Terminal 9: Open The Admin Dashboard

Open this URL in your browser:

```text
http://127.0.0.1:8000/admin/robot
```

Use these values:

```text
Robot IP: 10.10.221.115
ROS Port: 9090
Camera Port: 8080
Camera Path: /camera/stream
Save Map Path: /root/maps/admin_map
```

Test the camera stream directly:

```text
http://10.10.221.115:8080/camera/stream
```

## Useful Debug Commands

Run these inside the Docker container after the common ROS shell setup.

List all topics:

```bash
ros2 topic list
```

Find camera topics:

```bash
ros2 topic list | grep -Ei 'camera|image|depth|rgb|color'
```

Find navigation topics:

```bash
ros2 topic list | grep -Ei 'map|odom|scan|cmd_vel|goal|tf'
```

Check rosbridge is running:

```bash
ros2 node list | grep -Ei 'rosbridge|web'
```

Check camera frame rate:

```bash
ros2 topic hz /camera/color/image_raw
```

Check map data:

```bash
ros2 topic echo /map --once
```

Check robot odometry:

```bash
ros2 topic echo /odom --once
```

Check camera hardware inside Docker:

```bash
ls -la /dev/video*
```

Check port usage on the Jetson:

```bash
ss -ltnp | grep -Ei ':8080|:9090'
```

## Common Problems

### The Dashboard Says ROS Bridge Connected But Map Is Waiting

Navigation or SLAM is not publishing `/map`.

For a new map, make sure this is running:

```bash
ros2 launch m3pro_teacher_nav slam_online.launch.py rviz:=false
```

For an existing map, make sure this is running:

```bash
ros2 launch m3pro_teacher_nav navigation.launch.py map:=/root/maps/demo_map.yaml rviz:=false
```

### The Camera Topic Does Not Exist

Start the camera driver:

```bash
ros2 launch slam_mapping app_camera.launch.py
```

Then check:

```bash
ros2 topic list | grep -Ei 'camera|image|depth|rgb|color'
```

If there is still no camera topic, check camera hardware:

```bash
ls -la /dev/video*
```

If no `/dev/video*` exists inside Docker, the container does not have access to the camera device.

### The Camera Topic Exists But The Web Stream Is Broken

Restart the web server using the exact camera topic:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py rosbridge:=false port:=8080 camera_topic:=/camera/color/image_raw
```

Then test:

```text
http://10.10.221.115:8080/camera/stream
```

### Port 9090 Is Already Used

Start the web server without starting a second rosbridge:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py rosbridge:=false port:=8080 camera_topic:=/camera/color/image_raw
```

### Port 8080 Is Already Used

Use port `8081`:

```bash
ros2 launch m3pro_teacher_web web_dashboard.launch.py rosbridge:=false port:=8081 camera_topic:=/camera/color/image_raw
```

Then use these dashboard values:

```text
Camera Port: 8081
Camera Path: /camera/stream
```
