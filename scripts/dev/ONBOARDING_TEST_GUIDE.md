# Evo-Botics — Full Onboarding Test Guide

This guide tests the complete visitor journey:

1. A user books a room.
2. The user receives a confirmation email.
3. The robot displays the QR scanning screen.
4. `evo_vision` scans the QR code.
5. `evo_reception` validates the reservation.
6. The robot displays the success screen.

## Network values

Current Jetson IP:

```text
10.10.220.6
```

Find the Mac IP:

```bash
ipconfig getifaddr en0
```

In this guide, replace `<MAC_IP>` with the result.

Example:

```text
Mac:    10.10.220.25
Jetson: 10.10.220.6
```

Both devices must be connected to the same network.

---

## 1. Configure the reservation application

From the project root:

```bash
cd reservationApp
```

Create `.env` if it does not exist:

```bash
cp .env.example .env
```

Update these values in `.env`:

```env
APP_URL=http://<MAC_IP>:8000
APP_PORT=8000

ROBOT_ROSBRIDGE_URL=ws://10.10.220.6:9090

DB_CONNECTION=mysql
DB_HOST=mysql
DB_PORT=3306
DB_DATABASE=reservation_app
DB_USERNAME=sail
DB_PASSWORD=password

MAIL_MAILER=smtp
MAIL_HOST=mailpit
MAIL_PORT=1025
MAIL_USERNAME=null
MAIL_PASSWORD=null
MAIL_ENCRYPTION=null

FORWARD_MAILPIT_DASHBOARD_PORT=8025
```

---

## 2. Start Laravel Sail

Start Docker Desktop first.

Then run:

```bash
./vendor/bin/sail up -d
```

Install dependencies:

```bash
./vendor/bin/sail composer install
./vendor/bin/sail npm install
```

Prepare Laravel:

```bash
./vendor/bin/sail artisan key:generate
./vendor/bin/sail artisan migrate:fresh --seed
./vendor/bin/sail artisan config:clear
```

Start Vite:

```bash
./vendor/bin/sail npm run dev
```

Keep this terminal open.

Check the containers:

```bash
./vendor/bin/sail ps
```

Open the application:

```text
http://<MAC_IP>:8000
```

Open Mailpit:

```text
http://<MAC_IP>:8025
```

---

## 3. Check that the Jetson can reach Laravel

From the Mac:

```bash
ssh jetson@10.10.220.6
```

From the Jetson:

```bash
curl -I http://<MAC_IP>:8000/kiosk
```

An HTTP response such as `200 OK` means the connection works.

Return to the Mac:

```bash
exit
```

---

## 4. Start the robot development stack

From the project root on the Mac:

```bash
cd "/Users/galystan/Documents/HETIC - WEB 3/RAA/evo-botics-raa"
```

Find the active robot container:

```bash
ssh jetson@10.10.220.6 \
  "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

Start the robot stack. Replace `<CONTAINER>` with the active container name:

```bash
JETSON_IP=10.10.220.6 \
CONTAINER=<CONTAINER> \
ATTACH=0 \
./scripts/dev/start_robot_tmux.sh
```

This starts:

- Robot bringup
- Camera
- `evo_vision`
- `evo_web`
- Rosbridge

Check the robot tmux session:

```bash
ssh jetson@10.10.220.6 -t \
  tmux attach-session -t evo-robot
```

To detach without stopping it, press:

```text
Ctrl-b, then d
```

---

## 5. Start evo_reception

The current development script does not start `evo_reception`. Start it manually.

Connect to the Jetson:

```bash
ssh jetson@10.10.220.6
```

Find the active container:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Enter it:

```bash
docker exec -it \
  -e ROS_DOMAIN_ID=30 \
  -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 \
  <CONTAINER> bash
```

Inside the container:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/evo_ws/install/setup.bash

export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

Start reception:

```bash
ros2 launch evo_reception reception.launch.py \
  validation_url:=http://<MAC_IP>:8000/api/reservations/validate
```

Keep this terminal open.

Do not use `127.0.0.1` in the validation URL. Laravel runs on the Mac, not on the Jetson.

---

## 6. Check the ROS services

Open another Jetson container terminal and source ROS using the commands from the previous step.

Check the nodes:

```bash
ros2 node list | grep -E 'qr_scanner|qr_reservation'
```

Expected nodes:

```text
/qr_scanner_node
/qr_reservation_bridge_node
```

Check the camera:

```bash
ros2 topic hz /camera/color/image_raw
```

Check the QR scanner:

```bash
ros2 topic echo /vision/qr/status --once
```

`selected_backend` must be `pyzbar` or `opencv`.

If it is `null`, install the QR decoder inside the container:

```bash
apt-get update
apt-get install -y libzbar0 python3-pyzbar
```

Then restart the `vision` tmux window.

---

## 7. Open the robot kiosk

On the robot screen, open:

```text
http://<MAC_IP>:8000/kiosk
```

Expected screen:

```text
Welcome to EVOBOTICS
Show your reservation QR code
Waiting for the robot camera...
```

Use `/kiosk`, not `/kiosk?scan=browser`.

---

## 8. Create a reservation

Open this page on a computer:

```text
http://<MAC_IP>:8000/register
```

Create a normal user account, log in, and open:

```text
http://<MAC_IP>:8000/reservation
```

Choose:

- A future date
- An available time
- A valid number of guests

Press **Book now**.

---

## 9. Get the QR code from Mailpit

Open:

```text
http://<MAC_IP>:8025
```

Open the latest **Reservation Confirmed** email.

### Current Mailpit limitation

The QR is generated correctly, but Mailpit may not display it because it is embedded as an SVG `data:` URL.

To display it:

1. Open the email source or HTML view in Mailpit.
2. Search for:

```text
data:image/svg+xml;base64,
```

3. Copy the complete value inside:

```html
src="..."
```

4. Paste that value into a new browser tab.
5. The QR code should appear.

Keep the QR code open for the robot scan.

---

## 10. Monitor the QR scan

In one ROS terminal:

```bash
ros2 topic echo /vision/qr/detections
```

In another ROS terminal:

```bash
ros2 topic echo /reception/qr/status
```

Show the QR code to the robot camera.

Expected states:

```text
waiting
scanned
validating
success
```

Expected kiosk screens:

```text
Show your reservation QR code
QR detected
Validating your reservation...
Success
Please follow me!
```

The kiosk should then return to the welcome screen.

---

## 11. Check the reservation in the database

On the Mac:

```bash
cd reservationApp
./vendor/bin/sail artisan tinker
```

Run:

```php
App\Models\Reservation::latest()->first([
    'uuid',
    'customer_name',
    'status',
    'validated_at'
]);
```

Expected result:

```text
status = validated
validated_at = a valid date and time
```

Exit Tinker:

```php
exit
```

Scan the same QR again to test the already-used error.

Expected result:

```text
already_used
```

---

## Quick troubleshooting

### Laravel does not start

```bash
./vendor/bin/sail ps
./vendor/bin/sail logs laravel.test
```

### Jetson cannot reach Laravel

From the Jetson:

```bash
curl -I http://<MAC_IP>:8000/kiosk
```

Check that Docker Desktop is running and that macOS Firewall allows Docker connections.

### Camera does not publish

```bash
ros2 topic hz /camera/color/image_raw
```

### QR code is not detected

```bash
ros2 topic echo /vision/qr/status --once
ros2 topic echo /vision/qr/detections
```

Make the QR large and bright, keep it steady, and avoid screen reflections.

### Reception cannot validate the QR

From the Jetson:

```bash
curl -I http://<MAC_IP>:8000
```

Check that `evo_reception` uses:

```text
http://<MAC_IP>:8000/api/reservations/validate
```

### Kiosk does not update

Check rosbridge:

```bash
ss -ltn | grep 9090
```

Check reception messages:

```bash
ros2 topic echo /reception/qr/status
```

---

## Stop everything

Stop Laravel Sail:

```bash
cd reservationApp
./vendor/bin/sail down
```

Stop the robot tmux session:

```bash
ssh jetson@10.10.220.6 \
  "tmux kill-session -t evo-robot"
```

Stop the manual `evo_reception` command with:

```text
Ctrl-c
```
