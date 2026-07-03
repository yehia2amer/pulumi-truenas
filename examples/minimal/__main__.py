"""Minimal example: install one catalog app on TrueNAS.

Run:
    uv sync
    pulumi config set host nas.local
    pulumi config set --secret apiKey <your-key>
    pulumi preview
    pulumi up
"""

from __future__ import annotations

import pulumi

import pulumi_truenas as truenas

cfg = pulumi.Config()

# One provider carries connection settings for all resources.
nas = truenas.Provider(
    "nas",
    host=cfg.get("host") or "nas.local",
    transport="jsonrpc",
    api_key=cfg.get_secret("apiKey"),
)

# Install FlareSolverr (a small, stateless catalog app).
flaresolverr = truenas.CatalogApp(
    "flaresolverr",
    truenas.CatalogAppArgs(
        app_name="flaresolverr",
        catalog_app="flaresolverr",
        train="community",
        values={
            "TZ": "UTC",
            "network": {"web_port": {"port_number": 8191}},
        },
        desired_state="RUNNING",
        adopt_existing=True,  # reconcile if it already exists
    ),
    provider=nas,
)

pulumi.export("flaresolverr_state", flaresolverr.state)
