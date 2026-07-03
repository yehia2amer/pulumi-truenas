"""The TrueNAS ``Provider`` component.

Because the resources in this library are Pulumi *dynamic* providers (which run
out-of-process during ``pulumi up`` and cannot use Pulumi's native provider
plumbing), ``Provider`` is a lightweight connection holder rather than a native
``pulumi.ProviderResource``.

Usage::

    import pulumi_truenas as truenas

    nas = truenas.Provider("nas", host="nas.local", transport="jsonrpc")

    truenas.CatalogApp(
        "sonarr",
        truenas.CatalogAppArgs(
            app_name="sonarr", catalog_app="sonarr", train="community", values={...}
        ),
        provider=nas,
    )

Every resource accepts either ``provider=<Provider>`` or the individual
connection keyword arguments (``host=``, ``transport=`` ...) as an escape hatch.
"""

from __future__ import annotations

from pulumi_truenas.config import ProviderSettings

_VALID_TRANSPORTS = {"jsonrpc", "midclt_ssh"}


class Provider:
    """Connection settings shared by TrueNAS resources.

    Parameters
    ----------
    name:
        Logical name for this provider (for readability; not sent to TrueNAS).
    host:
        TrueNAS hostname or IP (required). e.g. ``nas.local`` or ``10.0.0.5``.
    transport:
        ``jsonrpc`` (JSON-RPC over WebSocket, recommended) or ``midclt_ssh``
        (ssh + midclt, bootstrap/fallback).
    ssh_user:
        SSH user for the ``midclt_ssh`` transport.
    api_url:
        Override the JSON-RPC URL (defaults to ``wss://<host>/api/current``).
    api_key:
        API key for the ``jsonrpc`` transport. Pass a Pulumi secret so it is
        encrypted in state. If omitted, the API layer falls back to
        ``$api_key_env`` / ``.env``.
    api_key_env:
        Environment variable name to read the key from (default
        ``TRUENAS_API_KEY``).
    verify_tls:
        Verify the server's TLS certificate. Default ``False`` because TrueNAS
        ships a self-signed certificate; enable once a trusted cert is present.
    ca_cert:
        Path to a CA cert/bundle to verify the server against (implies
        verification). Use this instead of ``verify_tls`` when you have a
        private/self-signed CA.
    job_timeout_s:
        Max seconds to wait for a middleware job to finish (jsonrpc). Increase
        for large image pulls; default ~1800s.
    poll_interval_s:
        Seconds between job status polls (jsonrpc).
    """

    def __init__(
        self,
        name: str,
        *,
        host: str,
        transport: str = "jsonrpc",
        ssh_user: str | None = None,
        api_url: str | None = None,
        api_key: object | None = None,
        api_key_env: str = "TRUENAS_API_KEY",
        verify_tls: bool = False,
        ca_cert: str | None = None,
        job_timeout_s: float | None = None,
        poll_interval_s: float | None = None,
    ) -> None:
        if not host:
            raise ValueError("Provider requires a non-empty 'host'")
        if transport not in _VALID_TRANSPORTS:
            raise ValueError(
                f"unknown transport {transport!r}; expected one of {sorted(_VALID_TRANSPORTS)}"
            )
        self.name = name
        self._settings = ProviderSettings(
            transport=transport,
            host=host,
            ssh_user=ssh_user,
            api_url=api_url,
            api_key_env=api_key_env,
            api_key=api_key,  # type: ignore[arg-type]
            verify_tls=verify_tls,
            ca_cert=ca_cert,
            job_timeout_s=job_timeout_s,
            poll_interval_s=poll_interval_s,
        )

    @property
    def settings(self) -> ProviderSettings:
        return self._settings

    def connection_inputs(self) -> dict[str, object]:
        """Serialized connection settings to embed into resource inputs."""
        return self._settings.to_inputs()


def resolve_settings(
    provider: Provider | None,
    *,
    host: str | None = None,
    transport: str | None = None,
    ssh_user: str | None = None,
    api_url: str | None = None,
    api_key: object | None = None,
    api_key_env: str | None = None,
    verify_tls: bool | None = None,
    ca_cert: str | None = None,
    job_timeout_s: float | None = None,
    poll_interval_s: float | None = None,
) -> ProviderSettings:
    """Resolve connection settings from a Provider or explicit kwargs.

    Precedence: an explicit ``provider`` wins; otherwise the individual kwargs
    are used. ``host`` is required in the kwargs path.
    """
    if provider is not None:
        return provider.settings
    if not host:
        raise ValueError("either 'provider=' or 'host=' must be supplied to a TrueNAS resource")
    if transport is None:
        transport = "jsonrpc"
    if transport not in _VALID_TRANSPORTS:
        raise ValueError(
            f"unknown transport {transport!r}; expected one of {sorted(_VALID_TRANSPORTS)}"
        )
    return ProviderSettings(
        transport=transport,
        host=host,
        ssh_user=ssh_user,
        api_url=api_url,
        api_key_env=api_key_env or "TRUENAS_API_KEY",
        api_key=api_key,  # type: ignore[arg-type]
        verify_tls=verify_tls if verify_tls is not None else False,
        ca_cert=ca_cert,
        job_timeout_s=job_timeout_s,
        poll_interval_s=poll_interval_s,
    )
