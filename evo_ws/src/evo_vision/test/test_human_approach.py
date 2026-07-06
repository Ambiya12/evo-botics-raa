import pytest

from evo_vision.human_approach import (
    ApproachConfig,
    HumanApproachFilter,
    PersonObservation,
)


def config(**overrides) -> ApproachConfig:
    values = {
        "min_confidence": 0.7,
        "min_distance_m": 0.5,
        "max_distance_m": 2.5,
        "zone_min_x": 0.25,
        "zone_max_x": 0.75,
        "zone_min_y": 0.2,
        "zone_max_y": 0.9,
        "debounce_frames": 3,
        "cooldown_sec": 5.0,
        "absence_reset_sec": 1.0,
    }
    values.update(overrides)
    return ApproachConfig(**values)


def person(**overrides) -> PersonObservation:
    values = {
        "tracking_id": "person-1",
        "confidence": 0.9,
        "distance_m": 1.5,
        "normalized_x": 0.5,
        "normalized_y": 0.5,
    }
    values.update(overrides)
    return PersonObservation(**values)


def test_passing_person_does_not_trigger_without_debounce() -> None:
    detector = HumanApproachFilter(config(debounce_frames=3))

    assert detector.process(person(), now=0.0) is None
    assert detector.process(person(), now=0.1) is None
    assert detector.process(person(confidence=0.1), now=0.2) is None


def test_repeated_frames_publish_only_one_approach() -> None:
    detector = HumanApproachFilter(config(debounce_frames=3))
    events = [
        detector.process(person(), now=index * 0.1)
        for index in range(10)
    ]

    assert sum(event is not None for event in events) == 1


def test_presence_tracks_valid_observation_and_absence_timeout() -> None:
    detector = HumanApproachFilter(
        config(debounce_frames=1, absence_reset_sec=1.0)
    )

    detector.process(person(), now=0.0)

    assert detector.is_person_present(now=0.5)
    detector.tick(now=1.1)
    assert not detector.is_person_present(now=1.1)


def test_presence_armed_survives_five_second_detector_dropout() -> None:
    detector = HumanApproachFilter(
        config(debounce_frames=1, absence_reset_sec=10.0)
    )
    detector.process(person(), now=0.0)
    detector.update_dialogue_state("PRESENCE_ARMED")

    detector.process(person(confidence=0.1), now=1.0)
    detector.tick(now=6.0)

    assert detector.is_person_present(now=6.0)

    # A later valid frame refreshes the departure timer, keeping the visitor
    # armed for as long as they remain intermittently visible.
    detector.process(person(), now=7.0)
    detector.tick(now=16.0)
    assert detector.is_person_present(now=16.0)


@pytest.mark.parametrize(
    "observation",
    [
        person(confidence=0.69),
        person(distance_m=0.4),
        person(distance_m=2.6),
        person(normalized_x=0.2),
        person(normalized_x=0.8),
        person(normalized_y=0.1),
        person(normalized_y=0.95),
    ],
)
def test_confidence_distance_and_zone_filters(
    observation: PersonObservation,
) -> None:
    detector = HumanApproachFilter(config(debounce_frames=1))

    assert detector.process(observation, now=0.0) is None


def test_dialogue_session_allows_only_one_greeting() -> None:
    detector = HumanApproachFilter(config(debounce_frames=1))

    first = detector.process(person(), now=0.0)
    detector.update_dialogue_state("GREETING")
    detector.update_dialogue_state("IDLE")
    same_person = detector.process(person(), now=0.5)

    assert first is not None
    assert same_person is None


def test_absence_and_cooldown_allow_a_later_session() -> None:
    detector = HumanApproachFilter(config(debounce_frames=1))
    assert detector.process(person(), now=0.0) is not None
    detector.update_dialogue_state("GREETING")
    detector.update_dialogue_state("IDLE")

    detector.tick(now=1.1)
    assert detector.process(person(tracking_id="person-2"), now=2.0) is None
    detector.tick(now=3.1)

    later = detector.process(person(tracking_id="person-2"), now=5.1)

    assert later is not None
    assert later.tracking_id == "person-2"


def test_recorded_detection_sequence_can_be_replayed_without_hardware() -> None:
    detector = HumanApproachFilter(config(debounce_frames=2))
    recorded_frames = [
        (0.0, person(normalized_x=0.1)),
        (0.1, person()),
        (0.2, person()),
        (0.3, person()),
    ]

    events = [
        detector.process(observation, now=timestamp)
        for timestamp, observation in recorded_frames
    ]

    assert [event.tracking_id for event in events if event is not None] == [
        "person-1"
    ]


def test_active_dialogue_suppresses_approach_events() -> None:
    detector = HumanApproachFilter(config(debounce_frames=1))
    detector.update_dialogue_state("NAVIGATING")

    assert detector.process(person(), now=0.0) is None


def test_unknown_startup_state_suppresses_until_idle_state_is_received() -> None:
    detector = HumanApproachFilter(
        config(debounce_frames=1),
        initial_dialogue_state="UNKNOWN",
    )

    assert detector.process(person(), now=0.0) is None
    detector.update_dialogue_state("IDLE")

    assert detector.process(person(), now=0.1) is not None


def test_invalid_threshold_configuration_fails_clearly() -> None:
    with pytest.raises(ValueError, match="max_distance_m"):
        HumanApproachFilter(
            config(min_distance_m=2.0, max_distance_m=1.0)
        )
