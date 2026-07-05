# Real Robot Activation Plan

## Purpose

Activate the implemented EVO reception workflow on the physical robot in
small, evidence-based steps. The first track validates real hardware while the
base remains stationary. A later track validates mapping and movement in a
controlled site with sufficient space.

This plan follows Milestones 0-10 in `voice_reception_plan.md`; it is a
hardware acceptance plan, not an additional feature milestone. Complete one
phase before starting the next. If a phase fails, record the blocker and
return to the last accepted configuration.

## Scope Boundary

### Allowed now in the apartment

- Robot computer startup and shutdown
- Real speaker and TTS
- Real microphone, VAD, and STT
- Deterministic intent detection and dialogue transitions
- Real QR camera and decoding
- Reservation verification against an approved backend
- Human-approach detection when it can be tested without base movement
- Workflow status and dashboard observation
- Complete stationary reception flow with mock navigation
- Restart, offline, timeout, and recovery checks that do not move the robot

### Deferred to a controlled navigation site

- Creating or approving the deployed map
- Measuring real room and reception waypoint poses
- Setting waypoint `hardware_validated: true`
- Running Nav2 with `mock_navigation:=false`
- Sending real `NavigateToPose` goals
- Obstacle avoidance and blocked-route trials
- Real visitor guidance and return-to-reception movement

## Non-Negotiable Safety Invariants

1. Apartment tests use `mock_navigation:=true`.
2. `reception_waypoints.yaml` remains `hardware_validated: false`.
3. No apartment acceptance step requires `/cmd_vel` output.
4. A valid QR may produce a destination ID and a simulated navigation result,
   but must not produce a real Nav2 goal.
5. The operator keeps the E-stop and shutdown method within reach.
6. Stop immediately on unexpected motion, an unexpected Nav2 goal, repeated
   uncontrolled speech/actions, sensor overheating or disconnect, loss of
   network control, or inability to stop a node.
7. Never bypass the orchestrator's E-stop, localization, Nav2-readiness, or
   waypoint-validation gates.
8. Do not use a production reservation backend unless test data and
   authorization are explicit. Avoid retaining visitor audio, images, or QR
   payloads in test evidence.

## Activation Profiles

Use separate saved ROS parameter/launch profiles rather than remembering
command-line flags. Profile files may be added during implementation after the
robot's real device names, model paths, and topics are known.

| Profile | Required safety values | Intended use | Permitted location |
| --- | --- | --- | --- |
| `laptop_mock` | `mock_audio:=true`, reservation `mock_mode:=true`, `mock_navigation:=true`, `hardware_validated: false` | Hardware-free mocks, fixtures, or replay | MacBook |
| `robot_safe_base` | `mock_navigation:=true`, `hardware_validated: false`; activate at most the subsystem under test | Preflight and one-real-subsystem-at-a-time checks | Apartment or controlled site |
| `robot_stationary_full` | Real voice/vision; reservation `mock_mode:=false` only for an approved backend; `mock_navigation:=true`, `hardware_validated: false` | Full physical workflow with simulated navigation | Apartment or controlled site |
| `robot_navigation_site` | Navigation values deliberately undefined until Track B review | Future real map, waypoint, Nav2, and return testing | Controlled navigation site only; forbidden in the apartment |

The repository's current controls use `mock_audio` for voice,
`mock_mode` for QR reservation validation, and `mock_navigation` for the
navigation orchestrator. Do not invent a single `real_mode` flag: independent
switches make staged activation and rollback safer.

These names currently define configuration contracts, not executable launch
files. Create robot-specific profiles only after device identities and local
model paths are inventoried. Every future apartment profile must set
`mock_navigation:=true` explicitly rather than relying only on a default.

Both apartment profiles must include
`evo_navigation/launch/stationary_orchestrator.launch.py`. That launcher does
not expose either navigation safety key: it forces `mock_navigation:=true` and
`allow_real_navigation:=false`. The general `orchestrator.launch.py` also
defaults to those values, but real mode requires both values to be explicitly
reversed and a waypoint registry with `hardware_validated: true`.

## Evidence Record

Copy `real_robot_evidence_template.md` for each physical-robot session. Record:

- Git commit, robot hostname, ROS domain ID, operator, location, and time
- Launch commands/profile and non-secret parameter values
- Connected microphone, speaker, camera, and base device identities
- Backend environment (mock, local, staging, or approved production)
- Checks attempted with pass, fail, or deferred
- Relevant topic/action observations and short redacted log excerpts
- Any tuning change, blocker, stop event, and rollback performed
- Explicit statement that the base did or did not move

Keep secrets, full QR values, identifiable images, and raw visitor audio out of
the repository.

## Track A: Stationary Robot Acceptance

### Phase A0: Session preflight and movement lockout

Goal: prove that the robot can be operated safely before enabling reception
hardware.

Actions:

1. Place the robot in a stable position with clear access to power and E-stop.
2. Identify the correct workspace, commit, ROS environment, and connected
   devices.
3. Confirm local model/voice files exist and startup needs no downloads.
4. Confirm the selected waypoint registry still has
   `hardware_validated: false`.
5. Start only the navigation orchestrator in mock mode and verify its startup
   log reports `mock_navigation=True`.
6. Observe that no `/navigate_to_pose` goal and no base velocity is emitted
   during a simulated navigation completion.
7. Exercise the operator's node-stop, stack-stop, and robot shutdown methods.

Acceptance:

- Device inventory and configuration are recorded.
- Mock navigation is visibly active.
- No movement or physical navigation goal occurs.
- E-stop and shutdown methods are understood and reachable.

Stop/blocker examples: unexpected wheel motion, missing E-stop, ambiguous
device identity, runtime download, or no reliable shutdown method.

### Phase A1: Real speaker and TTS

Goal: validate speech output without opening the microphone.

Configuration:

- Real TTS playback with a local Piper voice
- Launch `reception_voice.launch.py` with `tts_mock_audio:=false` and
  `stt_mock_audio:=true`
- Set `piper_model_path` and, when the system default is wrong,
  `audio_output_device`; do not commit robot-specific values
- QR/backend mocked or disabled
- Navigation mocked

Checks:

1. Play welcome, clarification, QR request, success, arrival, and failure
   phrases one at a time.
2. Queue multiple phrases and confirm ordering without overlap.
3. Confirm `idle`, `speaking`, `completed`, and a deliberately induced
   `failed` status.
4. Tune volume at the intended visitor distance without clipping.

Acceptance:

- Every required phrase is understandable.
- Requests do not overlap and statuses match playback.
- Playback failure leaves the workflow stationary and recoverable.

### Phase A2: Real microphone, VAD, and STT

Goal: validate capture and transcription independently from workflow actions.

Configuration:

- Launch `reception_voice.launch.py` with `tts_mock_audio:=true` and
  `stt_mock_audio:=false`
- Set the local `stt_model_path`, `microphone_device`, language, compute type,
  VAD threshold, confidence threshold, and capture timeouts explicitly
- Intent/dialogue observed but not allowed to trigger QR or movement if
  isolation is needed
- Navigation mocked

Checks:

1. Record quiet-room baseline, normal speech, silence, and ordinary apartment
   noise at representative distances.
2. Try the supported English phrases plus unsupported speech.
3. Confirm silence/noise does not publish a usable transcript.
4. Record recognition result and latency without storing raw visitor audio.
5. Restart STT and confirm capture resumes on the configured device.

Acceptance:

- Supported phrases yield usable transcripts at the chosen distance.
- Empty/noisy input is ignored within documented thresholds.
- Device selection and restart behavior are repeatable.
- Robot acoustic measurements are recorded separately from mock results.

### Phase A3: Duplex voice, intent, and dialogue

Goal: prove that the robot does not transcribe itself and that real transcripts
drive deterministic dialogue correctly.

Checks:

1. Start `reception_voice.launch.py` with both mock switches set to `false`.
2. Verify capture pauses for `speaking` and resumes for `completed`, `failed`,
   or `idle`.
3. Exercise reservation, check-in, meeting-room, help, repeat, cancel, and
   unknown utterances.
4. Verify retry limit, inactivity timeout, cancellation, and session reset.
5. Run several greet/listen cycles and check for feedback loops.

Acceptance:

- No robot phrase becomes a visitor transcript.
- Expected intents and state transitions are observed.
- Repeat, cancel, retry, timeout, and reset behave predictably.
- No QR or navigation behavior originates directly from STT.

### Phase A4: Real QR camera and decoder

Goal: validate camera transport and QR decoding while reservation validation is
still mocked.

Configuration:

- Real camera and QR scanner
- Reservation bridge `mock_mode:=true`
- Explicit camera topic, decoder backend, duplicate cooldown, scan interval,
  and processing width
- Navigation mocked

Checks:

1. Confirm the configured color topic, frame rate, exposure, and decoder
   backend work at realistic QR distance and angle.
2. Present QR data before `WAITING_FOR_QR`; it must not enter validation.
3. Present valid, invalid, and repeated test QR codes in the correct state.
4. Confirm duplicate cooldown and that camera loss is recoverable.

Acceptance:

- QR detection is reliable within a documented operating envelope.
- Out-of-state and duplicate scans cannot advance the workflow incorrectly.
- Camera failure does not trigger navigation or leave a stuck session.

### Phase A5: Real reservation verification

Goal: validate the robot-to-Laravel path without movement.

Configuration:

- Real QR camera
- Reservation bridge `mock_mode:=false`
- Explicit approved `validation_url`
- Positive request timeout; URLs containing credentials are rejected
- Navigation mocked

Checks:

1. Use dedicated test reservations for valid, invalid, expired, unknown room,
   timeout, malformed response, and backend-unavailable cases.
2. Verify only a valid response returns a stable destination ID.
3. Confirm destination IDs match the application's room-ID convention.
4. Disconnect and restore the backend; verify safe recovery.
5. Confirm logs and dashboard do not expose QR secrets.
6. Exercise timeout and malformed-response handling; both must report
   unavailable with no destination ID.

Acceptance:

- Backend outcomes map to the documented QR results.
- Invalid or unavailable results never request guidance.
- A valid result produces the expected destination ID and only simulated
  navigation.
- Backend loss has a clear spoken/status outcome and leaves the robot safe.

### Phase A6: Real human-approach detection

Goal: tune visitor triggering with the physical camera while the robot remains
stationary.

Checks:

1. Confirm an upstream node publishes typed `PersonDetection` messages; the
   existing object-detector scaffold does not provide them.
2. Confirm detection messages contain confidence, distance, and position.
3. Test outside/inside reception zone, passing by, approaching, standing,
   remaining in view, leaving, and returning after cooldown.
4. Tune distance, confidence, debounce, absence, and cooldown parameters.
5. Repeat under the available lighting conditions.

Acceptance:

- A deliberate visitor approach creates one greeting per session.
- Passing people and repeated frames do not repeatedly greet.
- A later visitor can start a new session after absence/cooldown.
- Known apartment limitations and false positives are recorded.

### Phase A7: Full stationary reception workflow

Goal: accept all currently testable real components together.

Configuration:

- Real TTS, microphone/STT, intent/dialogue, camera/QR, backend, and human
  approach
- Navigation orchestrator `mock_navigation:=true`
- Waypoint registry `hardware_validated: false`

Run at least these scenarios:

1. Happy path: approach, reservation question, affirmative answer, QR request, valid QR,
   backend success, destination ID, simulated arrival, session reset.
2. Unknown intent until retry limit.
3. Cancel during dialogue.
4. Invalid and expired QR.
5. Backend timeout or disconnection.
6. Camera or STT restart during an idle session.
7. Duplicate approach and duplicate QR events.

Acceptance:

- The happy path completes repeatedly without physical movement.
- Major failure paths recover to a safe state.
- Workflow/dashboard status clearly identifies simulated navigation.
- No `/navigate_to_pose` goal or reception-related base velocity is emitted.
- Restart/offline results and measured robot latency/recognition values are
  recorded in `reception_reliability.md` or a linked dated record.

Completion of A7 means the stationary hardware workflow is accepted. It does
not accept mapping, Nav2, guidance, or return-to-reception behavior.

## Gate Between Tracks

Do not start Track B until all Track A acceptance checks pass or have explicit
blockers, and a suitable site and supervisor are available. Hold a go/no-go
review covering:

- Physical E-stop tested and operator manual stop rehearsed
- Base, lidar/depth sensors, TF, odometry, and battery healthy
- Low initial velocity/acceleration limits reviewed
- Clear test perimeter and no uninvolved people
- Map ownership, waypoint measurement method, and rollback plan agreed
- Logs/rosbag plan with privacy and disk-space limits
- `robot_stationary_full` can be restored quickly

Any missing safety item is a no-go.

## Track B: Controlled-Site Navigation Acceptance

### Phase B0: Base and safety commissioning

Goal: validate the physical base independently from reception automation.

Verify E-stop state propagation, manual stop, commanded velocity direction,
odometry, TF, sensors, footprint, costmaps, and conservative speed limits.
Begin with wheels raised if mechanically safe, then use a cordoned low-speed
floor test. Do not involve QR or dialogue yet.

Acceptance: commanded and observed motion agree; stopping is immediate and
repeatable; TF and sensor data are stable; the operator can abort every test.

### Phase B1: Real map and localization

Goal: create or select the deployment map and prove repeatable localization.

Save the map as a versioned deployment asset, document its physical origin and
frame, launch AMCL/Nav2 against it, set the initial pose, and test recovery
after relaunch and modest displacement.

Acceptance: map scale/orientation are correct; localization is stable at
reception and along the test route; costmaps represent real obstacles; the
tested map version is recorded.

### Phase B2: Real waypoint registry

Goal: measure reception and one nearby test destination against the accepted
map.

Record each pose and yaw using localization, independently review room-ID
mapping, validate clearances, and first test plans without executing movement.
Only after this review may the deployment copy set
`hardware_validated: true`.

Acceptance: reception and test destination resolve to reviewed poses in the
correct frame; unknown rooms fail; a path can be planned; the exact registry
version is recorded.

### Phase B3: Single Nav2 goal

Goal: validate one short, supervised movement outside the reception workflow.

Use `mock_navigation:=false`, conservative limits, one nearby waypoint, and an
operator at the E-stop. Test success first, then cancellation and timeout.
Do not test deliberate dynamic obstruction until normal stopping is proven.

Acceptance: Nav2 readiness gates work; the robot reaches within the agreed
tolerance; cancel/timeout stop motion; status maps correctly to accepted,
active, arrived, cancelled, timeout, or failed.

### Phase B4: Verified reception-to-destination guidance

Goal: allow the full workflow to request exactly one real destination only
after valid QR verification.

Start with a dedicated QR for the accepted nearby waypoint. Confirm invalid,
expired, unknown-room, localization-not-ready, Nav2-not-ready, and E-stop cases
all reject without movement before running the valid case.

Acceptance: only a verified QR can start movement; the spoken and workflow
statuses match the Nav2 result; failure and cancellation leave the robot
stopped and do not automatically retry.

### Phase B5: Return to reception

Goal: validate return as a separately observable navigation leg.

After successful arrival, confirm arrival speech, configured wait, explicit
return request to the reviewed `reception` waypoint, navigation status, and
final reset. Test return failure/cancellation without automatic repeated
movement.

Acceptance: successful return reaches reception and resets to `IDLE`; a failed
return stops, publishes failure, and requires operator recovery; no new visitor
session starts while returning.

### Phase B6: Deployment rehearsal

Goal: validate repeated end-to-end operation under supervised site conditions.

Run multiple happy paths and representative failures, include real obstacles
only under an approved safety script, measure recognition/navigation latency,
restart nodes, and restore the stationary profile as a rollback drill.

Acceptance: the agreed repetition and reliability targets are met; all
remaining risks are documented; the exact map, waypoint, parameter, and
software versions are frozen for deployment.

## Rollback Strategy

At any failure:

1. Stop the active action/node and physically stop the robot if movement is
   possible.
2. Record the symptom, active profile, and last known state.
3. Restore `mock_navigation:=true`.
4. Restore `hardware_validated: false` for any unapproved waypoint registry.
5. Re-run the preceding accepted phase only after the cause and safe retry
   condition are documented.

Do not “test through” intermittent safety faults.

## Commands to Run Manually

These are templates; substitute robot-specific model paths, devices, topics,
and URLs from a non-secret parameter file. Run them only for the phase that is
currently authorized.

### Deploy after every ROS package change

```bash
./scripts/robot.sh setup
```

This deploys `evo_ws/src` to the Jetson, copies it into `/root/evo_ws` in the
robot container, and builds it there. Do not repeat those steps manually.

Then connect and enter the ROS container:

```bash
ssh jetson@192.168.1.9
docker ps
docker exec -it <robot-container> bash
source /opt/ros/humble/setup.bash
source /root/evo_ws/install/setup.bash
export ROS_DOMAIN_ID=30
```

Start the safe navigation orchestrator:

```bash
ros2 launch evo_navigation stationary_orchestrator.launch.py
```

Inspect the safety-relevant configuration and interfaces:

```bash
ros2 param get /navigation_orchestrator_node mock_navigation
ros2 param get /navigation_orchestrator_node allow_real_navigation
ros2 topic echo /reception/navigation/status
ros2 action list
ros2 topic info /cmd_vel
```

Do not use `./scripts/robot.sh launch`, `start navigate`, or `nav` in the
apartment; those existing commands start the real Nav2 stack.

Quick rollback from another robot mode:

```bash
./scripts/robot.sh stop all
./scripts/robot.sh start stationary
./scripts/robot.sh safety
```

Package tests, kept separate from physical acceptance:

```bash
cd evo_ws
colcon test --packages-select evo_reception_interfaces evo_voice evo_reception evo_vision evo_navigation
colcon test-result --verbose
```

Do not provide or run a real-navigation command until Track B's go/no-go gate
passes and the deployment map and waypoint files are reviewed.

## Later Work, Not Implemented by This Plan

- Robot-specific launch profiles after device names and installed paths are
  observed
- Real deployment map and measured waypoint values
- Site-specific Nav2 tuning, footprint, speed, and costmap changes
- Any fixes revealed by physical testing
- Production operating procedure and operator training
