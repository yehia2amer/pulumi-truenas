#!/usr/bin/env python
"""Read-only diff: desired app values vs. live TrueNAS app.config.

Runs ONLY read methods (app.config) so it never mutates anything and never
touches Pulumi state. For each managed app it builds the values dict the
Pulumi program *would* send, fetches the live config, and prints the
differences at leaf-key level.

This answers "what would `pulumi up` change?" without importing or applying.

Usage:
    uv run python scripts/diff_values.py --host truenas.local --ssh-user yehia
    uv run python scripts/diff_values.py --app sonarr --app qbittorrent
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from typing import Any

from pulumi_truenas.models import app_values, stack

from pulumi_truenas.api import build_api

# Only these top-level keys are managed by our builders. Everything else in
# app.config (ix_context, ix_volumes, labels, certificates, release_name, ...)
# is TrueNAS-managed and intentionally ignored.
_MANAGED_KEYS = {"TZ", "network", "storage", "run_as", "resources", "flaresolverr", "qbittorrent"}


def _desired_for(app_name: str) -> dict[str, Any] | None:
    for spec in stack.CATALOG_APPS:
        if spec.app_name != app_name:
            continue
        if spec.catalog_app == "qbittorrent":
            return app_values.qbittorrent_values(
                tz=stack.TZ,
                web_port=spec.web_port,
                bt_port=spec.bt_port or 51413,
                host_path=spec.host_path or "",
                container_path=spec.container_path or "",
                uid=stack.UID,
                gid=stack.GID,
            )
        return app_values.servarr_values(
            tz=stack.TZ,
            web_port=spec.web_port,
            host_path=spec.host_path or "",
            container_path=spec.container_path or "",
            uid=stack.UID,
            gid=stack.GID,
            instance_name=spec.instance_name,
        )
    if app_name == stack.FLARESOLVERR.app_name:
        return app_values.flaresolverr_values(tz=stack.TZ, web_port=stack.FLARESOLVERR.web_port)
    return None


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = value
    return out


def _diff(desired: dict[str, Any], live: dict[str, Any]) -> list[str]:
    # Restrict live to the keys we manage, so noise is excluded.
    live_managed = {k: v for k, v in live.items() if k in _MANAGED_KEYS}
    d_flat = _flatten(desired)
    l_flat = _flatten(live_managed)
    keys = sorted(set(d_flat) | set(l_flat))
    lines: list[str] = []
    for key in keys:
        dv = d_flat.get(key, "<absent>")
        lv = l_flat.get(key, "<absent>")
        if dv != lv:
            lines.append(f"    ~ {key}: live={lv!r} -> desired={dv!r}")
    return lines


def _diff_configarr(api: Any) -> bool:
    """Best-effort compare of the Configarr custom-app compose YAML."""
    name = stack.CONFIGARR.app_name
    row = api.app_get(name, retrieve_config=False)
    if row is None:
        print(f"[diff] {name}: absent (would be created)")
        return True
    print(
        f"[ok]   {name}: present ({row.get('state')}) "
        f"[custom-app compose diff not compared field-by-field]"
    )
    return False


def _diff_directories(host: str, ssh_user: str) -> bool:
    """Read-only presence check of the managed directories via SSH stat."""
    target = f"{ssh_user}@{host}" if ssh_user else host
    quoted = " ".join(shlex.quote(p) for p in stack.TRASH_DIRECTORIES)
    # Print each dir that is missing; empty output => all present.
    cmd = f'for d in {quoted}; do [ -d "$d" ] || echo "$d"; done'
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", target, cmd],
        check=False,
        capture_output=True,
    )
    missing = [line for line in result.stdout.decode().splitlines() if line.strip()]
    if missing:
        print(f"[diff] directories: {len(missing)} missing (would be created)")
        for d in missing:
            print(f"    + {d}")
        return True
    print(f"[ok]   directories: all {len(stack.TRASH_DIRECTORIES)} present")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", default="midclt_ssh")
    parser.add_argument("--host", default="truenas.local")
    parser.add_argument("--ssh-user", default="yehia")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--api-key-env", default="TRUENAS_API_KEY")
    parser.add_argument("--app", action="append", default=[], help="limit to app (repeatable)")
    parser.add_argument(
        "--no-extras",
        action="store_true",
        help="skip Configarr + directory checks (catalog apps only)",
    )
    args = parser.parse_args()

    targets = args.app or [s.app_name for s in stack.CATALOG_APPS] + [stack.FLARESOLVERR.app_name]

    api = build_api(
        transport=args.transport,
        host=args.host,
        ssh_user=args.ssh_user,
        api_url=args.api_url,
        api_key_env=args.api_key_env,
    )
    any_diffs = False
    try:
        for app in targets:
            desired = _desired_for(app)
            if desired is None:
                print(f"[skip] {app}: no desired-values builder")
                continue
            live = api.app_config(app)  # type: ignore[attr-defined]
            if not isinstance(live, dict):
                print(f"[warn] {app}: unexpected app.config result")
                continue
            lines = _diff(desired, live)
            if lines:
                any_diffs = True
                print(f"[diff] {app}: {len(lines)} field(s) would change")
                print("\n".join(lines))
            else:
                print(f"[ok]   {app}: no managed-field drift")

        if not args.no_extras and not args.app:
            any_diffs |= _diff_configarr(api)
            any_diffs |= _diff_directories(args.host, args.ssh_user)
    finally:
        api.close()  # type: ignore[attr-defined]
    print("\n" + ("Drift detected." if any_diffs else "No drift in managed fields."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
