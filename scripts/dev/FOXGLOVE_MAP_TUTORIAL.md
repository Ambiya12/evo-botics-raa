# Create a Map with Foxglove

This tutorial creates a ROS 2 occupancy map with `slam_toolbox`, displays it live in
Foxglove, lets you drive the robot from Foxglove, and saves the final map for Nav2.

Starting the complete mapping stack is one command:

```bash
./scripts/dev/foxglove_map.sh start
```

When the map is complete, save it and stop the stack:

```bash
./scripts/dev/foxglove_map.sh save ground_floor
./scripts/dev/foxglove_map.sh stop
```

## What the helper starts

The `start` command launches these processes in detached `tmux` sessions on the Jetson:

- robot bringup: lidar, odometry, TF, and base control;
- camera;
- `slam_toolbox`: builds `/map` from `/scan_multi`;
- the project web service and rosbridge on port `9090` for the admin dashboard;
- Foxglove Bridge on port `8765`.

The processes keep running if you close your Mac terminal.

## 1. Prerequisites

Run commands from the repository root on your Mac.

Check the saved Jetson configuration:

```bash
./scripts/robot/robot.sh config show
```

If DHCP changed the robot IP:

```bash
./scripts/robot/robot.sh config ip <jetson-ip>
```

Make sure the workspace is built inside the robot container:

```bash
./scripts/robot/robot.sh setup
```

Install the Foxglove desktop application on your Mac. The web application can also
connect, but the desktop application is usually simpler for local robot development.

### One-time Foxglove Bridge installation

Foxglove recommends its native bridge for live ROS 2 visualization because it provides
better features, performance, and stability than rosbridge.

If the helper reports that `foxglove_bridge` is missing, use the exact container name
printed by the error:

```bash
ssh jetson@<jetson-ip>
docker exec -it <container> bash -lc '
  apt-get update &&
  apt-get install -y ros-humble-foxglove-bridge
'
exit
```

The robot container is recreated after some reboots, so this package may need to be
installed again unless it is added to the Docker image.

## 2. Start mapping

```bash
./scripts/dev/foxglove_map.sh start
```

The command checks that the container and Foxglove Bridge exist, starts the complete
mapping stack, and prints the connection URL:

```text
ws://<jetson-ip>:8765
```

To inspect the stack at any time:

```bash
./scripts/dev/foxglove_map.sh status
```

You should see these important topics:

```text
/map
/scan_multi
/odom
/tf
/tf_static
/cmd_vel_teleop
```

It can take a few seconds and a small first movement before `/map` appears.

## 3. Connect Foxglove

In Foxglove:

1. Select **Open connection**.
2. Select **Foxglove WebSocket**.
3. Enter `ws://<jetson-ip>:8765`.
4. Select **Open**.

Do not select a rosbridge connection for this workflow. Port `8765` uses the native
Foxglove protocol.

## 4. Connect the admin dashboard

Foxglove and the admin dashboard use separate WebSocket servers and can run at the same
time:

```text
Foxglove:       ws://<jetson-ip>:8765  (native Foxglove protocol)
Admin dashboard: ws://<jetson-ip>:9090  (rosbridge protocol)
Camera:         http://<jetson-ip>:8080/camera/stream
```

Start the Laravel dashboard on your Mac in another terminal:

```bash
cd reservationApp
composer dev
```

Open:

```text
http://127.0.0.1:8000/admin/robot
```

In the admin sidebar, open **Connection** and enter:

```text
Robot IP:    <jetson-ip>
ROS port:    9090
Camera port: 8080
Camera path: /camera/stream
```

The connection indicator should become connected. Then open **Teleop** in the sidebar.
The dashboard already publishes `geometry_msgs/msg/Twist` commands to
`/cmd_vel_teleop`, which is the correct safety-gated topic for mapping.

If the mapping stack was started before this update with rosbridge disabled, restart it:

```bash
./scripts/dev/foxglove_map.sh stop
./scripts/dev/foxglove_map.sh start
```

## 5. Create the mapping layout

Add a **3D** panel and configure it:

1. Set the display frame to `map`.
2. Enable `/map` to show the occupancy grid.
3. Enable `/scan_multi` to show lidar points.
4. Enable the robot model or TF frames if useful.

The map colors normally mean:

- light cells: known free space;
- dark cells: occupied space such as walls;
- gray/transparent cells: unexplored space.

If the panel says that a transform is missing, confirm that `/tf` and `/tf_static` are
available and that the display frame is exactly `map`.

## 6. Add safe teleoperation in Foxglove

Add a **Teleop** panel. Configure:

```text
Message type: geometry_msgs/msg/Twist
Topic:        /cmd_vel_teleop
Publish rate: 10 Hz
Stop on release: enabled
```

Suggested low-speed controls for mapping:

```text
Forward:  linear.x  =  0.15
Backward: linear.x  = -0.10
Left:     angular.z =  0.35
Right:    angular.z = -0.35
Stop:     all values = 0.0
```

Use `/cmd_vel_teleop`, not `/cmd_vel`. The mapping launch includes the project's safety
gate, which validates and forwards teleoperation commands to the robot.

Keep the robot in sight, begin in an open area, and be ready to use the center stop
button. Foxglove visualization is not a replacement for physical supervision.

You only need this Foxglove Teleop panel if you prefer it over the dashboard's **Teleop**
page. Do not drive from both interfaces simultaneously.

## 7. Drive a good mapping route

For a cleaner map:

1. Start in an open, recognizable area.
2. Drive slowly and avoid sudden turns.
3. Keep walls within lidar range.
4. Trace the outside of the area first, then cover internal corridors and rooms.
5. Revisit the starting area so SLAM can detect loop closure.
6. Stop moving and wait a few seconds before saving.

Avoid moving chairs, people walking next to the lidar, reflective glass, and repeatedly
driving the robot by hand while its wheels are off the floor. These can distort lidar or
odometry measurements.

## 8. Save the map

Choose a descriptive name without spaces or a file extension:

```bash
./scripts/dev/foxglove_map.sh save ground_floor
```

The helper:

1. validates the map name;
2. confirms that `/map` is publishing;
3. refuses to overwrite an existing map;
4. runs Nav2's `map_saver_cli`;
5. verifies both generated files;
6. copies them from Docker to persistent storage on the Jetson host.

Generated files:

```text
Docker:
  /root/maps/ground_floor.yaml
  /root/maps/ground_floor.pgm

Persistent Jetson backup:
  /home/jetson/maps/ground_floor.yaml
  /home/jetson/maps/ground_floor.pgm
```

The `.yaml` metadata file and `.pgm` image belong together. Always copy, rename, or back
up both files.

If no name is supplied, the helper creates a timestamped name:

```bash
./scripts/dev/foxglove_map.sh save
# Example: map_20260618_143500
```

## 9. Stop mapping

```bash
./scripts/dev/foxglove_map.sh stop
```

Save before stopping. Unsaved map data exists only in the running SLAM process.

## 10. Test the saved map with Nav2

The map must exist inside Docker before starting navigation:

```bash
MAP_PATH=/root/maps/ground_floor.yaml \
  ./scripts/robot/robot.sh start navigate
```

If the Docker container was recreated, restore the persistent backup first:

```bash
ssh jetson@<jetson-ip>
C=$(docker ps --format '{{.Names}}' | head -n1)
docker exec "$C" mkdir -p /root/maps
docker cp ~/maps/ground_floor.yaml "$C":/root/maps/ground_floor.yaml
docker cp ~/maps/ground_floor.pgm  "$C":/root/maps/ground_floor.pgm
exit
```

Then start navigation with the `MAP_PATH` command above.

## Troubleshooting

### Foxglove cannot connect

```bash
./scripts/dev/foxglove_map.sh status
```

Confirm that port `8765` is open, the Jetson IP is current, and the Mac is on the same
network as the robot. Also check the bridge log:

```bash
ssh jetson@<jetson-ip> -t tmux attach-session -t evo_foxglove
```

Detach without stopping it with `Ctrl-b`, then `d`.

### The admin dashboard cannot connect

Check both bridge ports:

```bash
./scripts/dev/foxglove_map.sh status
```

Port `9090` must be open for the dashboard. In **Connection**, use only the Jetson IP in
the Robot IP field—do not include `ws://` or a port there. Keep ROS port set to `9090`.

If Foxglove connects on `8765` but `9090` is closed, restart the mapping stack:

```bash
./scripts/dev/foxglove_map.sh stop
./scripts/dev/foxglove_map.sh start
```

### `/map` is missing

Check SLAM logs:

```bash
./scripts/robot/robot.sh logs slam
```

Then verify that `/scan_multi` and `/odom` publish data. If the base board is silent:

```bash
./scripts/robot/robot.sh mcu
```

If the logs repeatedly contain this message:

```text
Message Filter dropping message ... discarding message because the queue is full
```

SLAM is receiving lidar data before the matching TF transform is ready. The repository's
`slam_toolbox_params.yaml` sets `scan_queue_size: 20` so short Jetson scheduling delays
do not discard every scan. Deploy the current workspace configuration and restart SLAM:

```bash
./scripts/robot/robot.sh setup --push
./scripts/robot/robot.sh stop slam
./scripts/robot/robot.sh start slam
```

The restart starts a fresh mapping session. In the SLAM log, the repeated queue-full
messages should stop; in Foxglove, `/map` should expand after moving at least `0.3 m`.

### The robot does not move from Foxglove

- Confirm the Teleop topic is `/cmd_vel_teleop`.
- Confirm **Stop on release** is enabled.
- Check that `/odom_raw` is alive with `./scripts/robot/robot.sh status`.
- Make sure no emergency stop is latched.
- Never bypass the safety gate by publishing directly to `/cmd_vel`.

### Saving times out

Do not stop SLAM before saving. Confirm that the 3D panel shows a real map, then run:

```bash
./scripts/dev/foxglove_map.sh status
./scripts/dev/foxglove_map.sh save another_name
```

`/map` is a latched ROS 2 topic with `TRANSIENT_LOCAL` durability. The save helper uses
the same QoS when validating the map, so it can retrieve a completed map even when the
robot has stopped moving and SLAM is not publishing a new update.

### A map name already exists

The script intentionally refuses to overwrite maps. Use a versioned name:

```bash
./scripts/dev/foxglove_map.sh save ground_floor_v2
```

## Command reference

```bash
./scripts/dev/foxglove_map.sh start
./scripts/dev/foxglove_map.sh status
./scripts/dev/foxglove_map.sh save [map-name]
./scripts/dev/foxglove_map.sh stop
./scripts/dev/foxglove_map.sh help
```
