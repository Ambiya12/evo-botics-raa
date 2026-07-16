from evo_navigation.reception_nav_readiness_checker import (
    ReceptionNavReadinessChecker,
    format_status,
)


def test_ready_requires_action_map_localization_and_clear_estop():
    ready = {
        "action": True,
        "map": True,
        "localization": True,
        "estop": False,
    }
    assert ReceptionNavReadinessChecker.is_ready(ready)

    for key in ("action", "map", "localization"):
        incomplete = dict(ready)
        incomplete[key] = False
        assert not ReceptionNavReadinessChecker.is_ready(incomplete)

    for estop in (None, True):
        incomplete = dict(ready)
        incomplete["estop"] = estop
        assert not ReceptionNavReadinessChecker.is_ready(incomplete)


def test_status_format_distinguishes_missing_and_active_estop():
    status = {
        "action": False,
        "map": True,
        "localization": False,
        "estop": None,
    }
    assert format_status(status) == (
        "action=missing; map=ready; localization=missing; estop=missing"
    )

    status["estop"] = True
    assert format_status(status).endswith("estop=active")
