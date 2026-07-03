from __future__ import annotations

import app_values
import stack


def test_qbittorrent_values_ports_and_mount():
    v = app_values.qbittorrent_values(
        tz="Africa/Cairo",
        web_port=30024,
        bt_port=51413,
        host_path="/mnt/AmerData/Media/torrents",
        container_path="/data/torrents",
        uid=568,
        gid=568,
    )
    assert v["TZ"] == "Africa/Cairo"
    assert v["network"]["web_port"]["port_number"] == 30024
    assert v["network"]["bt_port"]["port_number"] == 51413
    assert v["run_as"] == {"user": 568, "group": 568}
    downloads = v["storage"]["downloads"]
    assert downloads["mount_path"] == "/data/torrents"
    assert downloads["host_path_config"]["path"] == "/mnt/AmerData/Media/torrents"
    assert v["resources"]["limits"]["cpus"] == 2


def test_servarr_values_additional_storage():
    v = app_values.servarr_values(
        tz="Africa/Cairo",
        web_port=30113,
        host_path="/mnt/AmerData/Media",
        container_path="/data",
        uid=568,
        gid=568,
    )
    assert v["network"]["web_port"]["port_number"] == 30113
    add = v["storage"]["additional_storage"]
    assert add and add[0]["mount_path"] == "/data"
    assert add[0]["read_only"] is False


def test_prowlarr_has_no_media_mount():
    v = app_values.servarr_values(
        tz="Africa/Cairo", web_port=30050, host_path="", container_path="", uid=568, gid=568
    )
    assert v["storage"]["additional_storage"] == []


def test_flaresolverr_values_defaults():
    v = app_values.flaresolverr_values(tz="Africa/Cairo", web_port=8191)
    assert v["network"]["web_port"]["port_number"] == 8191
    assert v["flaresolverr"]["log_level"] == "info"
    assert v["flaresolverr"]["log_html"] is False
    assert v["flaresolverr"]["captcha_solver"] == ""


def test_configarr_compose_yaml_has_mounts_and_env():
    yaml = stack.CONFIGARR.compose_yaml()
    assert "ghcr.io/raydak-labs/configarr:latest" in yaml
    assert 'user: "568:568"' in yaml
    assert "/mnt/AmerData/appdata/configarr/config:/app/config" in yaml
    assert "/mnt/AmerData/appdata/configarr/templates:/app/templates" in yaml
    assert 'CONFIG_LOCATION: "/app/config/config.yml"' in yaml
    assert 'CONFIGARR_INTERVAL_SECONDS: "86400"' in yaml


def test_configarr_compose_is_valid_yaml():
    import yaml as pyyaml

    parsed = pyyaml.safe_load(stack.CONFIGARR.compose_yaml())
    assert "services" in parsed
    svc = parsed["services"]["configarr"]
    assert svc["image"] == "ghcr.io/raydak-labs/configarr:latest"
    assert len(svc["volumes"]) == 4


def test_trash_directories_cover_plan():
    dirs = set(stack.TRASH_DIRECTORIES)
    assert "/mnt/AmerData/Media/torrents/incomplete" in dirs
    assert "/mnt/AmerData/Media/media/tv" in dirs
    assert "/mnt/AmerData/appdata/configarr/config" in dirs
    assert "/mnt/AmerData/backups/arr-stack" in dirs
    assert len(dirs) == 14


def test_catalog_app_specs_ports():
    ports = {s.app_name: s.web_port for s in stack.CATALOG_APPS}
    assert ports == {
        "qbittorrent": 30024,
        "sonarr": 30113,
        "radarr": 30025,
        "prowlarr": 30050,
        "bazarr": 30046,
        "seerr": 30357,
    }


def test_bazarr_has_media_mount_seerr_does_not():
    by_name = {s.app_name: s for s in stack.CATALOG_APPS}
    assert by_name["bazarr"].host_path == stack.MEDIA_ROOT
    assert by_name["bazarr"].container_path == "/data"
    assert by_name["seerr"].host_path is None


def test_only_sonarr_radarr_have_instance_name():
    named = {s.app_name for s in stack.CATALOG_APPS if s.instance_name}
    assert named == {"sonarr", "radarr"}
