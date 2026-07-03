from __future__ import annotations

from typing import Any


class TrueNasOperationsMixin:
    """High-level TrueNAS middleware operations.

    Requires the host class to implement ``call(method, *params)`` and
    ``job(method, *params)``. All app/catalog semantics live here so the
    JSON-RPC and midclt/ssh adapters behave identically.
    """

    # --- provided by the concrete adapter ---
    def call(self, method: str, *params: object) -> object:  # pragma: no cover
        raise NotImplementedError

    def job(self, method: str, *params: object) -> object:  # pragma: no cover
        raise NotImplementedError

    # --- system ---
    def system_info(self) -> Any:
        return self.call("system.info")

    # --- catalog ---
    def catalog_app_details(self, catalog_app: str, train: str) -> Any:
        return self.call("catalog.get_app_details", catalog_app, {"train": train})

    # --- app read ---
    def app_query(self, names: list[str], retrieve_config: bool = False) -> list[Any]:
        filters = [["name", "in", names]]
        options = {"extra": {"retrieve_config": retrieve_config}}
        result = self.call("app.query", filters, options)
        return result if isinstance(result, list) else []

    def app_get(self, name: str, retrieve_config: bool = True) -> Any | None:
        rows = self.app_query([name], retrieve_config=retrieve_config)
        return rows[0] if rows else None

    def app_config(self, name: str) -> Any:
        return self.call("app.config", name)

    def app_exists(self, name: str) -> bool:
        return self.app_get(name, retrieve_config=False) is not None

    # --- catalog app lifecycle ---
    def app_create_catalog(
        self,
        *,
        app_name: str,
        catalog_app: str,
        train: str,
        values: dict[str, Any],
        version: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "custom_app": False,
            "app_name": app_name,
            "catalog_app": catalog_app,
            "train": train,
            "values": values,
        }
        if version is not None:
            payload["version"] = version
        return self.job("app.create", payload)

    def app_create_custom(self, *, app_name: str, compose_yaml: str) -> Any:
        payload: dict[str, Any] = {
            "custom_app": True,
            "app_name": app_name,
            "custom_compose_config_string": compose_yaml,
        }
        return self.job("app.create", payload)

    def app_update_values(self, name: str, values: dict[str, Any]) -> Any:
        return self.job("app.update", name, {"values": values})

    def app_update_custom(self, name: str, compose_yaml: str) -> Any:
        return self.job("app.update", name, {"custom_compose_config_string": compose_yaml})

    def app_upgrade(self, name: str, version: str | None = None) -> Any:
        options: dict[str, Any] = {}
        if version is not None:
            options["app_version"] = version
        return self.job("app.upgrade", name, options)

    def app_delete(
        self,
        name: str,
        *,
        remove_images: bool = True,
        remove_ix_volumes: bool = False,
        force_remove_ix_volumes: bool = False,
        force_remove_custom_app: bool = False,
    ) -> Any:
        options = {
            "remove_images": remove_images,
            "remove_ix_volumes": remove_ix_volumes,
            "force_remove_ix_volumes": force_remove_ix_volumes,
            "force_remove_custom_app": force_remove_custom_app,
        }
        return self.job("app.delete", name, options)

    def app_start(self, name: str) -> Any:
        return self.call("app.start", name)

    def app_stop(self, name: str) -> Any:
        return self.call("app.stop", name)

    # --- ZFS datasets ---
    def dataset_get(self, dataset_id: str) -> Any | None:
        rows = self.call("pool.dataset.query", [["id", "=", dataset_id]])
        return rows[0] if isinstance(rows, list) and rows else None

    def dataset_exists(self, dataset_id: str) -> bool:
        return self.dataset_get(dataset_id) is not None

    def dataset_create(self, name: str, properties: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {"name": name}
        if properties:
            payload.update(properties)
        return self.call("pool.dataset.create", payload)

    def dataset_update(self, dataset_id: str, properties: dict[str, Any]) -> Any:
        return self.call("pool.dataset.update", dataset_id, properties)

    def dataset_delete(
        self, dataset_id: str, *, recursive: bool = False, force: bool = False
    ) -> Any:
        return self.call(
            "pool.dataset.delete", dataset_id, {"recursive": recursive, "force": force}
        )
