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

Find the installed local models and required executables first:

```bash
find /root -type f -name '*.onnx' 2>/dev/null
command -v piper
command -v mpv
```

If no Piper model exists, download it once on the development computer:

```bash
python3 -m pip install -U huggingface_hub hf_xet
hf download rhasspy/piper-voices \
  en/en_US/lessac/medium/en_US-lessac-medium.onnx \
  en/en_US/lessac/medium/en_US-lessac-medium.onnx.json \
  --local-dir ~/Downloads/piper
scp ~/Downloads/piper/en/en_US/lessac/medium/en_US-lessac-medium.onnx* \
  jetson@192.168.1.9:/home/jetson/
```

On the Jetson host, use the container name shown by `docker ps`:

```bash
docker ps
docker exec <robot-container> mkdir -p /root/models/piper
docker cp /home/jetson/en_US-lessac-medium.onnx \
  <robot-container>:/root/models/piper/
docker cp /home/jetson/en_US-lessac-medium.onnx.json \
  <robot-container>:/root/models/piper/
docker exec -it <robot-container> bash
```

Inside Docker, verify and test the model:

```bash
export PIPER_MODEL=/root/models/piper/en_US-lessac-medium.onnx
echo '5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f  /root/models/piper/en_US-lessac-medium.onnx' \
  | sha256sum --check
command -v piper
command -v mpv
echo "Hello from EVO" \
  | piper --model "$PIPER_MODEL" --output_file /tmp/piper-test.wav
```

Omit `audio_output_device` to use the system-default speaker. If the default is
wrong, select a real value from `mpv --audio-device=help`, set
`AUDIO_OUTPUT`, and add `audio_output_device:="$AUDIO_OUTPUT"` to the launch.

### Phase A1 — Real Piper TTS and Speaker

STT stays mocked:

```bash
ros2 launch evo_voice reception_voice.launch.py \
  tts_mock_audio:=false \
  stt_mock_audio:=true \
  piper_model_path:=/root/models/piper/en_US-lessac-medium.onnx
```

Observe and request speech from another sourced Docker terminal:

```bash
ros2 topic echo /voice/tts/status
ros2 topic pub --once /voice/tts/request std_msgs/msg/String "{data: 'phrase:greeting'}"
ros2 topic pub --once /voice/tts/request std_msgs/msg/String "{data: 'phrase:clarify_intent'}"
```

### Phase A2 — Real Microphone, VAD, and STT

Provision the English `tiny.en` Faster Whisper model once on the Jetson host:

```bash
WHISPER_DIR=/home/jetson/models/faster-whisper-tiny.en
WHISPER_URL=https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main
mkdir -p "$WHISPER_DIR"
wget -c -O "$WHISPER_DIR/model.bin" \
  "$WHISPER_URL/model.bin?download=true"
for file in config.json tokenizer.json vocabulary.txt; do
  wget -O "$WHISPER_DIR/$file" \
    "$WHISPER_URL/$file?download=true"
done
echo '1a5afae06a4db91c975c9a9d78be5cc110ee4ea022ad57d55492e4550e936b2a  /home/jetson/models/faster-whisper-tiny.en/model.bin' \
  | sha256sum --check
```

On the Jetson host, copy it into the current robot container:

```bash
docker ps --format '{{.Names}}'
read -r -p "Robot container name: " ROBOT_CONTAINER
docker exec "$ROBOT_CONTAINER" mkdir -p /root/models
docker cp /home/jetson/models/faster-whisper-tiny.en \
  "$ROBOT_CONTAINER":/root/models/
docker exec -it "$ROBOT_CONTAINER" bash
```

Inside Docker, set:

```bash
python3 -m pip install --no-cache-dir faster-whisper SpeechRecognition
python3 -c 'from faster_whisper import WhisperModel; import speech_recognition; print("Voice Python dependencies ready")'
python3 -c 'import pyaudio; print("PyAudio ready")'
export WHISPER_MODEL=/root/models/faster-whisper-tiny.en
export MIC_INDEX=-1
test -f "$WHISPER_MODEL/model.bin"
```

TTS stays mocked:

```bash
ros2 launch evo_voice reception_voice.launch.py \
  tts_mock_audio:=true \
  stt_mock_audio:=false \
  stt_model_path:=/root/models/faster-whisper-tiny.en \
  microphone_device:=-1 \
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
  piper_model_path:=/root/models/piper/en_US-lessac-medium.onnx \
  stt_model_path:=/root/models/faster-whisper-tiny.en \
  microphone_device:=-1 \
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

## Flow 0B: Apartment-Safe QR, Backend, and Approach

Keep `stationary_orchestrator.launch.py` running throughout these phases.
Never echo or record `/vision/qr/detections`, because it contains the complete
decoded QR payload.

### Phase A4 — Real QR Camera and Decoder

Confirm the camera topic before launch:

```bash
ros2 topic info /camera/color/image_raw
```

Start only QR perception; obstacle and object detection stay disabled:

```bash
ros2 launch evo_vision vision.launch.py \
  camera_topic:=/camera/color/image_raw \
  enable_qr:=true \
  enable_depth_obstacles:=false \
  enable_object_detection:=false \
  qr_decoder_backend:=auto \
  qr_cooldown_sec:=2.0 \
  qr_min_scan_interval_sec:=0.25 \
  qr_max_width:=640
```

Observe decoder health without exposing QR contents:

```bash
ros2 topic echo /vision/qr/status
```

Start reservation validation in mock mode:

```bash
ros2 launch evo_reception reception.launch.py \
  mock_mode:=true \
  mock_outcome:=valid \
  mock_destination_id:=1
```

### Phase A5 — Real Reservation Verification

Use only an approved endpoint and dedicated test reservations:

```bash
export VALIDATION_URL='http://<approved-host>:8000/api/reservations/validate'
ros2 launch evo_reception reception.launch.py \
  mock_mode:=false \
  validation_url:="$VALIDATION_URL" \
  request_timeout_sec:=3.0 \
  duplicate_cooldown_sec:=5.0
```

Observe state only. Do not save output containing reservation details:

```bash
ros2 topic echo /reception/qr/status
ros2 topic echo /reception/dialogue/state
ros2 topic echo /reception/workflow/status
```

Test valid, invalid, expired, duplicate, timeout, malformed, and unavailable
responses with test reservations. Only a valid response with a stable
destination ID may reach `READY_TO_GUIDE`; navigation remains simulated.

### Phase A6 — Real Human-Approach Filtering

The approach filter requires an upstream detector publishing:

```text
/vision/people/detections
evo_reception_interfaces/msg/PersonDetection
```

Check it first:

```bash
ros2 topic info /vision/people/detections
```

If there is no publisher with that message type, Phase A6 is blocked. The
placeholder `object_detector_node` is not a person detector.

When the typed detector is available:

```bash
ros2 launch evo_vision human_approach.launch.py \
  detections_topic:=/vision/people/detections \
  min_confidence:=0.65 \
  min_distance_m:=0.5 \
  max_distance_m:=2.5 \
  zone_min_x:=0.25 \
  zone_max_x:=0.75 \
  zone_min_y:=0.15 \
  zone_max_y:=0.95 \
  debounce_frames:=3 \
  absence_reset_sec:=1.0 \
  cooldown_sec:=10.0
```

Observe without recording identifiable data:

```bash
ros2 topic echo /vision/people/approach
ros2 topic echo /reception/dialogue/state
```

Passing people, repeated frames, and an active dialogue must not create
duplicate approach events. An approach event may start dialogue only; it never
commands navigation.

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
