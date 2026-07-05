# Real Robot Session Evidence

Copy this file to a dated, non-secret record for each physical-robot session.
Do not record credentials, complete QR payloads, visitor audio, or identifiable
images.

## Session

- Date/time:
- Operator:
- Location:
- Profile: `robot_safe_base` / `robot_stationary_full`
- Git commit:
- Robot hostname:
- ROS 2 distribution and domain ID:
- Activation phase:

## Device Inventory

| Device | Observed identity or topic | Available | Notes |
| --- | --- | --- | --- |
| Microphone |  | yes/no |  |
| Speaker |  | yes/no |  |
| Color camera |  | yes/no |  |
| Depth/camera info |  | yes/no |  |
| E-stop |  | yes/no |  |
| Base interface |  | yes/no | Unused in apartment |
| STT model |  | yes/no | Local file only |
| TTS voice |  | yes/no | Local file only |
| Backend | mock/local/staging | yes/no | No credentials |

## Movement Lockout

- [ ] `mock_navigation:=true` explicitly selected.
- [ ] `hardware_validated: false` confirmed.
- [ ] No real Nav2 launch started.
- [ ] No `/navigate_to_pose` goal sent.
- [ ] No reception-related velocity command published.
- [ ] Physical base did not move.

## Checks and Evidence

| Check | Pass/fail/deferred | Redacted observation or log reference |
| --- | --- | --- |
| Session preflight |  |  |
| Device inventory |  |  |
| Movement lockout |  |  |
| Current phase acceptance |  |  |
| Shutdown/rollback readiness |  |  |

## Stop Event or Blocker

- Trigger:
- Last workflow state:
- Stop method and result:
- Follow-up required:

## Rollback

- [ ] Active stack stopped.
- [ ] `mock_navigation:=true` restored and confirmed.
- [ ] `hardware_validated: false` confirmed.
- [ ] Affected real subsystem returned to mock/disabled state.
- [ ] Movement-lockout checklist repeated.

## Session Result

- Result: pass / fail / blocked
- Base moved: no / unexpected (describe above)
- Accepted profile/phase:
- Next permitted phase:
- Deferred work:
