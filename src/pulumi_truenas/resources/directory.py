from __future__ import annotations

import shlex
import subprocess
from typing import Any

import pulumi
from pulumi.dynamic import (
    CheckFailure,
    CheckResult,
    CreateResult,
    DiffResult,
    ReadResult,
    Resource,
    ResourceProvider,
    UpdateResult,
)

from pulumi_truenas import validation
from pulumi_truenas.config import ProviderSettings
from pulumi_truenas.provider import Provider, resolve_settings


def _ssh_target(settings: ProviderSettings) -> str:
    return f"{settings.ssh_user}@{settings.host}" if settings.ssh_user else settings.host


def _id_token(value: Any) -> str:
    """Render an owner/group id for chown.

    Pulumi serializes ints through JSON, so numeric ids can arrive as floats
    (e.g. 568.0). Normalize whole-number floats back to plain ints so chown
    receives '568', not '568.0'.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _run_ssh(settings: ProviderSettings, remote_cmd: str) -> str:
    argv = ["ssh", "-o", "BatchMode=yes", _ssh_target(settings), remote_cmd]
    result = subprocess.run(argv, check=False, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.decode(errors="replace")
            or result.stdout.decode(errors="replace")
            or f"ssh command failed: {remote_cmd}"
        )
    return result.stdout.decode(errors="replace").strip()


class _DirectoryProvider(ResourceProvider):
    """Ensures a host directory exists with the requested ownership/mode.

    Uses SSH for now; can later migrate to the TrueNAS filesystem API. This
    provider is intentionally non-destructive: delete does NOT remove the
    directory (media/appdata must survive app recreation).
    """

    def _settings(self, inputs: dict[str, Any]) -> ProviderSettings:
        return ProviderSettings.from_inputs(inputs)

    def _ensure(self, inputs: dict[str, Any]) -> dict[str, Any]:
        settings = self._settings(inputs)
        path = inputs["path"]
        quoted = shlex.quote(path)

        # 1. Always ensure the directory exists.
        _run_ssh(settings, f"mkdir -p {quoted}")

        # 2. Read current ownership/mode so we only mutate on real drift.
        current = self._read_state(inputs)

        owner = inputs.get("owner")
        group = inputs.get("group")
        owner_tok = _id_token(owner) if owner is not None else None
        group_tok = _id_token(group) if group is not None else None

        owner_drift = owner_tok is not None and current.get("actual_owner") != owner_tok
        group_drift = group_tok is not None and current.get("actual_group") != group_tok
        if owner_drift or group_drift:
            spec = f"{owner_tok or ''}:{group_tok or ''}"
            # chown may require privileges; try sudo -n, fall back to plain.
            self._run_privileged(settings, f"chown {shlex.quote(spec)} {quoted}")

        mode = inputs.get("mode")
        if mode:
            want = str(mode).lstrip("0") or "0"
            have = str(current.get("actual_mode") or "").lstrip("0") or "0"
            if want != have:
                self._run_privileged(settings, f"chmod {shlex.quote(str(mode))} {quoted}")

        return self._read_state(inputs)

    def _run_privileged(self, settings: ProviderSettings, cmd: str) -> None:
        """Run a command that may need root; prefer sudo -n, fall back to plain."""
        try:
            _run_ssh(settings, f"sudo -n {cmd} 2>/dev/null || {cmd}")
        except RuntimeError:
            # Re-run without the sudo wrapper to surface the real error.
            _run_ssh(settings, cmd)

    def _read_state(self, inputs: dict[str, Any]) -> dict[str, Any]:
        settings = self._settings(inputs)
        path = inputs["path"]
        quoted = shlex.quote(path)
        # stat: uid gid octal-mode ; empty output => missing.
        out = _run_ssh(
            settings,
            f"stat -c '%u %g %a' {quoted} 2>/dev/null || true",
        )
        if not out:
            return {
                "_exists": False,
                "actual_owner": None,
                "actual_group": None,
                "actual_mode": None,
            }
        uid, gid, octal = out.split()
        return {
            "_exists": True,
            "actual_owner": uid,
            "actual_group": gid,
            "actual_mode": octal,
        }

    def check(self, _olds: dict[str, Any], news: dict[str, Any]) -> CheckResult:
        failures: list = []
        validation.check_connection(news, failures)
        path = news.get("path")
        if not path or not isinstance(path, str):
            failures.append(CheckFailure("path", "'path' is required"))
        elif not path.startswith("/"):
            failures.append(CheckFailure("path", "'path' must be absolute (start with '/')"))
        mode = news.get("mode")
        if mode is not None and not str(mode).isdigit():
            failures.append(CheckFailure("mode", "'mode' must be an octal string, e.g. '0755'"))
        return CheckResult(news, failures)

    def create(self, props: dict[str, Any]) -> CreateResult:
        inputs = props
        state = self._ensure(inputs)
        return CreateResult(id_=inputs["path"], outs={**inputs, **state})

    def read(self, id_: str, props: dict[str, Any]) -> ReadResult:
        state = props
        if not state.get("host"):
            return ReadResult(id_=id_, outs={**state, "path": id_})
        fresh = self._read_state(state)
        return ReadResult(id_=id_, outs={**state, "path": id_, **fresh})

    def diff(self, _id: str, _olds: dict[str, Any], _news: dict[str, Any]) -> DiffResult:
        old, new = _olds, _news
        replaces = ["path"] if old.get("path") != new.get("path") else []
        changes = any(old.get(k) != new.get(k) for k in ("owner", "group", "mode"))
        return DiffResult(changes=changes or bool(replaces), replaces=replaces)

    def update(self, _id: str, _olds: dict[str, Any], _news: dict[str, Any]) -> UpdateResult:
        state = self._ensure(_news)
        return UpdateResult(outs={**_news, **state})

    def delete(self, _id: str, _props: dict[str, Any]) -> None:
        # Intentionally a no-op: never delete host directories/data.
        return None


class DirectoryArgs:
    """Inputs for a Directory resource (resource-specific fields only)."""

    def __init__(
        self,
        *,
        path: pulumi.Input[str],
        owner: pulumi.Input[int | str] | None = None,
        group: pulumi.Input[int | str] | None = None,
        mode: pulumi.Input[str] | None = None,
    ) -> None:
        self.path = path
        self.owner = owner
        self.group = group
        self.mode = mode


class Directory(Resource):
    """Ensures a host directory exists on the TrueNAS server (SSH-backed)."""

    actual_owner: pulumi.Output[str]
    actual_group: pulumi.Output[str]
    actual_mode: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: DirectoryArgs,
        *,
        provider: Provider | None = None,
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
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        settings = resolve_settings(
            provider,
            host=host,
            transport=transport,
            ssh_user=ssh_user,
            api_url=api_url,
            api_key=api_key,
            api_key_env=api_key_env,
            verify_tls=verify_tls,
            ca_cert=ca_cert,
            job_timeout_s=job_timeout_s,
            poll_interval_s=poll_interval_s,
        )
        props = {
            "actual_owner": None,
            "actual_group": None,
            "actual_mode": None,
            "_exists": None,
            **vars(args),
            **settings.to_inputs(),
        }
        super().__init__(_DirectoryProvider(), name, props, opts)
