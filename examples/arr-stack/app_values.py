"""Builders for TrueNAS catalog app ``values`` payloads.

The catalog apps published by iXsystems share a common values schema layout
(network / storage / resources / run_as). These builders produce the values
dict passed to ``app.create`` / ``app.update``.

Schema verified against a live TrueNAS 25.10.3.1 host via ``app.config``:
ports are objects (``{bind_mode, host_ips, port_number}``), qBittorrent uses
``network.bt_port``, host_path mounts carry ``read_only``, and resources use
``limits`` (cpus/memory). Re-run ``scripts/preflight.py --config <app>`` if the
installed app version changes.
"""

from __future__ import annotations

from typing import Any

# Default compute limits observed on the live host. Adjust per app as needed.
DEFAULT_LIMITS = {"cpus": 2, "memory": 4096}


def _run_as(uid: int, gid: int) -> dict[str, Any]:
    return {"user": uid, "group": gid}


def _port(port_number: int, *, bind_mode: str = "published") -> dict[str, Any]:
    return {"bind_mode": bind_mode, "host_ips": [], "port_number": port_number}


def _resources(limits: dict[str, Any] | None) -> dict[str, Any]:
    return {"limits": dict(limits)} if limits else {}


def _ix_volume(dataset_name: str) -> dict[str, Any]:
    return {
        "type": "ix_volume",
        "ix_volume_config": {"acl_enable": False, "dataset_name": dataset_name},
    }


def _host_path_volume(
    host_path: str, mount_path: str, *, read_only: bool | None = None
) -> dict[str, Any]:
    vol: dict[str, Any] = {
        "type": "host_path",
        "mount_path": mount_path,
        "host_path_config": {"acl_enable": False, "path": host_path},
    }
    if read_only is not None:
        vol["read_only"] = read_only
    return vol


def qbittorrent_values(
    *,
    tz: str,
    web_port: int,
    bt_port: int,
    host_path: str,
    container_path: str,
    uid: int,
    gid: int,
    limits: dict[str, Any] | None = DEFAULT_LIMITS,
) -> dict[str, Any]:
    return {
        "TZ": tz,
        "qbittorrent": {"additional_envs": []},
        "network": {
            "host_network": False,
            "networks": [],
            "use_https_probe": False,
            "web_port": _port(web_port),
            "bt_port": _port(bt_port),
        },
        "storage": {
            "config": _ix_volume("config"),
            "downloads": _host_path_volume(host_path, container_path),
            "additional_storage": [],
        },
        "run_as": _run_as(uid, gid),
        "resources": _resources(limits),
    }


def servarr_values(
    *,
    tz: str,
    web_port: int,
    host_path: str,
    container_path: str,
    uid: int,
    gid: int,
    instance_name: str | None = None,
    limits: dict[str, Any] | None = DEFAULT_LIMITS,
) -> dict[str, Any]:
    """Shared values for Sonarr / Radarr / Prowlarr style apps."""
    app_block: dict[str, Any] = {"additional_envs": []}
    if instance_name:
        app_block["instance_name"] = instance_name
    values: dict[str, Any] = {
        "TZ": tz,
        "network": {"host_network": False, "networks": [], "web_port": _port(web_port)},
        "storage": {
            "config": _ix_volume("config"),
            "additional_storage": [],
        },
        "run_as": _run_as(uid, gid),
        "resources": _resources(limits),
    }
    if host_path and container_path:
        values["storage"]["additional_storage"] = [
            _host_path_volume(host_path, container_path, read_only=False),
        ]
    return values


def flaresolverr_values(
    *,
    tz: str,
    web_port: int,
    log_level: str = "info",
    log_html: bool = False,
    captcha_solver: str = "",
    limits: dict[str, Any] | None = DEFAULT_LIMITS,
) -> dict[str, Any]:
    return {
        "TZ": tz,
        "network": {"networks": [], "web_port": _port(web_port)},
        "flaresolverr": {
            "additional_envs": [],
            "log_level": log_level,
            "log_html": log_html,
            "captcha_solver": captcha_solver,
        },
        "storage": {"data": _ix_volume("data"), "additional_storage": []},
        "resources": _resources(limits),
    }
