from __future__ import annotations

from typing import Any

from pulumi_truenas.api.operations import TrueNasOperationsMixin


class FakeApi(TrueNasOperationsMixin):
    """Records call/job invocations and returns scripted responses."""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, tuple]] = []
        self.jobs: list[tuple[str, tuple]] = []

    def call(self, method: str, *params: object) -> object:
        self.calls.append((method, params))
        return self.responses.get(method)

    def job(self, method: str, *params: object) -> object:
        self.jobs.append((method, params))
        return self.responses.get(method)


# --- dataset ops ---
def test_dataset_create_payload():
    api = FakeApi()
    api.dataset_create("tank/media", {"compression": "LZ4", "recordsize": "1M"})
    method, params = api.calls[0]
    assert method == "pool.dataset.create"
    assert params[0] == {"name": "tank/media", "compression": "LZ4", "recordsize": "1M"}


def test_dataset_delete_defaults_non_recursive():
    api = FakeApi()
    api.dataset_delete("tank/media")
    method, params = api.calls[0]
    assert method == "pool.dataset.delete"
    assert params == ("tank/media", {"recursive": False, "force": False})


def test_dataset_exists_true_false():
    present = FakeApi({"pool.dataset.query": [{"id": "tank/media"}]})
    assert present.dataset_exists("tank/media") is True
    absent = FakeApi({"pool.dataset.query": []})
    assert absent.dataset_exists("tank/media") is False


def test_dataset_get_uses_id_filter():
    api = FakeApi({"pool.dataset.query": [{"id": "tank/x", "type": "FILESYSTEM"}]})
    row = api.dataset_get("tank/x")
    assert row is not None
    assert row["type"] == "FILESYSTEM"
    method, params = api.calls[0]
    assert method == "pool.dataset.query"
    assert params[0] == [["id", "=", "tank/x"]]


# --- app power ops ---
def test_app_start_stop_use_call():
    api = FakeApi()
    api.app_start("sonarr")
    api.app_stop("radarr")
    assert ("app.start", ("sonarr",)) in api.calls
    assert ("app.stop", ("radarr",)) in api.calls


# --- app query / exists ---
def test_app_exists():
    api = FakeApi({"app.query": [{"name": "sonarr", "state": "RUNNING"}]})
    assert api.app_exists("sonarr") is True
    api2 = FakeApi({"app.query": []})
    assert api2.app_exists("ghost") is False
