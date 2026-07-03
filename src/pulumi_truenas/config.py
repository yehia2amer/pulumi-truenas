from __future__ import annotations

from dataclasses import dataclass

from pulumi_truenas.api import TrueNasApiPort, build_api


@dataclass(frozen=True)
class ProviderSettings:
    """Connection settings shared by every dynamic provider.

    These values are serialized into each resource's inputs so the dynamic
    provider (which runs out-of-process during ``pulumi up``) can rebuild the
    API client.

    ``api_key`` is only populated for the jsonrpc transport and is passed into
    resources wrapped as a Pulumi secret (encrypted in state, masked in logs).
    When it is not set, the API layer falls back to ``$api_key_env``.

    Note: this is the internal serialization type. Library users construct a
    :class:`pulumi_truenas.Provider` (or pass connection kwargs) rather than
    this dataclass directly. There are deliberately **no deployment-specific
    defaults** here (no host/user) — the ``Provider`` supplies them.
    """

    transport: str = "jsonrpc"
    host: str = ""
    ssh_user: str | None = None
    api_url: str | None = None
    api_key_env: str = "TRUENAS_API_KEY"
    api_key: str | None = None
    verify_tls: bool = False
    ca_cert: str | None = None
    job_timeout_s: float | None = None
    poll_interval_s: float | None = None

    def to_inputs(self) -> dict[str, object]:
        return {
            "transport": self.transport,
            "host": self.host,
            "ssh_user": self.ssh_user,
            "api_url": self.api_url,
            "api_key_env": self.api_key_env,
            "api_key": self.api_key,
            "verify_tls": self.verify_tls,
            "ca_cert": self.ca_cert,
            "job_timeout_s": self.job_timeout_s,
            "poll_interval_s": self.poll_interval_s,
        }

    @classmethod
    def from_inputs(cls, inputs: dict[str, object]) -> ProviderSettings:
        return cls(
            transport=str(inputs.get("transport", "jsonrpc")),
            host=str(inputs.get("host", "")),
            ssh_user=inputs.get("ssh_user"),  # type: ignore[arg-type]
            api_url=inputs.get("api_url"),  # type: ignore[arg-type]
            api_key_env=str(inputs.get("api_key_env", "TRUENAS_API_KEY")),
            api_key=inputs.get("api_key"),  # type: ignore[arg-type]
            verify_tls=bool(inputs.get("verify_tls", False)),
            ca_cert=inputs.get("ca_cert"),  # type: ignore[arg-type]
            job_timeout_s=inputs.get("job_timeout_s"),  # type: ignore[arg-type]
            poll_interval_s=inputs.get("poll_interval_s"),  # type: ignore[arg-type]
        )

    def build(self) -> TrueNasApiPort:
        return build_api(
            transport=self.transport,
            host=self.host,
            ssh_user=self.ssh_user,
            api_url=self.api_url,
            api_key=self.api_key,
            api_key_env=self.api_key_env,
            verify_tls=self.verify_tls,
            ca_cert=self.ca_cert,
            job_timeout_s=self.job_timeout_s,
            poll_interval_s=self.poll_interval_s,
        )
