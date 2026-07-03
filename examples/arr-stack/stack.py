"""Desired-state definitions for the ARR stack (from the provider plan)."""

from __future__ import annotations

from dataclasses import dataclass, field

# Global defaults derived from the plan (section 7 / 8).
TZ = "Africa/Cairo"
TRAIN = "community"
UID = 568
GID = 568

MEDIA_ROOT = "/mnt/AmerData/Media"
APPDATA_ROOT = "/mnt/AmerData/appdata"
BACKUPS_ROOT = "/mnt/AmerData/backups"

# TRaSH-compatible directory layout (single media dataset -> hardlinks work).
TRASH_DIRECTORIES: list[str] = [
    f"{MEDIA_ROOT}/torrents/incomplete",
    f"{MEDIA_ROOT}/torrents/movies",
    f"{MEDIA_ROOT}/torrents/tv",
    f"{MEDIA_ROOT}/torrents/music",
    f"{MEDIA_ROOT}/torrents/books",
    f"{MEDIA_ROOT}/media/movies",
    f"{MEDIA_ROOT}/media/tv",
    f"{MEDIA_ROOT}/media/music",
    f"{MEDIA_ROOT}/media/books",
    f"{APPDATA_ROOT}/configarr/config",
    f"{APPDATA_ROOT}/configarr/repos",
    f"{APPDATA_ROOT}/configarr/cfs",
    f"{APPDATA_ROOT}/configarr/templates",
    f"{BACKUPS_ROOT}/arr-stack",
]


@dataclass(frozen=True)
class CatalogAppSpec:
    resource_name: str
    app_name: str
    catalog_app: str
    web_port: int
    bt_port: int | None = None
    host_path: str | None = None
    container_path: str | None = None
    # Only Sonarr/Radarr-style apps expose an instance_name field.
    instance_name: str | None = None


CATALOG_APPS: list[CatalogAppSpec] = [
    CatalogAppSpec(
        resource_name="qbittorrent",
        app_name="qbittorrent",
        catalog_app="qbittorrent",
        web_port=30024,
        bt_port=51413,
        host_path=f"{MEDIA_ROOT}/torrents",
        container_path="/data/torrents",
    ),
    CatalogAppSpec(
        resource_name="sonarr",
        app_name="sonarr",
        catalog_app="sonarr",
        web_port=30113,
        host_path=MEDIA_ROOT,
        container_path="/data",
        instance_name="Sonarr",
    ),
    CatalogAppSpec(
        resource_name="radarr",
        app_name="radarr",
        catalog_app="radarr",
        web_port=30025,
        host_path=MEDIA_ROOT,
        container_path="/data",
        instance_name="Radarr",
    ),
    CatalogAppSpec(
        resource_name="prowlarr",
        app_name="prowlarr",
        catalog_app="prowlarr",
        web_port=30050,
    ),
    CatalogAppSpec(
        # Subtitle manager: needs the media library mounted to sit beside video.
        resource_name="bazarr",
        app_name="bazarr",
        catalog_app="bazarr",
        web_port=30046,
        host_path=MEDIA_ROOT,
        container_path="/data",
    ),
    CatalogAppSpec(
        # Request frontend (Jellyseerr/Overseerr-style): no media mount needed.
        resource_name="seerr",
        app_name="seerr",
        catalog_app="seerr",
        web_port=30357,
    ),
]

FLARESOLVERR = CatalogAppSpec(
    resource_name="flaresolverr",
    app_name="flaresolverr",
    catalog_app="flaresolverr",
    web_port=8191,
)


@dataclass(frozen=True)
class ConfigarrSpec:
    resource_name: str = "configarr"
    app_name: str = "configarr"
    image: str = "ghcr.io/raydak-labs/configarr:latest"
    uid: int = UID
    gid: int = GID
    interval_seconds: int = 86400
    mounts: dict[str, str] = field(
        default_factory=lambda: {
            f"{APPDATA_ROOT}/configarr/config": "/app/config",
            f"{APPDATA_ROOT}/configarr/repos": "/app/repos",
            f"{APPDATA_ROOT}/configarr/cfs": "/app/cfs",
            f"{APPDATA_ROOT}/configarr/templates": "/app/templates",
        }
    )

    def compose_yaml(self) -> str:
        lines = [
            "services:",
            "  configarr:",
            f"    image: {self.image}",
            f'    user: "{self.uid}:{self.gid}"',
            "    restart: unless-stopped",
            "    environment:",
        ]
        env = {
            "TZ": TZ,
            "DRY_RUN": "false",
            "CONFIG_LOCATION": "/app/config/config.yml",
            "SECRETS_LOCATION": "/app/config/secrets.yml",
            "CUSTOM_REPO_ROOT": "/app/repos",
            "CONFIGARR_INTERVAL_SECONDS": str(self.interval_seconds),
        }
        lines += [f'      {k}: "{v}"' for k, v in env.items()]
        lines.append("    volumes:")
        lines += [f"      - {host}:{container}" for host, container in self.mounts.items()]
        return "\n".join(lines) + "\n"


CONFIGARR = ConfigarrSpec()
