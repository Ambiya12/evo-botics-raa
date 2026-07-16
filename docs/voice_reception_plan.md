# Voice Reception Implementation Plan

Work through one milestone per implementation request. Do not begin the next
milestone until the current acceptance checks pass or its blocker is recorded.

## Target Workflow

1. Detect a visitor approaching reception.
2. Greet the visitor once.
3. Listen for a supported reception intent.
4. Ask for a QR code or repeat the clarification prompt.
5. Verify the QR code and reservation.
6. Resolve the verified room to a navigation waypoint.
7. Announce success and guide the visitor with Nav2.
8. Announce arrival, handle failure safely, and return to reception.

## Milestone 0: Freeze Contracts

Scope:
- Audit existing voice, reception, vision, and navigation interfaces.
- Define dialogue states, intents, events, timeouts, and failure outcomes.
- Decide which interfaces require custom messages, services, or actions.

Acceptance:
- A documented interface table and state-transition table exist.
- No feature behavior or new runtime dependency is introduced.

## Milestone 1: Voice Package Foundations

Scope:
- Split configuration from `translator_fr_en.py`.
- Make model, device, language, audio device, and voice paths ROS parameters.
- Remove startup downloads and unsafe shell interpolation.
- Declare all runtime dependencies and provide a mock audio mode.

Acceptance:
- `evo_voice` builds and launches without downloading files.
- Parameters are visible through ROS 2 and invalid configuration fails clearly.

## Milestone 2: Text-to-Speech Node

Scope:
- Add a queued Piper TTS node with speak requests.
- Publish `idle`, `speaking`, `completed`, and `failed` status.
- Keep fixed reception phrases in YAML configuration.

Acceptance:
- Requests play in order and never overlap.
- Mock tests verify queue and status behavior without a speaker.

## Milestone 3: Speech-to-Text Node

Scope:
- Add microphone capture, voice activity detection, and Faster Whisper.
- Publish transcript, detected language, confidence, and timestamps.
- Pause capture while TTS is speaking.

Acceptance:
- Empty/noisy input does not publish a usable transcript.
- Mock audio fixtures test valid, empty, and failed transcription paths.

## Milestone 4: Intent Detector

Scope:
- Normalize transcript text and load phrases/synonyms from YAML.
- Support presence-gated `greeting`, contextual `affirmative` and `negative`
  answers, plus `reservation`, `repeat`, `cancel`, and `unknown`.
- Publish a structured intent result with confidence and source transcript.

Acceptance:
- Unit tests cover synonyms, punctuation, casing, false positives, and unknowns.
- Intent detection has no QR, TTS, or navigation side effects.

## Milestone 5: Dialogue Manager

Scope:
- Implement `IDLE`, `PRESENCE_ARMED`, `GREETING`, `WAITING_FOR_INTENT`,
  `WAITING_FOR_QR`, `VERIFYING_QR`, `READY_TO_GUIDE`, `NAVIGATING`,
  `ARRIVED`, and `ERROR`.
- Handle retry count, inactivity timeout, cancellation, and session reset.
- Coordinate STT, intent, and TTS through ROS interfaces.

Acceptance:
- Transition tests cover the happy path and every invalid transition.
- Unknown speech repeats the clarification prompt up to a configured limit.

## Milestone 6: QR Integration

Scope:
- Connect the dialogue manager to the existing QR scanner and reservation bridge.
- Enable workflow acceptance only while waiting for a QR code.
- Handle invalid, expired, duplicate, unavailable, and valid responses.

Acceptance:
- Navigation cannot be requested from an invalid or unverified QR result.
- A valid result contains a stable room or destination ID.

## Milestone 7: Waypoints and Navigation

Scope:
- Add a YAML room-to-waypoint registry with reception as a destination.
- Add a navigation orchestrator using the Nav2 `NavigateToPose` action.
- Publish accepted, active, arrived, cancelled, timeout, and failed states.

Acceptance:
- Unknown rooms fail without movement.
- Mock Nav2 tests cover success, rejection, cancellation, and timeout.
- E-stop, localization, and Nav2 readiness gate every navigation request.

## Milestone 8: Human Approach Detection

Scope:
- Implement person detection and depth/distance filtering in `evo_vision`.
- Add reception-zone, debounce, cooldown, and one-greeting-per-session rules.

Acceptance:
- Passing people and repeated frames do not trigger repeated greetings.
- Detection can be replayed from recorded sensor data without hardware.

## Milestone 9: End-to-End Reception

Scope:
- Connect human detection, dialogue, QR verification, waypoint lookup, and Nav2.
- Add arrival speech, navigation failure speech, and return-to-reception behavior.
- Publish workflow status for the kiosk/admin dashboard.

Acceptance:
- Automated mocks pass the complete happy path and major failure paths.
- A hardware checklist validates microphone, speaker, camera, QR, and movement.

## Milestone 10: Reliability and Multilingual Support

Scope:
- Measure noisy-room accuracy and end-to-end latency.
- Tune VAD/STT thresholds and add acoustic echo cancellation if required.
- Add French or translation only after the English workflow is reliable.

Acceptance:
- Target latency and recognition success thresholds are documented and measured.
- Offline operation and recovery after node restart are verified.

## Deferred Until Required

- LLM-based intent detection or open-ended conversation.
- Wake-word detection.
- Cloud speech services.
- Additional languages beyond the validated reception workflow.
- Badge dispensing, face recognition, or visitor identity inference.
