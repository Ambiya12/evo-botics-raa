# Reception Hardware Checklist

Use this checklist only with the physical robot. Laptop mock acceptance does
not establish hardware readiness.

## Apartment-Safe Session Preflight

Allowed profiles: `robot_safe_base` and `robot_stationary_full`.
`robot_navigation_site` is forbidden in the apartment.

- [ ] Date, operator, location, Git commit, and selected profile are recorded.
- [ ] Robot is stable; power isolation, E-stop, and stack shutdown are reachable.
- [ ] Operator knows how to stop every launched node.
- [ ] `mock_navigation:=true` is explicit in the launch configuration.
- [ ] Selected waypoint registry has `hardware_validated: false`.
- [ ] No real map, waypoint pose, Nav2, or return test is planned.
- [ ] No test will send `/navigate_to_pose` goals or publish velocity commands.
- [ ] Local model and voice files exist; startup requires no downloads.
- [ ] A dated copy of `real_robot_evidence_template.md` is ready.

Any failed item blocks the session.

## Hardware Device Inventory

Record observed identifiers without adding machine-specific paths to repository
configuration.

- [ ] Robot hostname, OS, ROS distribution, and ROS domain ID.
- [ ] Microphone and speaker identities.
- [ ] Camera identity and available color, depth, and camera-info topics.
- [ ] E-stop topic and observed safe state.
- [ ] Base interface identified but unused during apartment reception tests.
- [ ] Backend environment and non-secret validation URL.
- [ ] Local STT model and TTS voice files.

## Movement Lockout

- [ ] Navigation orchestrator reports `mock_navigation=True`.
- [ ] Navigation orchestrator reports `allow_real_navigation=False`.
- [ ] Startup log contains `STATIONARY SAFETY MODE ACTIVE`.
- [ ] Waypoint registry reports `hardware_validated: false`.
- [ ] No Nav2 bringup or real-navigation profile was started.
- [ ] No `/navigate_to_pose` goal occurs during a simulated happy path.
- [ ] No reception-related `/cmd_vel` output occurs.
- [ ] Logs and workflow status clearly identify simulated navigation.

Stop immediately if any item becomes false.

## Stop or Blocker Conditions

- [ ] Unexpected wheel movement, Nav2 goal, or velocity command.
- [ ] E-stop, stack stop, or shutdown cannot be reached or confirmed.
- [ ] Active profile or mock-navigation state is ambiguous.
- [ ] Wrong device, backend, model, or voice is selected.
- [ ] Device disconnect, overheating, repeated uncontrolled action, or loss of
      operator control.
- [ ] Runtime attempts an unapproved download.
- [ ] Logs expose credentials, complete QR data, visitor audio, or identifiable images.

If any condition occurs, stop, record the blocker, and roll back. Do not
continue through intermittent safety faults.

## Rollback to Mock Navigation

- [ ] Stop the reception stack; use the physical E-stop first if motion occurred.
- [ ] Record the profile, last workflow state, symptom, and stop method.
- [ ] Restart only with `mock_navigation:=true`.
- [ ] Confirm `hardware_validated: false`.
- [ ] Restore reservation `mock_mode:=true` if the backend was involved.
- [ ] Restore `mock_audio:=true` if voice hardware was involved.
- [ ] Repeat movement lockout before resuming from the last accepted phase.

## Stationary Hardware Checks

### Microphone

- [ ] Configured device opens without falling back to another device.
- [ ] Microphone index and displayed device name are recorded.
- [ ] Model path, compute device/type, language, VAD threshold, confidence
      threshold, listen timeout, and phrase limit are recorded.
- [ ] Quiet/noisy input does not publish a usable transcript.
- [ ] Visitor speech publishes the expected transcript and confidence.
- [ ] Capture pauses throughout TTS and resumes after terminal TTS status.
- [ ] Temporary capture stays outside the repository and is handled according
      to the session privacy policy.

### Speaker

- [ ] Piper loads its configured local model without downloads.
- [ ] Piper model, player executable, and MPV audio-output device are recorded.
- [ ] Reception phrases are understandable at the intended distance.
- [ ] Queued phrases never overlap.
- [ ] Playback failure publishes `failed` and leaves the workflow safe.

### Duplex Voice, Intent, and Dialogue

- [ ] TTS and STT use the same `/voice/tts/status` topic.
- [ ] STT publishes nothing from robot speech while status is `speaking`.
- [ ] STT resumes after `completed`, `failed`, or `idle`.
- [ ] Supported visitor speech produces one transcript and expected intent.
- [ ] Unknown speech, repeat, cancel, retry, timeout, and reset are observed.
- [ ] Navigation remains mocked throughout the voice session.

### Camera and Human Approach

- [ ] `/vision/people/detections` has a real publisher using
      `evo_reception_interfaces/msg/PersonDetection`; otherwise A6 is blocked.
- [ ] Person detections include confidence, distance, and normalized position.
- [ ] Zone, distance, debounce, absence, and cooldown rules behave as configured.
- [ ] Passing and stationary people do not produce repeated greetings.

### QR and Reservation

- [ ] Camera topic, decoder backend, cooldown, scan interval, and processing
      width are recorded.
- [ ] Camera decodes an approved test QR.
- [ ] Scans outside `WAITING_FOR_QR` do not reach validation.
- [ ] Invalid, expired, duplicate, and unavailable outcomes never request motion.
- [ ] Timeout and malformed responses return unavailable with no destination ID.
- [ ] Real validation starts only with `mock_mode:=false` and an approved
      absolute `validation_url`.
- [ ] Only dedicated test reservations are used.
- [ ] Valid response contains the expected stable destination ID.
- [ ] Valid response produces simulated navigation only.

## Controlled Navigation Site Checklist — Deferred

Do not perform these checks for the first activation task or in the apartment.
They require the Track B go/no-go review.

- [ ] Controlled site, supervisor, safety perimeter, and operator are available.
- [ ] Physical E-stop and manual stop have been tested.
- [ ] Base, sensors, TF, odometry, footprint, and conservative limits are reviewed.
- [ ] Deployment map exists and localization is repeatable.
- [ ] Reception and test waypoint poses are measured and independently reviewed.
- [ ] Deployment registry may be marked `hardware_validated: true` only after review.
- [ ] Nav2 readiness, cancellation, timeout, and blocked-path procedures are approved.
- [ ] Rollback to `robot_stationary_full` is rehearsed.
- [ ] Real guidance is accepted before return-to-reception is attempted.
- [ ] Return-to-reception remains a separate final acceptance phase.
