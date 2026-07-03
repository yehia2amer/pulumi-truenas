from __future__ import annotations

from typing import Any

from pulumi_truenas.resources.catalog_app import _CatalogAppProvider
from pulumi_truenas.resources.custom_app import _CustomAppProvider
from pulumi_truenas.resources.dataset import _DatasetProvider


class FakeAppApi:
    def __init__(self, exists: bool, state: str = "RUNNING") -> None:
        self._exists = exists
        self._state = state
        self.actions: list[tuple[str, tuple]] = []

    def app_exists(self, name: str) -> bool:
        return self._exists

    def app_get(self, name: str, retrieve_config: bool = False) -> Any:
        if not self._exists:
            return None
        return {"name": name, "state": self._state, "version": "1.0.0"}

    def app_update_values(self, name, values):
        self.actions.append(("update_values", (name, values)))
        self._exists = True

    def app_create_catalog(self, **kwargs):
        self.actions.append(("create_catalog", (kwargs["app_name"],)))
        self._exists = True

    def app_update_custom(self, name, yaml):
        self.actions.append(("update_custom", (name,)))
        self._exists = True

    def app_create_custom(self, **kwargs):
        self.actions.append(("create_custom", (kwargs["app_name"],)))
        self._exists = True

    def app_start(self, name):
        self.actions.append(("start", (name,)))
        self._state = "RUNNING"

    def app_stop(self, name):
        self.actions.append(("stop", (name,)))
        self._state = "STOPPED"

    def close(self):
        pass


def _catalog_inputs(**over):
    base = {
        "app_name": "sonarr",
        "catalog_app": "sonarr",
        "train": "community",
        "values": {"TZ": "Africa/Cairo"},
        "adopt_existing": True,
        "transport": "midclt_ssh",
        "host": "h",
    }
    base.update(over)
    return base


def test_catalog_adopt_when_exists():
    api = FakeAppApi(exists=True)
    prov = _CatalogAppProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    result = prov.create(_catalog_inputs())
    kinds = [a[0] for a in api.actions]
    assert "update_values" in kinds
    assert "create_catalog" not in kinds
    assert result.id == "sonarr"


def test_catalog_creates_when_absent():
    api = FakeAppApi(exists=False)
    prov = _CatalogAppProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    prov.create(_catalog_inputs())
    kinds = [a[0] for a in api.actions]
    assert "create_catalog" in kinds
    assert "update_values" not in kinds


def test_catalog_no_adopt_flag_forces_create():
    api = FakeAppApi(exists=True)
    prov = _CatalogAppProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    prov.create(_catalog_inputs(adopt_existing=False))
    kinds = [a[0] for a in api.actions]
    assert "create_catalog" in kinds


def test_catalog_desired_state_stopped_stops_running_app():
    api = FakeAppApi(exists=True, state="RUNNING")
    prov = _CatalogAppProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    prov.create(_catalog_inputs(desired_state="STOPPED"))
    assert ("stop", ("sonarr",)) in api.actions


def test_catalog_desired_state_running_starts_stopped_app():
    api = FakeAppApi(exists=True, state="STOPPED")
    prov = _CatalogAppProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    prov.create(_catalog_inputs(desired_state="RUNNING"))
    assert ("start", ("sonarr",)) in api.actions


def test_custom_adopt_when_exists():
    api = FakeAppApi(exists=True)
    prov = _CustomAppProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    prov.create(
        {
            "app_name": "configarr",
            "compose_yaml": "services: {}\n",
            "adopt_existing": True,
            "transport": "midclt_ssh",
            "host": "h",
        }
    )
    kinds = [a[0] for a in api.actions]
    assert "update_custom" in kinds
    assert "create_custom" not in kinds


# --- dataset provider safety ---
class FakeDatasetApi:
    def __init__(self, exists: bool) -> None:
        self._exists = exists
        self.actions: list[tuple[str, tuple]] = []

    def dataset_exists(self, name):
        return self._exists

    def dataset_get(self, name):
        return {"id": name, "type": "FILESYSTEM", "mountpoint": "/mnt/x"} if self._exists else None

    def dataset_create(self, name, props):
        self.actions.append(("create", (name,)))
        self._exists = True

    def dataset_update(self, name, props):
        self.actions.append(("update", (name,)))

    def dataset_delete(self, name, **kw):
        self.actions.append(("delete", (name,)))

    def close(self):
        pass


def _ds_inputs(**over):
    base = {"name": "tank/media", "adopt_existing": True, "transport": "midclt_ssh", "host": "h"}
    base.update(over)
    return base


def test_dataset_delete_is_noop_by_default():
    api = FakeDatasetApi(exists=True)
    prov = _DatasetProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    prov.delete("tank/media", _ds_inputs())
    assert api.actions == []  # nothing destroyed


def test_dataset_delete_when_allowed():
    api = FakeDatasetApi(exists=True)
    prov = _DatasetProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    prov.delete("tank/media", _ds_inputs(allow_destroy=True))
    assert ("delete", ("tank/media",)) in api.actions


def test_dataset_adopt_when_exists():
    api = FakeDatasetApi(exists=True)
    prov = _DatasetProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    prov.create(_ds_inputs(compression="LZ4"))
    kinds = [a[0] for a in api.actions]
    assert "update" in kinds
    assert "create" not in kinds


# --- check() input validation ---
def test_catalog_check_reports_failures():
    prov = _CatalogAppProvider()
    result = prov.check({}, {"transport": "bad", "host": "", "app_name": "BAD", "catalog_app": ""})
    props = {f.property for f in result.failures}
    assert "transport" in props
    assert "host" in props
    assert "app_name" in props
    assert "catalog_app" in props


def test_catalog_check_passes_valid():
    prov = _CatalogAppProvider()
    result = prov.check(
        {},
        {
            "transport": "jsonrpc",
            "host": "nas.local",
            "app_name": "sonarr",
            "catalog_app": "sonarr",
        },
    )
    assert result.failures == []


def test_custom_check_requires_compose():
    prov = _CustomAppProvider()
    result = prov.check({}, {"transport": "jsonrpc", "host": "h", "app_name": "configarr"})
    assert any(f.property == "compose_yaml" for f in result.failures)


def test_dataset_check_requires_pool_path():
    prov = _DatasetProvider()
    result = prov.check({}, {"transport": "jsonrpc", "host": "h", "name": "nopool"})
    assert any(f.property == "name" for f in result.failures)


# --- read() import behavior ---
def test_catalog_read_without_host_is_import_safe():
    prov = _CatalogAppProvider()
    result = prov.read("sonarr", {})  # no connection settings (import case)
    outs = dict(result.outs or {})
    assert outs["app_name"] == "sonarr"


def test_catalog_read_with_host_queries_api():
    api = FakeAppApi(exists=True, state="RUNNING")
    prov = _CatalogAppProvider()
    prov._api = lambda inputs: api  # type: ignore[method-assign]
    result = prov.read("sonarr", {"host": "nas.local", "app_name": "sonarr"})
    outs = dict(result.outs or {})
    assert outs["app_name"] == "sonarr"
    assert outs["state"] == "RUNNING"
