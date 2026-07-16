# Changelog

All notable changes to Evo-Botics are documented in this file.

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-17

### Added

- Autonomous reception workflow connecting person detection, voice interaction,
  QR reservation validation, visitor guidance, and kiosk feedback.
- ROS 2 navigation safety gates, readiness diagnostics, waypoint registries, and
  controlled-site deployment profiles.
- Laravel reservation application with role-based administration, booking
  sessions, signed QR payloads, email notifications, and robot telemetry views.
- Robot launch, deployment, diagnostics, recovery, and rollback tooling.
- Continuous integration checks for the Laravel test suite and production
  frontend build.
- Architecture, launch, reliability, hardware acceptance, and QR workflow
  documentation.

### Changed

- Simplified navigation, reception, voice, vision, and dashboard responsibilities
  after the initial feature integrations.
- Hardened dialogue deadlines, navigation outcomes, QR state transitions, and
  fail-closed real-movement configuration.
- Reworked robot startup and demo orchestration around the maintained
  `scripts/robot.sh` entry point.

### Removed

- Obsolete exploration packages, legacy voice translation components, and
  superseded mock reception and navigation scripts.
- Accidentally tracked Python bytecode.

### Fixed

- Voice intent configuration so the `"no"` phrase remains a string when parsed
  from YAML.
- Logout test expectations to match the maintained redirect to the login page.
- Fixable development-tool dependency advisories in the npm lockfile.

[Unreleased]: https://github.com/Ambiya12/evo-botics-raa/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Ambiya12/evo-botics-raa/releases/tag/v0.1.0
