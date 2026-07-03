from __future__ import annotations

import orjson
import pytest

from pulumi_truenas.api.midclt_ssh import MidcltSshTrueNasApi


class RecordingRunner:
    """Captures argv and returns a queued JSON response."""

    def __init__(self, responses: list[bytes]) -> None:
        self.responses = list(responses)
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> bytes:
        self.calls.append(argv)
        return self.responses.pop(0) if self.responses else b""


def make_api(responses: list[bytes]) -> tuple[MidcltSshTrueNasApi, RecordingRunner]:
    runner = RecordingRunner(responses)
    api = MidcltSshTrueNasApi(host="truenas.local", ssh_user="yehia", runner=runner)
    return api, runner


def test_call_builds_ssh_midclt_command():
    api, runner = make_api([b'{"version": "25.10.4"}'])
    result = api.call("system.info")
    assert result == {"version": "25.10.4"}
    argv = runner.calls[0]
    assert argv[0] == "ssh"
    assert argv[-2] == "yehia@truenas.local"
    remote = argv[-1]
    assert remote == "midclt call system.info"


def test_call_encodes_params_as_json():
    api, runner = make_api([b"[]"])
    api.call("app.query", [["name", "in", ["sonarr"]]], {"extra": {"retrieve_config": False}})
    remote = runner.calls[0][-1]
    # The remote string is shell-quoted; the JSON payloads must be present.
    assert "app.query" in remote
    assert '["name","in",["sonarr"]]' in remote.replace("'", "")
    assert '{"extra":{"retrieve_config":false}}' in remote.replace("'", "")


def test_job_uses_dash_j_flag():
    api, runner = make_api([b'{"ok": true}'])
    api.job("app.delete", "flaresolverr", {"remove_ix_volumes": False})
    remote = runner.calls[0][-1]
    assert "midclt call -j app.delete" in remote


def test_app_create_catalog_payload():
    api, runner = make_api([b"null"])
    api.app_create_catalog(
        app_name="flaresolverr",
        catalog_app="flaresolverr",
        train="community",
        values={"TZ": "Africa/Cairo"},
    )
    remote = runner.calls[0][-1].replace("'", "")
    payload = orjson.loads(remote.split("midclt call -j app.create ", 1)[1])
    assert payload["custom_app"] is False
    assert payload["app_name"] == "flaresolverr"
    assert payload["catalog_app"] == "flaresolverr"
    assert payload["train"] == "community"
    assert payload["values"] == {"TZ": "Africa/Cairo"}


def test_app_create_custom_payload():
    api, runner = make_api([b"null"])
    api.app_create_custom(app_name="configarr", compose_yaml="services: {}\n")
    remote = runner.calls[0][-1].replace("'", "")
    payload = orjson.loads(remote.split("midclt call -j app.create ", 1)[1])
    assert payload["custom_app"] is True
    assert payload["custom_compose_config_string"] == "services: {}\n"


def test_app_delete_defaults_are_conservative():
    api, runner = make_api([b"null"])
    api.app_delete("sonarr")
    remote = runner.calls[0][-1].replace("'", "")
    _, opts_json = remote.split('midclt call -j app.delete "sonarr" ', 1)
    opts = orjson.loads(opts_json)
    assert opts["remove_ix_volumes"] is False
    assert opts["force_remove_ix_volumes"] is False
    assert opts["force_remove_custom_app"] is False


def test_empty_output_returns_none():
    api, _ = make_api([b""])
    assert api.call("app.start", "sonarr") is None


def test_command_failure_raises():
    from pulumi_truenas.api.base import TrueNasApiError

    class FailingRunner:
        def __call__(self, argv: list[str]) -> bytes:
            raise TrueNasApiError("boom")

    api = MidcltSshTrueNasApi(host="h", runner=FailingRunner())
    with pytest.raises(TrueNasApiError):
        api.call("system.info")
