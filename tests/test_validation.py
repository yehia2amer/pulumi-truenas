from __future__ import annotations

from pulumi_truenas import validation


def _reasons(failures):
    return {f.property for f in failures}


def test_check_connection_valid():
    f: list = []
    validation.check_connection({"transport": "jsonrpc", "host": "nas.local"}, f)
    assert f == []


def test_check_connection_bad_transport_and_missing_host():
    f: list = []
    validation.check_connection({"transport": "carrier", "host": ""}, f)
    assert _reasons(f) == {"transport", "host"}


def test_check_app_name_valid():
    f: list = []
    validation.check_app_name({"app_name": "sonarr-4k"}, f)
    assert f == []


def test_check_app_name_invalid():
    for bad in ("Sonarr", "-bad", "bad-", "1abc", "a" * 41, ""):
        f: list = []
        validation.check_app_name({"app_name": bad}, f)
        assert any(x.property == "app_name" for x in f), bad


def test_check_desired_state():
    f: list = []
    validation.check_desired_state({"desired_state": "running"}, f)  # case-insensitive
    assert f == []
    f2: list = []
    validation.check_desired_state({"desired_state": "PAUSED"}, f2)
    assert _reasons(f2) == {"desired_state"}
    f3: list = []
    validation.check_desired_state({}, f3)  # unset is fine
    assert f3 == []


def test_flatten_nested():
    flat = validation.flatten({"a": {"b": 1}, "c": [10, 20]})
    assert flat == {"a.b": 1, "c[0]": 10, "c[1]": 20}


def test_changed_keys_reports_leaf_paths():
    old = {"network": {"web_port": {"port_number": 30013}}, "TZ": "UTC"}
    new = {"network": {"web_port": {"port_number": 30099}}, "TZ": "UTC"}
    assert validation.changed_keys(old, new) == ["network.web_port.port_number"]


def test_changed_keys_added_and_removed():
    assert validation.changed_keys({"a": 1}, {"a": 1, "b": 2}) == ["b"]
    assert validation.changed_keys({"a": 1, "b": 2}, {"a": 1}) == ["b"]


def test_changed_keys_none_when_equal():
    same = {"x": {"y": [1, 2, 3]}}
    assert validation.changed_keys(same, dict(same)) == []
