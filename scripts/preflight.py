#!/usr/bin/env python
"""Read-only connectivity preflight against a live TrueNAS host.

Runs ONLY read methods (``system.info``, optionally ``app.query`` /
``app.config``) so it can never mutate anything. Use it to confirm connectivity
and auth for the chosen transport before running Pulumi.

Usage:
    python scripts/preflight.py --transport jsonrpc --host nas.local
    python scripts/preflight.py --transport midclt_ssh --host nas.local --ssh-user admin
    python scripts/preflight.py --host nas.local --app sonarr   # dump one config
"""

from __future__ import annotations

import argparse
import json
import sys

from pulumi_truenas.api import build_api


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", default="jsonrpc")
    parser.add_argument("--host", required=True)
    parser.add_argument("--ssh-user", default=None)
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--api-key-env", default="TRUENAS_API_KEY")
    parser.add_argument(
        "--app",
        action="append",
        default=[],
        metavar="NAME",
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

        for app in args.app:
            print(f"\n[config] app.config {app}:")
            print(json.dumps(api.app_config(app), indent=2, sort_keys=True))  # type: ignore[attr-defined]
    finally:
        api.close()  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    sys.exit(main())
