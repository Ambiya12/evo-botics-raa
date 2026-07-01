# Robot Launch

## After Every ROS Package Change

From the repository root on the development computer, run exactly:

```bash
./scripts/robot.sh setup
```

This single command:

1. Copies `evo_ws/src` to `jetson@192.168.1.9:/home/jetson/evo_ws/src`.
2. Copies the Jetson workspace into the robot Docker container at
   `/root/evo_ws`.
3. Runs `colcon build --symlink-install` inside Docker.

Do not run another copy or build command after `setup`.

Configure the robot IP once, only if it is not already configured:

```bash
./scripts/robot.sh config ip 192.168.1.9
```

After deployment, connect to the robot:

```bash
ssh jetson@192.168.1.9
```

> Apartment safety: keep the stationary orchestrator running. Do not launch
> saved-map navigation, `navigation.launch.py`, or `slam_and_nav.launch.py`.

## Main Idea

Source code moves through one fixed path:

```text
local evo_ws/src → Jetson /home/jetson/evo_ws/src → Docker /root/evo_ws → build
```

The `setup` command handles that complete path. After it finishes, enter the
ROS Docker container from the Jetson:

```bash
docker ps
docker exec -it <robot-container> bash
```

Inside Docker, prepare every terminal with:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/evo_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

Do not run `./scripts/robot.sh setup` inside the Jetson SSH session. Run it
from the development repository, then use SSH only for launching and observing
ROS.

## Flow 0: Apartment-Safe Real Voice

Use separate Docker terminals for stationary navigation, voice, and
observation.

### Keep Navigation Mocked

```bash
ros2 launch evo_navigation stationary_orchestrator.launch.py
```

Confirm in another sourced Docker terminal:

```bash
ros2 param get /navigation_orchestrator_node mock_navigation
ros2 param get /navigation_orchestrator_node allow_real_navigation
```

Required results are `True` and `False`.

### Discover Audio Devices

Run manually inside Docker and record the selected identifiers in the session
evidence:

```bash
python3 -c 'import speech_recognition as sr; print(*enumerate(sr.Microphone.list_microphone_names()), sep="\\n")'
mpv --audio-device=help
```

Do not add the discovered identifiers to tracked configuration. Use launch
arguments or a local, ignored parameter file.

Set session-local values:

```bash
export PIPER_MODEL=/absolute/local/path/to/voice.onnx
export WHISPER_MODEL=/absolute/local/path/to/faster-whisper-model
export AUDIO_OUTPUT='<mpv-audio-device>'
export MIC_INDEX='<microphone-index>'
```

### Phase A1 — Real Piper TTS and Speaker

STT stays mocked:

```bash
ros2 launch evo_voice reception_voice.launch.py \
  tts_mock_audio:=false \
  stt_mock_audio:=true \
  piper_model_path:="$PIPER_MODEL" \
  audio_output_device:="$AUDIO_OUTPUT"
```

Observe and request speech from another sourced Docker terminal:

```bash
ros2 topic echo /voice/tts/status
ros2 topic pub --once /voice/tts/request std_msgs/msg/String "{data: 'phrase:greeting'}"
ros2 topic pub --once /voice/tts/request std_msgs/msg/String "{data: 'phrase:clarify_intent'}"
```

### Phase A2 — Real Microphone, VAD, and STT

TTS stays mocked:

```bash
ros2 launch evo_voice reception_voice.launch.py \
  tts_mock_audio:=true \
  stt_mock_audio:=false \
  stt_model_path:="$WHISPER_MODEL" \
  microphone_device:="$MIC_INDEX" \
  language:=en \
  vad_rms_threshold:=0.01 \
  minimum_confidence:=0.4
```

Observe:

```bash
ros2 topic echo /voice/stt/transcript
ros2 topic echo /voice/intent/result
```

The default capture file is under `/tmp`, outside the repository. Do not copy
raw visitor audio into the repository; remove temporary captures after the
session if they are not needed.

### Phase A3 — Duplex Voice, Intent, and Dialogue

```bash
ros2 launch evo_voice reception_voice.launch.py \
  tts_mock_audio:=false \
  stt_mock_audio:=false \
  piper_model_path:="$PIPER_MODEL" \
  audio_output_device:="$AUDIO_OUTPUT" \
  stt_model_path:="$WHISPER_MODEL" \
  microphone_device:="$MIC_INDEX" \
  language:=en
```

Start the dialogue manager only when its non-voice dependencies for the
planned check are available:

```bash
ros2 launch evo_reception dialogue_manager.launch.py
```

Observe:

```bash
ros2 topic echo /voice/tts/status
ros2 topic echo /voice/stt/transcript
ros2 topic echo /voice/intent/result
ros2 topic echo /reception/dialogue/state
```

While TTS reports `speaking`, STT must publish no robot-speech transcript.
Capture must resume after `completed`, `failed`, or `idle`. Stop and record a
blocker if the robot transcribes itself repeatedly.

## Reservation App Setup

If the reservation app runs on another computer, configure its IP:

```bash
./scripts/robot.sh config app-host <mac-ip>
./scripts/robot.sh config app-port 8000
```

Check the current config:

```bash
./scripts/robot.sh config show
```

## Flow 1: Create And Launch A New Map

Use this when you need to create a map, save it, then launch navigation with that saved map.

Start mapping:

```bash
./scripts/robot.sh map foxglove
```

Open Foxglove and connect to:

```text
ws://<jetson-ip>:8765
```

When the map is ready:

```bash
./scripts/robot.sh save-map school_map
./scripts/robot.sh map stop
```

Launch navigation with the saved map:

```bash
./scripts/robot.sh nav school_map
```

You can save and launch another map name if needed:

```bash
./scripts/robot.sh save-map ground_floor
./scripts/robot.sh nav ground_floor
```

## Flow 2: Normal Robot Launch

Use this for the usual robot run: saved `school_map` navigation plus the reservation QR kiosk on the robot screen.

First, make sure the reservation app is running on your Mac:

```bash
cd reservationApp
composer dev
```

Then start the robot with one command:

```bash
./scripts/robot.sh launch
```

This command handles the reboot-safe steps:

```text
sync school_map into Docker
install QR decoder packages if missing
restore/build evo_ws in Docker if missing
start navigation with /root/maps/school_map.yaml
start camera + QR scanner + reservation bridge + web stream
open the kiosk on the robot screen
wake/check the MCU
```

To launch another saved map:

```bash
./scripts/robot.sh launch ground_floor
```

To stop the normal robot launch:

```bash
./scripts/robot.sh stop launch
```

## Useful Commands

```bash
./scripts/robot.sh status
./scripts/robot.sh logs nav
./scripts/robot.sh logs vision
./scripts/robot.sh logs reception
./scripts/robot.sh kiosk
./scripts/robot.sh stop all
./scripts/robot.sh mcu
```

Use `Ctrl-b` then `d` to detach from logs without stopping the robot.

## Files And Defaults

Saved map files on the Jetson host:

```text
/home/<user>/maps/school_map.yaml
/home/<user>/maps/school_map.pgm
```

Map files inside Docker after launch:

```text
/root/maps/school_map.yaml
/root/maps/school_map.pgm
```

Robot kiosk URL:

```text
http://<mac-ip>:8000/kiosk?scan=robot
```
