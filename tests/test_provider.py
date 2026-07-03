from __future__ import annotations

import pytest

from pulumi_truenas.provider import Provider, resolve_settings


def test_provider_requires_host():
    with pytest.raises(ValueError):
        Provider("nas", host="")


def test_provider_rejects_unknown_transport():
    with pytest.raises(ValueError):
        Provider("nas", host="nas.local", transport="carrier-pigeon")


def test_provider_connection_inputs_roundtrip():
    p = Provider(
        "nas",
        host="nas.local",
        transport="jsonrpc",
        api_url="wss://nas.local/api/current",
        verify_tls=True,
    )
    inputs = p.connection_inputs()
    assert inputs["host"] == "nas.local"
    assert inputs["transport"] == "jsonrpc"
    assert inputs["api_url"] == "wss://nas.local/api/current"
    assert inputs["verify_tls"] is True


def test_provider_defaults_jsonrpc_no_hardcoded_host():
    p = Provider("nas", host="example.internal")
    s = p.settings
    assert s.transport == "jsonrpc"
    assert s.host == "example.internal"
    # No leftover deployment defaults.
    assert s.ssh_user is None


def test_resolve_settings_prefers_provider():
    p = Provider("nas", host="from-provider")
    s = resolve_settings(p, host="ignored")
    assert s.host == "from-provider"


def test_resolve_settings_from_kwargs():
    s = resolve_settings(None, host="kw.local", transport="midclt_ssh", ssh_user="admin")
    assert s.host == "kw.local"
    assert s.transport == "midclt_ssh"
    assert s.ssh_user == "admin"


def test_resolve_settings_requires_host_without_provider():
    with pytest.raises(ValueError):
        resolve_settings(None)


def test_resolve_settings_rejects_unknown_transport():
    with pytest.raises(ValueError):
        resolve_settings(None, host="h", transport="nope")


def test_provider_threads_hardening_options():
    provider = Provider(
        "nas",
        host="nas.local",
        ca_cert="/etc/ca.pem",
        job_timeout_s=3600,
        poll_interval_s=5,
    )
    inputs = provider.connection_inputs()
    assert inputs["ca_cert"] == "/etc/ca.pem"
    assert inputs["job_timeout_s"] == 3600
    assert inputs["poll_interval_s"] == 5


def test_resolve_settings_threads_hardening_kwargs():
    s = resolve_settings(None, host="h", ca_cert="/x.pem", job_timeout_s=10, poll_interval_s=1)
    assert s.ca_cert == "/x.pem"
    assert s.job_timeout_s == 10
    assert s.poll_interval_s == 1
