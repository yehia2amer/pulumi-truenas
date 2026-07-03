from __future__ import annotations

from typing import Protocol, runtime_checkable


class TrueNasApiError(Exception):
    """Raised when a TrueNAS API call fails."""


@runtime_checkable
class TrueNasApiPort(Protocol):
    """Common interface for talking to the TrueNAS middleware.

    Implementations wrap either the JSON-RPC WebSocket API or the
    ``ssh + midclt`` process adapter. Both expose the same high-level
    surface so Pulumi resources are transport-agnostic.
    """

    name: str

    def call(self, method: str, *params: object) -> object:
        """Invoke a non-job middleware method and return the decoded result."""
        ...

    def job(self, method: str, *params: object) -> object:
        """Invoke a job method, wait for completion, and return its result."""
        ...

    def close(self) -> None:
        """Release any underlying resources (connections, sockets)."""
        ...
