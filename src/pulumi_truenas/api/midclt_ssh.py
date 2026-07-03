from __future__ import annotations

import shlex
import subprocess
from typing import Any

from pulumi_truenas.api.base import TrueNasApiError
from pulumi_truenas.api.operations import TrueNasOperationsMixin
from pulumi_truenas.util import json as jsonutil


class MidcltSshTrueNasApi(TrueNasOperationsMixin):
    """TrueNAS API adapter using ``ssh <host> midclt call ...``.

    This is the bootstrap/fallback transport. It builds ``midclt`` command
    lines, encodes params as JSON, and decodes JSON output. Job methods use
    ``midclt call -j`` which blocks until the job completes and prints the
    result.
    """

    name = "midclt-ssh"

    def __init__(
        self,
        host: str,
        ssh_user: str | None = None,
        *,
        ssh_options: list[str] | None = None,
        runner: object | None = None,
    ) -> None:
        self._host = host
        self._ssh_user = ssh_user
        self._ssh_options = ssh_options or ["-o", "BatchMode=yes"]
        # `runner` is an injection seam for tests: a callable(list[str]) -> bytes.
        self._runner = runner

    # --- command building ---
    def _target(self) -> str:
        return f"{self._ssh_user}@{self._host}" if self._ssh_user else self._host

    def _midclt_command(self, method: str, params: tuple[object, ...], *, job: bool) -> list[str]:
        parts = ["midclt", "call"]
        if job:
            parts.append("-j")
        parts.append(method)
        parts.extend(jsonutil.dumps(param) for param in params)
        return parts

    def _ssh_argv(self, midclt_command: list[str]) -> list[str]:
        remote = " ".join(shlex.quote(part) for part in midclt_command)
        return ["ssh", *self._ssh_options, self._target(), remote]

    # --- execution ---
    def _run(self, argv: list[str]) -> bytes:
        if self._runner is not None:
            return self._runner(argv)  # type: ignore[operator]
        result = subprocess.run(argv, check=False, capture_output=True)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            stdout = result.stdout.decode(errors="replace")
            raise TrueNasApiError(stderr or stdout or f"command failed: {' '.join(argv)}")
        return result.stdout

    def _invoke(self, method: str, params: tuple[object, ...], *, job: bool) -> Any:
        argv = self._ssh_argv(self._midclt_command(method, params, job=job))
        output = self._run(argv).strip()
        if not output:
            return None
        try:
            return jsonutil.loads(output)
        except Exception:
            # Some midclt outputs are bare scalars/strings, not JSON.
            return output.decode() if isinstance(output, bytes) else output

    def call(self, method: str, *params: object) -> object:
        return self._invoke(method, params, job=False)

    def job(self, method: str, *params: object) -> object:
        return self._invoke(method, params, job=True)

    def close(self) -> None:
        return None
