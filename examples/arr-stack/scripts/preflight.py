#!/usr/bin/env python
"""Read-only preflight check against a live TrueNAS host.

Runs ONLY read methods (system.info, app.query, app.config) so it can never
mutate anything. Use it before `pulumi up` to:

  1. confirm connectivity + auth for the chosen transport, and
  2. dump the live `values` schema of any already-installed apps so you can
     compare against models/app_values.py.

Usage:
    uv run python scripts/preflight.py \
        --transport midclt_ssh --host truenas.local --ssh-user yehia

    uv run python scripts/preflight.py \
        --transport jsonrpc --host truenas.local   # needs TRUENAS_API_KEY

    # dump live config for specific apps:
    uv run python scripts/preflight.py --config sonarr --config qbittorrent
"""

from __future__ import annotations

import argparse
import json
import sys

from pulumi_truenas.models import stack

from pulumi_truenas.api import build_api

_ALL_APPS = [s.app_name for s in stack.CATALOG_APPS] + [
    stack.FLARESOLVERR.app_name,
    stack.CONFIGARR.app_name,
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", default="midclt_ssh")
    parser.add_argument("--host", default="truenas.local")
    parser.add_argument("--ssh-user", default="yehia")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--api-key-env", default="TRUENAS_API_KEY")
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        metavar="APP",
        help="dump live app.config for this app (repeatable)",
    )
    args = parser.parse_args()

    api = build_api(
        transport=args.transport,
        host=args.host,
        ssh_user=args.ssh_user,
        api_url=args.api_url,
        api_key_env=args.api_key_env,
    )
    try:
        info = api.system_info()  # type: ignore[attr-defined]
        version = info.get("version") if isinstance(info, dict) else info
        print(f"[ok] connected via {api.name}: TrueNAS {version}")

        rows = api.app_query(_ALL_APPS, retrieve_config=False)  # type: ignore[attr-defined]
        installed = {r.get("name"): r.get("state") for r in rows}
        print("\n[apps] managed-app presence on host:")
        for name in _ALL_APPS:
            state = installed.get(name)
            mark = f"present ({state})" if name in installed else "absent"
            print(f"  - {name:<14} {mark}")

        for app in args.config:
            print(f"\n[config] app.config {app}:")
            cfg = api.app_config(app)  # type: ignore[attr-defined]
            print(json.dumps(cfg, indent=2, sort_keys=True))
    finally:
        api.close()  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    sys.exit(main())
