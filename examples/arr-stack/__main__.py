"""Pulumi program: provision the TrueNAS ARR stack.

Order:
  1. Ensure TRaSH + Configarr appdata directories (Directory resources).
  2. Create catalog apps (qBittorrent, Sonarr, Radarr, Prowlarr, FlareSolverr).
  3. Create the Configarr custom app.

Apps depend on their host directories so mounts resolve on first start.
"""

from __future__ import annotations

import app_values
import pulumi
import stack
from config import load_provider

from pulumi_truenas.resources import (
    CatalogApp,
    CatalogAppArgs,
    CustomApp,
    CustomAppArgs,
    Directory,
    DirectoryArgs,
)

provider = load_provider()

# This example manages a stack that already exists on the host, so we adopt
# existing resources on first apply instead of failing.
ADOPT = True

# --- Phase D: directories -------------------------------------------------
directories: list[Directory] = []
for path in stack.TRASH_DIRECTORIES:
    safe = path.strip("/").replace("/", "-")
    directories.append(
        Directory(
            f"dir-{safe}",
            DirectoryArgs(
                path=path,
                owner=stack.UID,
                group=stack.GID,
                mode="0775",
            ),
            provider=provider,
        )
    )

dir_dep = pulumi.ResourceOptions(depends_on=directories)

# --- Phase B / E: catalog apps -------------------------------------------
catalog_apps: dict[str, CatalogApp] = {}

for spec in stack.CATALOG_APPS:
    if spec.catalog_app == "qbittorrent":
        values = app_values.qbittorrent_values(
            tz=stack.TZ,
            web_port=spec.web_port,
            bt_port=spec.bt_port or 51413,
            host_path=spec.host_path or "",
            container_path=spec.container_path or "",
            uid=stack.UID,
            gid=stack.GID,
        )
    else:
        values = app_values.servarr_values(
            tz=stack.TZ,
            web_port=spec.web_port,
            host_path=spec.host_path or "",
            container_path=spec.container_path or "",
            uid=stack.UID,
            gid=stack.GID,
            instance_name=spec.instance_name,
        )
    catalog_apps[spec.resource_name] = CatalogApp(
        spec.resource_name,
        CatalogAppArgs(
            app_name=spec.app_name,
            catalog_app=spec.catalog_app,
            train=stack.TRAIN,
            values=values,
            desired_state="RUNNING",
            adopt_existing=ADOPT,
        ),
        provider=provider,
        opts=dir_dep,
    )

# FlareSolverr (stateless; first DR recreate target).
flaresolverr = CatalogApp(
    stack.FLARESOLVERR.resource_name,
    CatalogAppArgs(
        app_name=stack.FLARESOLVERR.app_name,
        catalog_app=stack.FLARESOLVERR.catalog_app,
        train=stack.TRAIN,
        values=app_values.flaresolverr_values(
            tz=stack.TZ,
            web_port=stack.FLARESOLVERR.web_port,
        ),
        desired_state="RUNNING",
        adopt_existing=ADOPT,
    ),
    provider=provider,
    opts=dir_dep,
)
catalog_apps["flaresolverr"] = flaresolverr

# --- Phase C: Configarr custom app ---------------------------------------
configarr = CustomApp(
    stack.CONFIGARR.resource_name,
    CustomAppArgs(
        app_name=stack.CONFIGARR.app_name,
        compose_yaml=stack.CONFIGARR.compose_yaml(),
        desired_state="RUNNING",
        adopt_existing=ADOPT,
    ),
    provider=provider,
    opts=dir_dep,
)

# --- Outputs --------------------------------------------------------------
pulumi.export("transport", provider.settings.transport)
pulumi.export("host", provider.settings.host)
pulumi.export(
    "apps",
    {name: app.state for name, app in catalog_apps.items()} | {"configarr": configarr.state},
)
pulumi.export("directories", [d.path for d in directories])
