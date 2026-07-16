# Evo Botics — Prioritized Backlog (P0/P1/P2)

| Task | Priority (P0/P1/P2) | Owner | DoD (definition of done) | Dependencies | Estimation (S/M/L) |
|---|---|---|---|---|---|
| Set up Jetson + ROS2 Humble baseline | P0 | Backend/DevOps | Robot boots with ROS2 workspace; camera, LiDAR, audio, and touchscreen are detected; setup steps documented in README. | None | M |
| Bring up Nav2 + SLAM mapping | P0 | ROS/Nav | Robot creates/loads a map and can navigate to at least 3 waypoints safely on one floor. | Set up Jetson + ROS2 Humble baseline | L |
| Define room waypoint registry + guide orchestrator | P0 | ROS/Nav | Given a room ID, robot selects waypoint, starts guidance, and confirms arrival on UI. | Bring up Nav2 + SLAM mapping | M |
| Implement QR/badge scan node (`vision_node`) | P0 | Vision | Scanner reads valid QR/badge in normal indoor light with retry flow and clear user feedback. | Set up Jetson + ROS2 Humble baseline | M |
| Integrate Reservation API | P0 | Backend/DevOps | Real reservation validation is returned to UI; median response time target < 3s; unavailable or malformed responses fail closed. | Implement QR/badge scan node (`vision_node`) | M |
| Build touchscreen MVP flow (welcome → scan → result → guide) | P0 | Web/UI | Full visitor flow works end-to-end on touchscreen with error states and clear prompts. | Integrate Reservation API; Define room waypoint registry + guide orchestrator | M |
| Implement voice mediation MVP (`STT` → translate → `TTS`) | P0 | AI Voice | At least 2 languages supported with subtitle display and audible response in live test. | Set up Jetson + ROS2 Humble baseline | L |
| Add safety controls (Emergency Stop + watchdog) | P0 | ROS/Nav | Emergency stop halts movement immediately; watchdog detects critical node failure and triggers safe state. | Bring up Nav2 + SLAM mapping | M |
| Implement staff notification pipeline (`notify_node`) | P0 | Backend/DevOps | Help request from UI sends email/webhook with timestamp and robot context. | Build touchscreen MVP flow (welcome → scan → result → guide); Integrate Reservation API | S |
| Run end-to-end MVP acceptance scenario | P0 | PM/QA | Scripted test passes: welcome → scan → validate → guide; failures logged and triaged with severity. | All P0 tasks above | M |
| Build admin web interface (`admin_node` via rosbridge) | P1 | Web/UI | Admin can view robot status and trigger remote control + emergency stop from browser. | Add safety controls (Emergency Stop + watchdog); Set up Jetson + ROS2 Humble baseline | M |
| Add monitoring dashboard (battery, nav status, logs) | P1 | Backend/DevOps | Real-time status panel available; logs retained for incident review. | Build admin web interface (`admin_node` via rosbridge) | M |
| Improve voice robustness in noisy environment | P1 | AI Voice | Noise-reduction + confirmation prompts improve recognition in noisy test runs. | Implement voice mediation MVP (`STT` → translate → `TTS`) | M |
| Tune navigation parameters (costmap/footprint/inflation) | P1 | ROS/Nav | Reduced stalls and smoother paths in corridor stress tests. | Bring up Nav2 + SLAM mapping | M |
| Add group visitor flow | P1 | Web/UI + ROS/Nav | Group mode supports start/stop guidance and regroup instructions for multiple visitors. | Build touchscreen MVP flow (welcome → scan → result → guide); Define room waypoint registry + guide orchestrator | M |
| Finalize UML package (use case, sequence, state) | P1 | PM/QA | 3 UML diagrams completed and consistent with implemented architecture. | Run end-to-end MVP acceptance scenario | S |
| Add greeting arm gesture sequence | P2 | ROS/Arm | Safe predefined arm gestures run during welcome scenario with speed/joint limits. | Add safety controls (Emergency Stop + watchdog) | M |
| Implement small object grasp PoC | P2 | ROS/Arm + Vision | Robot picks and releases a light object in controlled conditions. | Add greeting arm gesture sequence | L |
| Add advanced multilingual UX preferences | P2 | Web/UI | Session language preference persists during interaction; subtitles style configurable. | Implement voice mediation MVP (`STT` → translate → `TTS`) | S |
| Add predictive anomaly alerts | P2 | Backend/DevOps | Rule-based alerts triggered for low battery, repeated navigation failure, or node crashes. | Add monitoring dashboard (battery, nav status, logs) | M |

## Notes

- `P0` = MVP-critical path (must be delivered first).
- `P1` = important stabilization/features after MVP path is solid.
- `P2` = stretch objectives if time allows.


- `S` (Small): ~0.5–2 person-days. Low risk, little integration, little testing, clear requirements.
- `M` (Medium): ~3–7 person-days. Some integration, moderate testing, a few unknowns.
- `L` (Large): ~8+ person-days (often spans a sprint). High integration, hardware dependencies, complex 
testing, or unknowns.
