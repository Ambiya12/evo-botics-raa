# Voice Reception Contracts

Milestone 0 freezes the reception workflow contracts. This document describes
the repository as audited on 2026-06-29 and the interfaces required by later
milestones. It does not add runtime behavior or dependencies.

## Ownership and package structure

| Package | Existing responsibility | Reception responsibility |
| --- | --- | --- |
| `evo_voice` | One blocking node combines microphone capture, STT, translation, Piper playback, and publication of translated text. | Later split into STT, deterministic intent detection, and queued TTS. STT publishes transcripts only; TTS owns playback and speaking status. |
| `evo_reception` | QR payload validation bridge and JSON status publication. | Own the dialogue manager and conversation state. Coordinate typed voice, QR, and navigation contracts. |
| `evo_vision` | QR decoding, depth obstacle point cloud, and an object-detection scaffold. | Publish QR detections. Later publish debounced approach events; do not own dialogue state. |
| `evo_navigation` | Nav2 launch/configuration, goal validation, velocity routing, collision monitoring, and emergency-stop gating. | Later map a verified destination ID to a configured waypoint and invoke Nav2. Never derive coordinates from speech. |

No custom ROS interface package currently exists in the audited packages. A
later milestone should add one shared interface package (proposed name:
`evo_reception_interfaces`) rather than creating cross-package dependencies on
implementation packages.

## Existing interface inventory

Directions are relative to the named node. Unless stated otherwise, the code
uses queue depth 10 and default reliable/volatile QoS.

| Package / node | Kind | Name and ROS type | Direction | Current payload or purpose | Reception decision |
| --- | --- | --- | --- | --- | --- |
| `evo_voice/translator_node` | Topic | `/voice/translation` — `std_msgs/msg/String` | Publish | Translated text after the node has listened, translated, and spoken. | Do not use as the reception transcript contract. It loses source text, language, confidence, and timestamp and couples STT to translation/TTS. |
| `evo_vision/qr_scanner_node` | Topic | Camera parameter, default `/camera/color/image_raw` — `sensor_msgs/msg/Image` | Subscribe | Color frames, sensor-data QoS (best effort, depth 1). | Reuse camera input. |
| `evo_vision/qr_scanner_node` | Topic | `/vision/qr/detections` — `std_msgs/msg/String` | Publish | JSON containing `decoded_text`, image stamp, camera topic, decoder backend, JSON metadata, and UUID presence. | Temporarily compatible with the bridge; replace with a typed QR detection event before workflow integration. |
| `evo_vision/qr_scanner_node` | Topic | `/vision/qr/status` — `std_msgs/msg/String` | Publish | JSON health counters every two seconds. | Keep as diagnostics only; it is not a workflow event. A diagnostic message or `/diagnostics` migration is optional later work. |
| `evo_vision/depth_obstacle_scan_node` | Topic | `/camera/depth/image_raw` — `sensor_msgs/msg/Image` | Subscribe | Depth frames, sensor-data QoS. | Reuse for navigation safety; not a dialogue input. |
| `evo_vision/depth_obstacle_scan_node` | Topic | `/camera/depth/camera_info` — `sensor_msgs/msg/CameraInfo` | Subscribe | Camera intrinsics, sensor-data QoS. | Reuse. |
| `evo_vision/depth_obstacle_scan_node` | Topic | `/vision/obstacles/points` — `sensor_msgs/msg/PointCloud2` | Publish | Calibrated obstacle points in the camera optical frame. | Reuse through the Nav2 costmap. |
| `evo_vision/object_detector_node` | Topic | `/vision/objects/detections` — `std_msgs/msg/String` | Publish | JSON scaffold status with an always-empty detection array. | Cannot be reused for approach detection; it has no model behavior or person event contract. |
| `evo_reception/qr_reservation_bridge_node` | Topic | `/vision/qr/detections` — `std_msgs/msg/String` | Subscribe | Accepts scanner JSON or a non-empty raw string when legacy topic mode is explicitly enabled. | Retained as a migration adapter and disabled by default. |
| `evo_reception/qr_reservation_bridge_node` | Service | `/reception/qr/validate` — `evo_reception_interfaces/srv/ValidateQr` | Server | Validates one correlated QR request and returns a typed outcome plus stable destination ID. | Reused by the dialogue manager only while waiting for QR. |
| `evo_reception/qr_reservation_bridge_node` | Topic | `/reception/qr/status` — `std_msgs/msg/String` | Publish | JSON states `waiting`, `scanned`, `validating`, `success`, or `error`; optional reservation and error code. | Existing business/API adapter is reusable, but topic JSON is not the final workflow contract. Expose validation as a typed service later. |
| `evo_navigation/navigation_goal_validator` | Topic | `/evo/navigation/goal_request` — `geometry_msgs/msg/PoseStamped` | Subscribe | Candidate coordinate goal. | Reuse inside the navigation orchestrator only, after destination-to-waypoint lookup. |
| `evo_navigation/navigation_goal_validator` | Topic | `/map`, `/global_costmap/costmap` — `nav_msgs/msg/OccupancyGrid` | Subscribe | Map and costmap used to reject unsafe goals. | Reuse. |
| `evo_navigation/navigation_goal_validator` | Action | `/compute_path_to_pose` — `nav2_msgs/action/ComputePathToPose` | Client | Checks that Nav2 can plan to the candidate goal. | Reuse. |
| `evo_navigation/navigation_goal_validator` | Topic | `/goal_pose_validated` — `geometry_msgs/msg/PoseStamped` | Publish | Goal accepted after transform, map, clearance, and path checks. | Reuse as the existing validated-goal bridge, but completion must be observed through the Nav2 action. |
| `evo_navigation/navigation_goal_validator` | Topic | `/evo/navigation/goal_status` — `std_msgs/msg/String` | Publish | `planning`, `accepted`, and `rejected_*` codes. | Reuse only as validator telemetry. It does not report navigation progress or arrival and should become typed if consumed as workflow data. |
| Nav2 `bt_navigator` | Action | `/navigate_to_pose` — `nav2_msgs/action/NavigateToPose` | Server | Long-running navigation with goal acceptance, feedback, result, and cancellation. | Reuse as the navigation orchestrator's downstream action. |
| `evo_navigation/cmd_vel_safety_gate` | Topics | `/cmd_vel_nav`, `/cmd_vel_teleop`, output `/cmd_vel_selected` — `geometry_msgs/msg/Twist` | Subscribe / publish | Routes motion commands unless emergency stop is latched. | Reuse. |
| `evo_navigation/cmd_vel_safety_gate` | Topics | `/e_stop`, `/e_stop_reset`, `/e_stop_active` — `std_msgs/msg/Bool` | Subscribe / subscribe / publish | Latched emergency stop, explicit reset, and transient-local reliable status. | Reuse and gate every reception navigation request on `/e_stop_active == false`. |
| `evo_navigation/cmd_vel_output_relay` | Topics | `/cmd_vel_safe` (or configured fallback) to `/cmd_vel` — `geometry_msgs/msg/Twist` | Subscribe / publish | Final velocity relay with a 0.5 s watchdog by default. | Reuse. |

### Existing launch surfaces

| Launch file | Current surface | Audit finding |
| --- | --- | --- |
| `evo_voice/launch/voice.launch.py` | `model_size`, `device`, and `language`; starts `translator_node`. | Arguments are passed as ROS parameters, but the node does not declare or read them. It still uses module constants. |
| `evo_reception/launch/reception.launch.py` | Validation URL, QR/status topics, HTTP timeout, duplicate cooldown, and simulated time. | Reusable launch point for the existing bridge; there is no dialogue manager or enable/disable validation contract. |
| `evo_vision/launch/vision.launch.py` | Color/depth topics, node enable flags, QR backend, and simulated time. | Reusable. Object detection is disabled and scaffold-only. |
| `evo_navigation/launch/navigation.launch.py` | Saved map plus goal-policy and safety options. | Provides localization, Nav2, goal validation, and safety, but no room registry or reception orchestrator. |
| `evo_navigation/launch/slam_and_nav.launch.py` | Online SLAM plus the same navigation/safety pipeline. | Same reception limitation as saved-map navigation. |
| `evo_navigation/launch/explore.launch.py` | Exploration plus goal validation and safety. | Not a reception guidance mode. |
| `evo_navigation/launch/slam_online.launch.py` | SLAM and velocity safety without the full navigation servers. | Cannot guide a visitor by itself. |

## Frozen workflow vocabulary

### Dialogue states

| State | Meaning | Allowed owner activity |
| --- | --- | --- |
| `IDLE` | No active visitor session. | Wait for a debounced approach event. QR and transcript events do not advance the workflow. |
| `PRESENCE_ARMED` | A visitor is present in the reception zone. | Accept only a greeting intent, disarm on absence, or use the configured proactive fallback. |
| `GREETING` | Greeting has been queued or is being spoken. | Wait for TTS completion; listening remains paused while TTS is active. |
| `WAITING_FOR_INTENT` | Greeting/clarification finished and visitor input is accepted. | Accept structured intent results and enforce inactivity/retry limits. |
| `WAITING_FOR_QR` | A supported reception intent was accepted and a QR prompt completed. | Accept a QR detection for validation. |
| `VERIFYING_QR` | Exactly one QR validation request is in progress. | Wait for a typed validation response or timeout; do not request navigation. |
| `READY_TO_GUIDE` | QR validation produced a stable destination ID. | Announce guidance and submit that ID to the navigation orchestrator. |
| `NAVIGATING` | A navigation goal was accepted and is active. | Track action feedback/result and allow cancellation or emergency-stop handling. |
| `ARRIVED` | Nav2 reported success at the visitor destination. | Announce arrival, then request the configured return-to-reception waypoint. |
| `ERROR` | A terminal or retryable operation failed and a safe outcome is being announced. | Never initiate motion; cancel active navigation when applicable, then retry an explicitly allowed step or reset. |

### Supported intents

| Intent | Meaning | Workflow effect |
| --- | --- | --- |
| `greeting` | A present visitor says “Hi”, “Hello”, or addresses Evo. | Starts the greeting only from `PRESENCE_ARMED`; ignored from `IDLE`. |
| `affirmative` | Visitor answers yes to the reservation question. | Prompt for QR, then enter `WAITING_FOR_QR`. |
| `negative` | Visitor answers no to the reservation question. | Speak the configured no-reservation response and reset to `IDLE` without QR or navigation. |
| `reservation` | Visitor says “reservation” or “booking” instead of yes. | Treat as an affirmative fallback and prompt for QR. |
| `repeat` | Visitor asks to hear the current prompt again. | Replay the prompt for the current waiting state without changing the state. |
| `cancel` | Visitor declines or ends the interaction. | Cancel active work if any, acknowledge, and reset to `IDLE`. |
| `unknown` | No deterministic supported intent matched. | Clarify and retry up to the configured limit; then announce failure and reset. |

Intent detection must be deterministic. An intent result contains the normalized
classification plus the original transcript; it has no QR, TTS, or navigation
side effects.

### Events, timeouts, and failure outcomes

| Event / timeout | Valid state(s) | Outcome |
| --- | --- | --- |
| `visitor_approached` | `IDLE` | Enter `PRESENCE_ARMED` without speaking. Debounce/cooldown prevents duplicate sessions. |
| `visitor_left` | `PRESENCE_ARMED` | Disarm and return to `IDLE` without speech. |
| `greeting` intent | `PRESENCE_ARMED` | Enter `GREETING` and queue the welcome phrase. |
| `presence_greeting_timeout` | `PRESENCE_ARMED` | Queue the proactive welcome only if presence remains active. |
| `tts_completed` | `GREETING`, prompt/announcement phases | Enter the state associated with that prompt (`WAITING_FOR_INTENT`, `WAITING_FOR_QR`, navigation submission, or session reset). |
| `tts_failed` / `tts_timeout` | Any active speaking phase | Enter `ERROR`; record `TTS_FAILED`; reset without motion if the required safety/instruction prompt cannot be delivered. |
| `intent_detected` | `WAITING_FOR_INTENT` | Apply the intent table. Stale or out-of-state results are ignored and logged. |
| `intent_inactivity_timeout` | `WAITING_FOR_INTENT` | Clarify up to the retry limit, then `ERROR` with `INTENT_TIMEOUT` and reset. |
| `qr_detected` | `WAITING_FOR_QR` | Enter `VERIFYING_QR` and issue one validation request. Out-of-state detections never authorize navigation. |
| `qr_inactivity_timeout` | `WAITING_FOR_QR` | Repeat the QR prompt up to the retry limit, then `ERROR` with `QR_TIMEOUT` and reset. |
| `qr_valid` | `VERIFYING_QR` | Require a non-empty stable destination ID, then enter `READY_TO_GUIDE`. |
| `qr_invalid` | `VERIFYING_QR` | Announce `INVALID_QR`; return to `WAITING_FOR_QR` if retries remain, otherwise reset through `ERROR`. |
| `qr_expired` | `VERIFYING_QR` | Announce `EXPIRED_QR`; reset through `ERROR`. |
| `qr_duplicate` | `WAITING_FOR_QR`, `VERIFYING_QR` | Ignore while the same request is active/cooling down; it never creates a second validation or navigation request. |
| `qr_service_unavailable` / `qr_validation_timeout` | `VERIFYING_QR` | `ERROR` with `VALIDATION_UNAVAILABLE`; announce safe failure and reset. |
| `guide_goal_accepted` | `READY_TO_GUIDE` | Enter `NAVIGATING`. |
| `guide_goal_rejected` | `READY_TO_GUIDE` | `ERROR` with one of `UNKNOWN_DESTINATION`, `NAV_NOT_READY`, `LOCALIZATION_UNAVAILABLE`, `ESTOP_ACTIVE`, or `GOAL_REJECTED`; no movement. |
| `navigation_succeeded` | `NAVIGATING` | Enter `ARRIVED`, announce arrival, then request return to reception. |
| `navigation_cancelled` | `NAVIGATING` | Stop safely, announce cancellation when possible, then reset. |
| `navigation_aborted` / `navigation_timeout` | `NAVIGATING` | Cancel/stop safely, enter `ERROR` with `NAVIGATION_FAILED` or `NAVIGATION_TIMEOUT`, then reset. |
| `estop_activated` | `READY_TO_GUIDE`, `NAVIGATING` | Reject or cancel navigation immediately, enter `ERROR` with `ESTOP_ACTIVE`, and require external reset before later movement. |
| `session_timeout` | Any non-terminal active state | Cancel outstanding service/action work, announce timeout when possible, and reset to `IDLE`. |

All durations and retry limits must be ROS parameters loaded from YAML. The
contract intentionally does not freeze numeric values before hardware latency
and reception UX are measured. Timeouts use a monotonic/steady clock for local
deadlines; message stamps remain ROS time.

## State-transition table

`ERROR -> IDLE` includes the configured error announcement when TTS is
available. Any event not listed for a state is invalid, has no state-changing
effect, and should be logged at a throttled rate.

| Current state | Trigger / guard | Next state | Required effect |
| --- | --- | --- | --- |
| `IDLE` | Debounced `visitor_approached` | `PRESENCE_ARMED` | Create an armed session without speaking. |
| `PRESENCE_ARMED` | `greeting` | `GREETING` | Queue the welcome phrase while presence is active. |
| `PRESENCE_ARMED` | Presence lost | `IDLE` | Disarm silently. |
| `PRESENCE_ARMED` | Proactive fallback timeout | `GREETING` | Queue the welcome phrase after the configured delay. |
| `GREETING` | Greeting `tts_completed` | `WAITING_FOR_INTENT` | Enable acceptance of new transcript/intent events. |
| `GREETING` | `cancel` or session timeout | `IDLE` | Cancel queued speech when supported and reset. |
| `GREETING` | TTS failure | `ERROR` | Record failure; do not listen during unresolved playback. |
| `WAITING_FOR_INTENT` | `affirmative` or `reservation` | `WAITING_FOR_QR` after prompt completion | Queue QR prompt and pause listening while it is spoken. |
| `WAITING_FOR_INTENT` | `negative` | `IDLE` | Announce the no-reservation response; never enable QR or navigation. |
| `WAITING_FOR_INTENT` | `repeat` or `greeting` | `WAITING_FOR_INTENT` | Replay the yes/no question; preserve session. |
| `WAITING_FOR_INTENT` | `unknown` or inactivity timeout, retries remain | `WAITING_FOR_INTENT` | Increment retry count and replay clarification. |
| `WAITING_FOR_INTENT` | `unknown` or inactivity timeout, retries exhausted | `ERROR` | Announce inability to help and reset. |
| `WAITING_FOR_INTENT` | `cancel` | `IDLE` | Acknowledge and reset. |
| `WAITING_FOR_QR` | `qr_detected` | `VERIFYING_QR` | Correlate one detection with one validation request. |
| `WAITING_FOR_QR` | `repeat`, or QR timeout with retries remaining | `WAITING_FOR_QR` | Replay QR prompt and increment retry only for timeout. |
| `WAITING_FOR_QR` | QR timeout with retries exhausted | `ERROR` | Announce timeout and reset. |
| `WAITING_FOR_QR` | `cancel` | `IDLE` | Acknowledge and reset. |
| `VERIFYING_QR` | Valid response with destination ID | `READY_TO_GUIDE` | Store only the verified destination ID needed for navigation. |
| `VERIFYING_QR` | Invalid response and retries remain | `WAITING_FOR_QR` | Announce rejection and request another QR. |
| `VERIFYING_QR` | Expired response, unavailable service, timeout, or retries exhausted | `ERROR` | Announce mapped failure; clear QR and destination data. |
| `VERIFYING_QR` | `cancel` | `IDLE` | Ignore any later response by request/session ID and reset. |
| `READY_TO_GUIDE` | Guidance announcement completed and all safety/readiness gates pass | `NAVIGATING` when action accepts | Send verified destination ID to the guide action; orchestrator resolves its configured waypoint. |
| `READY_TO_GUIDE` | Unknown destination, gate failure, or action rejection | `ERROR` | Do not publish or send an unchecked coordinate goal. |
| `READY_TO_GUIDE` | `cancel` | `IDLE` | Do not submit the action. |
| `NAVIGATING` | Nav2 action succeeds | `ARRIVED` | Queue arrival announcement. |
| `NAVIGATING` | `cancel`, emergency stop, action abort, or navigation timeout | `ERROR` | Cancel goal, ensure safe stop, and map the failure outcome. |
| `ARRIVED` | Arrival announcement completed | `ARRIVED` | Submit the configured `reception` destination through the same gated guide action. |
| `ARRIVED` | Return navigation succeeds | `IDLE` | Clear session and destination after the robot reaches reception. |
| `ARRIVED` | Return navigation fails, is cancelled, or times out | `ERROR` | Announce navigation failure and do not retry movement automatically. |
| `ARRIVED` | TTS failure or timeout | `IDLE` | Record failure and reset; navigation is already complete. |
| `ERROR` | Error handling/announcement completed or timed out | `IDLE` | Clear session, retries, pending request IDs, and destination. |

## Interface decisions for later milestones

These contracts are implemented incrementally by the milestone that first
requires them.

| Proposed interface | Kind | Minimum data | Decision and rationale |
| --- | --- | --- | --- |
| `Transcript` | Message / topic | Header/stamp, transcript text, detected language, confidence | Implemented in Milestone 3 as `evo_reception_interfaces/msg/Transcript`. The STT node publishes only final, usable results. |
| `IntentResult` | Message / topic | Header/stamp, intent enum/string constant, confidence, source transcript | Implemented in Milestone 4 as `evo_reception_interfaces/msg/IntentResult`. It is a structured event stream and intent detection remains side-effect free. |
| `SpeakRequest` | Message / topic | Request/session ID, phrase key or text, language, priority/cancel policy | Custom message required for a queued TTS stream. Fixed reception text remains configuration, not hardcoded logic. |
| `SpeakingStatus` | Message / topic | Request/session ID, `idle`/`speaking`/`completed`/`failed`, error detail | Custom message required so the dialogue manager can correlate completion and pause STT reliably. |
| `QrDetection` | Message / topic | Header/stamp, detection ID, decoded payload, decoder source | Custom message required to replace JSON. Payload is an opaque validation input and never a navigation destination. |
| `ValidateQr` | Service | Request ID and QR payload; response outcome, stable destination ID, optional user-facing reason | Implemented in Milestone 6 as `evo_reception_interfaces/srv/ValidateQr`. It defines valid, invalid, expired, duplicate, and unavailable outcomes and does not expose customer data. |
| `PersonDetection` | Message / topic | Header/stamp, tracking ID, confidence, distance, normalized image position | Implemented in Milestone 8 as the detector, rosbag replay, or mock-fixture input to approach filtering. |
| `PersonApproach` | Message / topic | Header/stamp, event ID, tracking ID, zone ID, distance/confidence | Implemented in Milestone 8 as the clean, debounced vision event consumed by the dialogue manager. |
| Person presence | `std_msgs/msg/Bool` topic | `/vision/people/presence` | Transient-local state used to gate greeting acceptance and disarm when the visitor leaves. |
| `GuideToDestination` | Action | Goal: request ID and verified destination ID; feedback: accepted/active status; result: arrived/cancelled/timeout/failed plus reason | Implemented in Milestone 7. Its server maps IDs through YAML and uses `NavigateToPose` only when explicitly configured for real navigation. |
| `NavigationStatus` | Message / topic | Request ID, destination ID, state, detail, timestamp | Implemented in Milestone 7 for accepted, active, arrived, cancelled, timeout, and failed navigation states. |
| `WorkflowStatus` | Message / topic | Session ID, dialogue state, outcome/reason, destination ID, timestamp | Implemented in Milestone 9 for kiosk/admin observation without parsing logs or internal topics. |

No custom action should replace `nav2_msgs/action/NavigateToPose`; it remains the
orchestrator's robot-navigation interface. No custom service is needed for
intent detection or TTS because those are event/queue streams. The
`/e_stop*`, sensor, map, costmap, point-cloud, velocity, and Nav2 interfaces
retain their standard message types.

## Reusable components

- QR image subscription, decoding, scan throttling, and duplicate cooldown in
  `qr_scanner_node`.
- Reservation API call and response/error mapping logic in
  `qr_reservation_bridge_node`, behind a later typed service.
- Calibrated depth obstacle point cloud and its Nav2 costmap integration.
- Navigation goal transform, mapped-space/clearance/path validation, and
  `ComputePathToPose` client.
- Nav2 `NavigateToPose`, localization, planner/controller/behavior servers, and
  lifecycle management.
- Emergency-stop latch/status, collision monitor, velocity smoothing/routing,
  and final command watchdog.
- Existing launch files as package-level composition points.

The combined translator node is useful only as legacy/prototype code. Its
`/voice/translation` topic is not reusable as a reception contract.

## Blockers, risks, and unclear behavior

- The reservation API now returns `room_id`, which is exposed as the stable
  destination ID. The later waypoint registry must use the same ID vocabulary.
- The bridge maps explicit API error codes for invalid, expired, duplicate, and
  unavailable outcomes. Unknown 4xx validation errors remain invalid.
- The dialogue manager invokes the typed bridge service only from
  `WAITING_FOR_QR`; the bridge's direct scanner-topic mode is disabled by
  default and retained only as an explicit legacy option.
- The QR scanner and bridge use JSON inside `std_msgs/String`, with no schema
  version or request/session correlation.
- Voice launch parameters are ineffective because `translator_node` uses
  constants. The node also blocks in its listening loop, performs runtime
  translation-package downloads, speaks its own output, and does not publish
  transcript or speaking status. These are Milestones 1–3 concerns.
- The object detector is explicitly scaffold-only, so no approach event,
  distance filter, reception zone, debounce, or one-greeting guarantee exists.
- No waypoint registry or stable mapping from reservation room to pose exists.
  Waypoint frame, orientation, room ID vocabulary, reception waypoint, and
  ownership of map-specific registries must be supplied before Milestone 7.
- The goal validator reports validation only. Publishing a validated pose does
  not provide correlated navigation acceptance, feedback, cancellation, or
  arrival to a reception caller.
- Readiness is spread across Nav2 lifecycle state, localization/TF, map/costmap,
  goal-validator status, and emergency-stop status. The precise readiness gate
  belongs in the later navigation orchestrator and needs mockable checks.
- The dashboard cancels Nav2 through the action protocol's generated service;
  reception code should use an action client cancellation API instead.
- Return-to-reception is implemented in Milestone 9 through the same waypoint
  registry, action, and safety gates as outbound guidance.

## Milestone 0 acceptance

- Interface inventory and reuse decisions are documented above.
- Dialogue states, intents, events, timeouts, failures, and transitions are
  documented above.
- Missing typed messages, service, and action are identified for later
  milestones.
- This milestone changes documentation only; it introduces no feature behavior
  or runtime dependency.
