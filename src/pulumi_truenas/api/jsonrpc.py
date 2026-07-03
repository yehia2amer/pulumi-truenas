from __future__ import annotations

import itertools
import time
from typing import Any

from pulumi_truenas.api.base import TrueNasApiError
from pulumi_truenas.api.operations import TrueNasOperationsMixin
from pulumi_truenas.util import json as jsonutil

_JOB_POLL_INTERVAL_S = 2.0
_JOB_TIMEOUT_S = 1800.0


class JsonRpcTrueNasApi(TrueNasOperationsMixin):
    """TrueNAS API adapter over the JSON-RPC 2.0 WebSocket endpoint.

    Connects to ``wss://<host>/api/current``, authenticates with an API key
    via ``auth.login_with_api_key``, and invokes methods with JSON-RPC. Job
    methods return a job id which is polled via ``core.get_jobs`` until the
    job reaches a terminal state.
    """

    name = "jsonrpc"

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        verify_tls: bool = False,
        ca_cert: str | None = None,
        job_timeout_s: float = _JOB_TIMEOUT_S,
        poll_interval_s: float = _JOB_POLL_INTERVAL_S,
        connect_timeout_s: float = 15.0,
        connect_retries: int = 3,
        connect_backoff_s: float = 2.0,
    ) -> None:
        self._url = url
        self._api_key = api_key
        # TrueNAS ships a self-signed certificate by default, so verification
        # is off unless the caller opts in (e.g. a proper cert is installed).
        self._verify_tls = verify_tls
        self._ca_cert = ca_cert
        self._job_timeout_s = job_timeout_s
        self._poll_interval_s = poll_interval_s
        self._connect_timeout_s = connect_timeout_s
        self._connect_retries = max(1, connect_retries)
        self._connect_backoff_s = connect_backoff_s
        self._ids = itertools.count(1)
        self._ws: Any | None = None

    # --- connection ---
    def _sslopt(self) -> dict[str, Any] | None:
        import ssl

        if not self._url.startswith("wss://"):
            return None
        if self._ca_cert:
            # Verify against a provided CA bundle/cert.
            return {"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": self._ca_cert}
        if not self._verify_tls:
            return {"cert_reqs": ssl.CERT_NONE}
        return None  # default system verification

    def _open_once(self) -> Any:
        from websocket import create_connection

        ws = create_connection(self._url, sslopt=self._sslopt(), timeout=self._connect_timeout_s)
        self._ws = ws
        self._authenticate()
        return ws

    def _connect(self) -> Any:
        if self._ws is not None:
            return self._ws
        last_exc: Exception | None = None
        for attempt in range(self._connect_retries):
            outcome = self._try_open()
            if outcome is True:
                return self._ws
            last_exc = outcome  # type: ignore[assignment]
            if attempt < self._connect_retries - 1:
                time.sleep(self._connect_backoff_s * (attempt + 1))
        raise TrueNasApiError(
            f"failed to connect to {self._url} after {self._connect_retries} attempts: {last_exc}"
        )

    def _try_open(self) -> Any:
        """Return True on success, or the transient exception to retry."""
        try:
            self._open_once()
        except ImportError as exc:  # pragma: no cover
            raise TrueNasApiError("websocket-client is required for the jsonrpc transport") from exc
        except TrueNasApiError:
            raise  # auth failures are not retryable
        except Exception as exc:  # transient connection errors
            self._ws = None
            return exc
        return True

    def _authenticate(self) -> None:
        result = self._rpc("auth.login_with_api_key", self._api_key)
        if result is not True:
            raise TrueNasApiError("TrueNAS API key authentication failed")

    # --- raw JSON-RPC ---
    def _rpc(self, method: str, *params: object) -> Any:
        ws = self._ws
        if ws is None:
            ws = self._connect()
        request_id = next(self._ids)
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": list(params),
        }
        ws.send(jsonutil.dumps(payload))
        while True:
            message = jsonutil.loads(ws.recv())
            if message.get("id") != request_id:
                # Ignore notifications / unrelated responses.
                continue
            if "error" in message:
                error = self._redact(str(message["error"]))
                raise TrueNasApiError(f"{method} failed: {error}")
            return message.get("result")

    def _redact(self, text: str) -> str:
        """Never let the API key appear in an error message."""
        if self._api_key and self._api_key in text:
            return text.replace(self._api_key, "***")
        return text

    # --- port surface ---
    def call(self, method: str, *params: object) -> object:
        self._connect()
        return self._rpc(method, *params)

    def job(self, method: str, *params: object) -> object:
        self._connect()
        job_id = self._rpc(method, *params)
        if not isinstance(job_id, int):
            # Not all "job" methods necessarily return an id in every version.
            return job_id
        return self._wait_for_job(job_id)

    def _wait_for_job(self, job_id: int) -> Any:
        deadline = time.monotonic() + self._job_timeout_s
        while True:
            rows = self._rpc("core.get_jobs", [["id", "=", job_id]])
            job = rows[0] if isinstance(rows, list) and rows else None
            if job is not None:
                state = job.get("state")
                if state == "SUCCESS":
                    return job.get("result")
                if state in {"FAILED", "ABORTED"}:
                    error = job.get("error") or job.get("exception") or "unknown error"
                    raise TrueNasApiError(f"job {job_id} {state}: {error}")
            if time.monotonic() > deadline:
                raise TrueNasApiError(f"job {job_id} timed out after {self._job_timeout_s}s")
            time.sleep(self._poll_interval_s)

    def close(self) -> None:
        if self._ws is not None:
            try:
                self._ws.close()
            finally:
                self._ws = None
