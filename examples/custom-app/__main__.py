"""Custom-app example: deploy an app from Docker Compose YAML on TrueNAS.

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

nas = truenas.Provider(
    "nas",
    host=cfg.get("host") or "nas.local",
    transport="jsonrpc",
    api_key=cfg.get_secret("apiKey"),
)

# A tiny "whoami" web service defined entirely as Compose YAML.
COMPOSE = """\
services:
  whoami:
    image: traefik/whoami:latest
    restart: unless-stopped
    ports:
      - 30080:80
    environment:
      TZ: UTC
"""

whoami = truenas.CustomApp(
    "whoami",
    truenas.CustomAppArgs(
        app_name="whoami",
        compose_yaml=COMPOSE,
        desired_state="RUNNING",
        adopt_existing=True,
    ),
    provider=nas,
)

pulumi.export("whoami_state", whoami.state)
