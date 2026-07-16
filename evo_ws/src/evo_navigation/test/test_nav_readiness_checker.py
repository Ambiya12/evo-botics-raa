from types import SimpleNamespace

from evo_navigation.nav_readiness_checker import NavReadinessChecker, format_status


class FakeFuture:
    def __init__(self, response=None, done=False):
        self._done = done
        self._response = response
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def done(self):
        return self._done

    def result(self):
        return self._response


class FakeClient:
    def __init__(self, futures, ready=True):
        self.futures = list(futures)
        self.ready = ready
        self.removed = []

    def call_async(self, _request):
        return self.futures.pop(0)

    def remove_pending_request(self, future):
        self.removed.append(future)

    def service_is_ready(self):
        return self.ready


class FakeChecker(NavReadinessChecker):
    def __init__(self, client, replacement_client, timeout=5.0):
        self._lifecycle_request_timeout_sec = timeout
        self._lifecycle_clients = {"bt_navigator": client}
        self._lifecycle_futures = {"bt_navigator": None}
        self._lifecycle_requested_at = {"bt_navigator": None}
        self._lifecycle_probe_timeouts = {"bt_navigator": 0}
        self._lifecycle_probe_retrying = {"bt_navigator": False}
        self.lifecycle_states = {"bt_navigator": "unavailable"}
        self._replacement_client = replacement_client
        self.destroyed_clients = []

    def create_client(self, _service_type, _service_name):
        return self._replacement_client

    def count_publishers(self, _topic):
        return 1

    def destroy_client(self, client):
        self.destroyed_clients.append(client)

    def validator_available(self):
        return True


def test_ready_requires_every_navigation_signal():
    status = {
        "lifecycle": "active",
        "map": 1,
        "validator": True,
        "cmd_vel_nav_raw": 1,
        "cmd_vel": 1,
    }

    assert NavReadinessChecker.is_ready(status)

    inactive = dict(status)
    inactive["lifecycle"] = "/map_server: inactive"
    assert not NavReadinessChecker.is_ready(inactive)

    for key in ("map", "validator", "cmd_vel_nav_raw", "cmd_vel"):
        incomplete = dict(status)
        incomplete[key] = 0
        assert not NavReadinessChecker.is_ready(incomplete)


def test_status_format_matches_robot_startup_output():
    assert format_status(
        {
            "lifecycle": "/map_server: unavailable",
            "map": 0,
            "validator": False,
            "cmd_vel_nav_raw": 0,
            "cmd_vel": 0,
        }
    ) == (
        "lifecycle=/map_server: unavailable; map=0; validator=no; "
        "cmd_vel_nav_raw=0; cmd_vel=0"
    )


def test_stuck_lifecycle_probe_is_replaced_and_later_recovers():
    stuck_future = FakeFuture()
    active_response = SimpleNamespace(
        current_state=SimpleNamespace(label="active"),
    )
    active_future = FakeFuture(response=active_response, done=True)
    original_client = FakeClient([stuck_future])
    replacement_client = FakeClient([active_future])
    checker = FakeChecker(original_client, replacement_client)

    checker.poll_lifecycle_states(now=10.0)
    checker.poll_lifecycle_states(now=15.0)

    assert original_client.removed == [stuck_future]
    assert checker.destroyed_clients == [original_client]
    assert checker._lifecycle_clients["bt_navigator"] is replacement_client
    assert checker._lifecycle_probe_timeouts["bt_navigator"] == 1
    assert "probe timed out 1 time(s); retrying" in checker.status()["lifecycle"]

    checker.poll_lifecycle_states(now=15.1)
    checker.poll_lifecycle_states(now=15.2)

    assert checker.lifecycle_states["bt_navigator"] == "active"
    assert checker._lifecycle_probe_retrying["bt_navigator"] is False
    assert checker.status()["lifecycle"] == "active"


def test_repeated_probe_timeouts_are_reported():
    first_future = FakeFuture()
    second_future = FakeFuture()
    original_client = FakeClient([first_future])
    replacement_client = FakeClient([second_future])
    checker = FakeChecker(original_client, replacement_client, timeout=2.0)

    checker.poll_lifecycle_states(now=1.0)
    checker.poll_lifecycle_states(now=3.0)
    checker.poll_lifecycle_states(now=3.1)
    checker.poll_lifecycle_states(now=5.2)

    assert checker._lifecycle_probe_timeouts["bt_navigator"] == 2
    assert "probe timed out 2 time(s); retrying" in checker.status()["lifecycle"]


def test_only_one_lifecycle_request_is_in_flight():
    first_future = FakeFuture()
    second_future = FakeFuture()
    first_client = FakeClient([first_future])
    second_client = FakeClient([second_future])
    checker = FakeChecker(first_client, first_client)
    checker._lifecycle_clients["planner_server"] = second_client
    checker._lifecycle_futures["planner_server"] = None
    checker._lifecycle_requested_at["planner_server"] = None
    checker._lifecycle_probe_timeouts["planner_server"] = 0
    checker._lifecycle_probe_retrying["planner_server"] = False
    checker.lifecycle_states["planner_server"] = "unavailable"

    checker.poll_lifecycle_states(now=1.0)

    assert checker._lifecycle_futures["bt_navigator"] is first_future
    assert checker._lifecycle_futures["planner_server"] is None
