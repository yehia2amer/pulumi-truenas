"""Shared input validation and structured-diff helpers for resources.

These back the dynamic providers' ``check()`` (input validation before apply)
and ``diff()`` (field-level change detection) methods.
"""

from __future__ import annotations

import re
from typing import Any

from pulumi.dynamic import CheckFailure

# TrueNAS app name rules (from app.create schema):
# lowercase alphanumeric, must start with a letter, hyphens allowed but not at
# the ends, 1..40 chars.
APP_NAME_RE = re.compile(r"^[a-z]([-a-z0-9]*[a-z0-9])?$")

VALID_TRANSPORTS = ("jsonrpc", "midclt_ssh")
VALID_DESIRED_STATES = ("RUNNING", "STOPPED")


def _require(inputs: dict[str, Any], key: str, failures: list[CheckFailure]) -> None:
    value = inputs.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        failures.append(CheckFailure(key, f"'{key}' is required"))


def check_connection(inputs: dict[str, Any], failures: list[CheckFailure]) -> None:
    """Validate the connection settings embedded in every resource's inputs."""
    transport = inputs.get("transport")
    if transport not in VALID_TRANSPORTS:
        failures.append(
            CheckFailure(
                "transport",
                f"transport must be one of {VALID_TRANSPORTS}, got {transport!r}",
            )
        )
    _require(inputs, "host", failures)


def check_app_name(inputs: dict[str, Any], failures: list[CheckFailure]) -> None:
    name = inputs.get("app_name")
    if not name or not isinstance(name, str):
        failures.append(CheckFailure("app_name", "'app_name' is required"))
        return
    if not APP_NAME_RE.match(name):
        failures.append(
            CheckFailure(
                "app_name",
                "'app_name' must be lowercase alphanumeric, start with a letter, "
                "may contain hyphens (not at the ends), max 40 chars",
            )
        )
    if len(name) > 40:
        failures.append(CheckFailure("app_name", "'app_name' must be at most 40 characters"))


def check_desired_state(inputs: dict[str, Any], failures: list[CheckFailure]) -> None:
    ds = inputs.get("desired_state")
    if ds is None:
        return
    if str(ds).upper() not in VALID_DESIRED_STATES:
        failures.append(
            CheckFailure(
                "desired_state",
                f"desired_state must be one of {VALID_DESIRED_STATES} (or unset)",
            )
        )


# --- structured diff ------------------------------------------------------
def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict/list into dotted leaf keys for diffing."""
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = value
    return out


def changed_keys(old: Any, new: Any) -> list[str]:
    """Return the sorted set of leaf keys that differ between two structures."""
    of = flatten(old)
    nf = flatten(new)
    keys = set(of) | set(nf)
    return sorted(k for k in keys if of.get(k) != nf.get(k))
