from __future__ import annotations

import orjson
import pytest

from pulumi_truenas.api.base import TrueNasApiError
from pulumi_truenas.api.jsonrpc import JsonRpcTrueNasApi


class FakeWebSocket:
    """Scripted JSON-RPC peer.

    ``handler(method, params, id)`` returns a response dict; the socket
    queues it for the next ``recv``.
    """

    def __init__(self, handler):
        self._handler = handler
        self._outbox: list[str] = []
        self.sent: list[dict] = []
        self.closed = False

    def send(self, raw: str) -> None:
        message = orjson.loads(raw)
        self.sent.append(message)
        response = self._handler(message["method"], message["params"], message["id"])
        self._outbox.append(orjson.dumps(response).decode())

    def recv(self) -> str:
        return self._outbox.pop(0)

    def close(self) -> None:
        self.closed = True


def install_fake(monkeypatch, handler) -> FakeWebSocket:
    ws = FakeWebSocket(handler)
    import websocket

    monkeypatch.setattr(websocket, "create_connection", lambda url, **kwargs: ws)
    return ws


def test_auth_and_call(monkeypatch):
    def handler(method, params, rid):
        if method == "auth.login_with_api_key":
            assert params == ["KEY"]
            return {"jsonrpc": "2.0", "id": rid, "result": True}
        if method == "system.info":
            return {"jsonrpc": "2.0", "id": rid, "result": {"version": "25.10.4"}}
        raise AssertionError(method)

    install_fake(monkeypatch, handler)
    api = JsonRpcTrueNasApi(url="wss://x/api/current", api_key="KEY")
    assert api.system_info() == {"version": "25.10.4"}


def test_auth_failure_raises(monkeypatch):
    install_fake(
        monkeypatch,
        lambda m, p, rid: {"jsonrpc": "2.0", "id": rid, "result": False},
    )
    api = JsonRpcTrueNasApi(url="wss://x/api/current", api_key="BAD")
    with pytest.raises(TrueNasApiError):
        api.call("system.info")


def test_error_response_raises(monkeypatch):
    def handler(method, params, rid):
        if method == "auth.login_with_api_key":
            return {"jsonrpc": "2.0", "id": rid, "result": True}
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -1, "message": "nope"}}

    install_fake(monkeypatch, handler)
    api = JsonRpcTrueNasApi(url="wss://x/api/current", api_key="KEY")
    with pytest.raises(TrueNasApiError):
        api.call("app.query", [])


def test_job_polls_until_success(monkeypatch):
    state = {"polls": 0}

    def handler(method, params, rid):
        if method == "auth.login_with_api_key":
            return {"jsonrpc": "2.0", "id": rid, "result": True}
        if method == "app.create":
            return {"jsonrpc": "2.0", "id": rid, "result": 42}
        if method == "core.get_jobs":
            state["polls"] += 1
            if state["polls"] < 2:
                return {"jsonrpc": "2.0", "id": rid, "result": [{"id": 42, "state": "RUNNING"}]}
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": [{"id": 42, "state": "SUCCESS", "result": {"name": "flaresolverr"}}],
            }
        raise AssertionError(method)

    install_fake(monkeypatch, handler)
    api = JsonRpcTrueNasApi(url="wss://x/api/current", api_key="KEY", poll_interval_s=0.0)
    result = api.app_create_catalog(
        app_name="flaresolverr",
        catalog_app="flaresolverr",
        train="community",
        values={},
    )
    assert result == {"name": "flaresolverr"}
    assert state["polls"] >= 2


def test_job_failure_raises(monkeypatch):
    def handler(method, params, rid):
        if method == "auth.login_with_api_key":
            return {"jsonrpc": "2.0", "id": rid, "result": True}
        if method == "app.delete":
            return {"jsonrpc": "2.0", "id": rid, "result": 7}
        if method == "core.get_jobs":
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": [{"id": 7, "state": "FAILED", "error": "kaboom"}],
            }
        raise AssertionError(method)

    install_fake(monkeypatch, handler)
    api = JsonRpcTrueNasApi(url="wss://x/api/current", api_key="KEY", poll_interval_s=0.0)
    with pytest.raises(TrueNasApiError):
        api.app_delete("sonarr")


# --- Phase 6 hardening ---
def test_sslopt_self_signed_by_default():
    api = JsonRpcTrueNasApi(url="wss://nas/api/current", api_key="k")
    import ssl

    assert api._sslopt() == {"cert_reqs": ssl.CERT_NONE}


def test_sslopt_ca_cert_verifies():
    api = JsonRpcTrueNasApi(url="wss://nas/api/current", api_key="k", ca_cert="/etc/ca.pem")
    import ssl

    opt = api._sslopt()
    assert opt is not None
    assert opt["cert_reqs"] == ssl.CERT_REQUIRED
    assert opt["ca_certs"] == "/etc/ca.pem"


def test_sslopt_verify_tls_uses_system_default():
    api = JsonRpcTrueNasApi(url="wss://nas/api/current", api_key="k", verify_tls=True)
    assert api._sslopt() is None


def test_redact_hides_api_key():
    api = JsonRpcTrueNasApi(url="wss://nas/api/current", api_key="super-secret")
    assert "super-secret" not in api._redact("boom super-secret boom")
    assert "***" in api._redact("boom super-secret boom")


def test_connect_retries_then_fails(monkeypatch):
    attempts = {"n": 0}

    def boom(url, **kwargs):
        attempts["n"] += 1
        raise OSError("connection refused")

    import websocket

    monkeypatch.setattr(websocket, "create_connection", boom)
    api = JsonRpcTrueNasApi(
        url="wss://nas/api/current",
        api_key="k",
        connect_retries=3,
        connect_backoff_s=0.0,
    )
    with pytest.raises(TrueNasApiError):
        api.call("system.info")
    assert attempts["n"] == 3


def test_connect_retries_then_succeeds(monkeypatch):
    state = {"n": 0}

    def handler(method, params, rid):
        if method == "auth.login_with_api_key":
            return {"jsonrpc": "2.0", "id": rid, "result": True}
        return {"jsonrpc": "2.0", "id": rid, "result": {"version": "25.10"}}

    ws = FakeWebSocket(handler)

    def flaky(url, **kwargs):
        state["n"] += 1
        if state["n"] < 2:
            raise OSError("transient")
        return ws

    import websocket

    monkeypatch.setattr(websocket, "create_connection", flaky)
    api = JsonRpcTrueNasApi(url="wss://nas/api/current", api_key="k", connect_backoff_s=0.0)
    assert api.system_info() == {"version": "25.10"}
    assert state["n"] == 2
