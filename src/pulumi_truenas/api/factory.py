from __future__ import annotations

from pulumi_truenas.api.base import TrueNasApiError, TrueNasApiPort
from pulumi_truenas.api.jsonrpc import JsonRpcTrueNasApi
from pulumi_truenas.api.midclt_ssh import MidcltSshTrueNasApi


def build_api(
    *,
    transport: str,
    host: str,
    ssh_user: str | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
    api_key_env: str = "TRUENAS_API_KEY",
    verify_tls: bool = False,
    ca_cert: str | None = None,
    job_timeout_s: float | None = None,
    poll_interval_s: float | None = None,
) -> TrueNasApiPort:
    """Construct a TrueNAS API adapter for the requested transport.

    transport:
      - ``midclt_ssh`` : ssh + midclt process adapter (bootstrap/fallback).
      - ``jsonrpc``    : JSON-RPC over WebSocket (preferred long-term).
    """
    transport = transport.lower()
    if transport in {"midclt_ssh", "midclt-ssh", "ssh"}:
        return MidcltSshTrueNasApi(host=host, ssh_user=ssh_user)
    if transport in {"jsonrpc", "json-rpc", "ws", "websocket"}:
        from pulumi_truenas.secrets import resolve_api_key

        url = api_url or f"wss://{host}/api/current"
        # Precedence: explicit arg -> Pulumi config/env/.env chain.
        key = api_key or resolve_api_key(env_var=api_key_env)
        if not key:
            raise TrueNasApiError(
                "jsonrpc transport requires an API key. Provide it via one of:\n"
                f"  pulumi config set --secret truenas-pulumi:apiKey <key>\n"
                f"  export {api_key_env}=<key>\n"
                f"  echo '{api_key_env}=<key>' >> .env"
            )
        kwargs: dict[str, object] = {"verify_tls": verify_tls, "ca_cert": ca_cert}
        if job_timeout_s is not None:
            kwargs["job_timeout_s"] = job_timeout_s
        if poll_interval_s is not None:
            kwargs["poll_interval_s"] = poll_interval_s
        return JsonRpcTrueNasApi(url=url, api_key=key, **kwargs)  # type: ignore[arg-type]
    raise TrueNasApiError(f"unknown transport: {transport!r}")
