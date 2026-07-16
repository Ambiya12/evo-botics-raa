# Manual School Demo Launch

This is the manual terminal equivalent of:

```bash
./scripts/robot.sh demo school
```

Use this when the Mac wrapper/SSH multiplexing is unstable. Keep each ROS launch running in its own terminal.

## Mac: Laravel

Run this on the Mac, from the repository:

```bash
cd "/Users/galystan/Documents/HETIC - WEB 3/RAA/evo-botics-raa/reservationApp"
./vendor/bin/sail up -d
curl http://10.10.220.25:8000/
```

## Jetson: Common ROS Setup

For every Jetson ROS terminal:

```bash
ssh jetson@10.10.221.241
docker exec -it evo-ros bash
```

Then paste:

```bash
source /opt/ros/humble/setup.bash
source /root/yahboomcar_ws/install/setup.bash 2>/dev/null || true
source /root/M3Pro_ws/install/setup.bash 2>/dev/null || true
source /root/evo_ws/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=30
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

## Terminal 1: Bringup

```bash
ros2 launch slam_mapping bringup.launch.py
```

## Terminal 2: Camera

```bash
ros2 launch slam_mapping app_camera.launch.py
```

Verify real publishers, not only topic names:

```bash
ros2 topic info /camera/color/image_raw -v
ros2 topic info /camera/depth/image_raw -v
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_raw
```

Both color and depth should show `Publisher count: 1`.

## Terminal 3: Voice

```bash
ros2 launch evo_voice reception_voice.launch.py \
  stt_device:=cpu \
  stt_compute_type:=int8 \
  language:=en \
  microphone_device:=12 \
  phrase_time_limit_sec:=5.0 \
  pause_threshold_sec:=0.4 \
  non_speaking_duration_sec:=0.2 \
  piper_model_path:=/root/evo-models/piper/en_US-lessac-medium.onnx \
  stt_model_path:=/root/evo-models/whisper/tiny.en \
  audio_output_device:=pulse/alsa_output.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.analog-stereo
```

## Terminal 4: Web Dashboard

```bash
ros2 launch evo_web web_dashboard.launch.py \
  rosbridge:=true \
  rosbridge_port:=9090 \
  http_port:=8080 \
  camera_topic:=/camera/color/image_raw \
  camera_max_fps:=8.0 \
  camera_max_width:=640 \
  camera_jpeg_quality:=60
```

## Terminal 5: Vision

```bash
ros2 launch evo_vision vision.launch.py \
  camera_topic:=/camera/color/image_raw \
  depth_topic:=/camera/depth/image_raw \
  qr_decoder_backend:=auto \
  enable_object_detection:=true \
  person_model_path:=/root/models/person_detector.onnx \
  person_confidence_threshold:=0.35 \
  person_nms_threshold:=0.45 \
  person_max_fps:=5.0
```

Verify detector health:

```bash
ros2 topic echo /vision/people/detector_status --once
ros2 topic echo /vision/people/health --once
```

Healthy examples include `state: active` or `state: detecting`, with `model_loaded: true` and `depth_sync_ok: true`.

## Terminal 6: Navigation

Use either real navigation or mock navigation.

### Option A: Real Navigation

```bash
ros2 launch evo_navigation navigation.launch.py \
  map:=/root/evo_ws/src/evo_navigation/maps/school_v1.yaml \
  rviz:=false \
  use_collision_monitor:=false
```

After Nav2 is running, set the robot initial pose from RViz/dashboard, or publish the known reception pose if the robot is physically at reception.

Check AMCL:

```bash
ros2 topic echo /amcl_pose --once
```

The pose should be in frame `map` with small covariance before starting `reception_nav`.

### Option B: Mock Navigation

Use this mode to test the complete reception workflow without AMCL, initial pose, or real robot movement.

After rebuilding/deploying the workspace that contains `mock_guide_action_server`, run:

```bash
ros2 run evo_reception mock_guide_action_server \
  --ros-args \
  -p action_name:=/reception/guide_to_destination \
  -p travel_time_sec:=3.0 \
  -p return_time_sec:=3.0
```

In mock mode, do not start Nav2 or `reception_nav`.

## Terminal 7: Reception Navigation

Start this only for real navigation, after Nav2 and AMCL are ready:

```bash
ros2 launch evo_navigation orchestrator.launch.py \
  waypoint_config_path:=/root/evo_ws/install/evo_navigation/share/evo_navigation/config/school_reception_waypoints.yaml \
  allow_real_navigation:=true \
  navigation_timeout_sec:=120.0 \
  localization_timeout_sec:=0.0 \
  max_localization_xy_variance:=0.5
```

## Terminal 8: Reception Bridge

```bash
ros2 launch evo_reception reception.launch.py \
  validation_url:=http://10.10.220.25:8000/api/reservations/validate
```

## Terminal 9: Dialogue

For real navigation without automatic return:

```bash
ros2 launch evo_reception dialogue_manager.launch.py \
  presence_greeting_fallback_sec:=5.0 \
  intent_timeout_sec:=45.0 \
  qr_inactivity_timeout_sec:=20.0 \
  allowed_destination_ids_csv:=1,2 \
  automatic_return_enabled:=false
```

For mock navigation or supervised real return-to-reception testing:

```bash
ros2 launch evo_reception dialogue_manager.launch.py \
  presence_greeting_fallback_sec:=5.0 \
  intent_timeout_sec:=45.0 \
  qr_inactivity_timeout_sec:=20.0 \
  allowed_destination_ids_csv:=1,2 \
  automatic_return_enabled:=true
```

## Optional: Jetson Kiosk

Run this on the Jetson host, not inside Docker:

```bash
DISPLAY=:0 chromium-browser --kiosk --noerrdialogs --disable-infobars http://10.10.220.25:8000/kiosk?scan=robot
```

## Demo Rescue Commands

Run these inside `evo-ros` with the common ROS setup sourced.

Check dialogue state:

```bash
ros2 topic echo /reception/dialogue/state --once
```

When the robot is stuck in `WAITING_FOR_INTENT`, manually publish "yes" as an affirmative intent:

```bash
ros2 topic pub --once /voice/intent/result evo_reception_interfaces/msg/IntentResult \
"{intent: affirmative, confidence: 1.0, source_transcript: 'manual yes'}"
```

To test the voice intent detector path instead of bypassing it, publish a transcript:

```bash
ros2 topic pub --once /voice/stt/transcript evo_reception_interfaces/msg/Transcript \
"{text: 'yes', language: 'en', confidence: 1.0}"
```

Useful alternatives:

```bash
ros2 topic pub --once /voice/intent/result evo_reception_interfaces/msg/IntentResult \
"{intent: negative, confidence: 1.0, source_transcript: 'manual no'}"

ros2 topic pub --once /voice/intent/result evo_reception_interfaces/msg/IntentResult \
"{intent: repeat, confidence: 1.0, source_transcript: 'manual repeat'}"

ros2 topic pub --once /voice/intent/result evo_reception_interfaces/msg/IntentResult \
"{intent: cancel, confidence: 1.0, source_transcript: 'manual cancel'}"
```

To force visitor presence during a workflow rehearsal:

```bash
ros2 topic pub --once /vision/people/presence std_msgs/msg/Bool "{data: true}"
```

To simulate a QR scanner event, publish a payload to the QR topic. The payload still has to be accepted by the reception validation service:

```bash
ros2 topic pub --once /vision/qr/detections std_msgs/msg/String \
"{data: 'PASTE_VALID_QR_PAYLOAD_HERE'}"
```

## Stop Manual Demo

Press `Ctrl-C` in each launch terminal. If a ROS node is stuck, exit the container terminal and stop the relevant process from the Jetson host.
