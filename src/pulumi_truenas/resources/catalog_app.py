from __future__ import annotations

import time
from typing import Any

import pulumi
from pulumi.dynamic import (
    CheckResult,
    CreateResult,
    DiffResult,
    ReadResult,
    Resource,
    ResourceProvider,
)

from pulumi_truenas import validation
from pulumi_truenas.config import ProviderSettings
from pulumi_truenas.provider import Provider, resolve_settings


def _stably_exists(api: Any, name: str, *, checks: int = 2, delay_s: float = 1.5) -> bool:
    """True only if the app is present on consecutive checks.

    Guards against the delete-before-replace race: during a replace, the app
    may still linger for a moment after the delete job. Requiring the app to be
    present across a short window avoids adopting an app that is mid-deletion.
    """
    for i in range(checks):
        if not api.app_exists(name):
            return False
        if i < checks - 1:
            time.sleep(delay_s)
    return True


class _CatalogAppProvider(ResourceProvider):
    """Dynamic provider backing the CatalogApp resource.

    Runs out-of-process during ``pulumi up``; rebuilds the TrueNAS API from
    the serialized provider settings in each set of inputs.
    """

    def _api(self, inputs: dict[str, Any]):
        return ProviderSettings.from_inputs(inputs).build()

    def check(self, _olds: dict[str, Any], news: dict[str, Any]) -> CheckResult:
        failures: list = []
        validation.check_connection(news, failures)
        validation.check_app_name(news, failures)
        validation.check_desired_state(news, failures)
        if not news.get("catalog_app"):
            from pulumi.dynamic import CheckFailure

            failures.append(CheckFailure("catalog_app", "'catalog_app' is required"))
        return CheckResult(news, failures)

    def create(self, props: dict[str, Any]) -> CreateResult:
        inputs = props
        api = self._api(inputs)
        try:
            name = inputs["app_name"]
            if inputs.get("adopt_existing", True) and _stably_exists(api, name):
                # Adopt-on-create: the app already exists on the host, so
                # reconcile its values in place instead of failing.
                api.app_update_values(name, inputs.get("values") or {})
            else:
                api.app_create_catalog(
                    app_name=name,
                    catalog_app=inputs["catalog_app"],
                    train=inputs["train"],
                    values=inputs.get("values") or {},
                    version=inputs.get("version"),
                )
            self._reconcile_power(api, name, inputs.get("desired_state"))
            state = self._read_state(api, inputs)
        finally:
            api.close()
        return CreateResult(id_=name, outs={**inputs, **state})

    def read(self, id_: str, props: dict[str, Any]) -> ReadResult:
        # `pulumi import` calls read with the id and (often) no connection
        # settings. If we can't reach the API, return the id-derived state so
        # the user can fill inputs in code and re-run.
        state = props
        if not state.get("host"):
            return ReadResult(id_=id_, outs={**state, "app_name": id_})
        api = self._api(state)
        try:
            fresh = self._read_state(api, state)
        finally:
            api.close()
        return ReadResult(id_=id_, outs={**state, "app_name": id_, **fresh})

    def diff(self, _id: str, _olds: dict[str, Any], _news: dict[str, Any]) -> DiffResult:
        old, new = _olds, _news
        # app_name and catalog_app changes require replacement.
        replaces = [k for k in ("app_name", "catalog_app") if old.get(k) != new.get(k)]
        # train / version / desired_state + structured values diff (in place).
        detailed = [k for k in ("train", "version", "desired_state") if old.get(k) != new.get(k)]
        detailed += [
            f"values.{k}"
            for k in validation.changed_keys(old.get("values") or {}, new.get("values") or {})
        ]
        return DiffResult(
            changes=bool(detailed) or bool(replaces),
            replaces=replaces,
            delete_before_replace=True,
        )

    def update(self, _id: str, _olds: dict[str, Any], _news: dict[str, Any]):
        from pulumi.dynamic import UpdateResult

        old, new = _olds, _news
        api = self._api(new)
        try:
            version_changed = old.get("version") != new.get("version") and new.get("version")
            if version_changed:
                api.app_upgrade(_id, new.get("version"))
            # Always reconcile values (also picks up train changes via values).
            api.app_update_values(_id, new.get("values") or {})
            self._reconcile_power(api, _id, new.get("desired_state"))
            state = self._read_state(api, new)
        finally:
            api.close()
        return UpdateResult(outs={**new, **state})

    def delete(self, _id: str, _props: dict[str, Any]) -> None:
        state = _props
        api = self._api(state)
        try:
            api.app_delete(
                _id,
                remove_images=bool(state.get("remove_images", True)),
                remove_ix_volumes=bool(state.get("remove_ix_volumes", False)),
                force_remove_ix_volumes=bool(state.get("force_remove_ix_volumes", False)),
            )
        finally:
            api.close()

    # --- helpers ---
    def _reconcile_power(self, api: Any, name: str, desired_state: object) -> None:
        """Start/stop the app to match desired_state (RUNNING/STOPPED)."""
        if not desired_state:
            return
        target = str(desired_state).upper()
        row = api.app_get(name, retrieve_config=False)
        current = (row or {}).get("state")
        if target == "RUNNING" and current != "RUNNING":
            api.app_start(name)
        elif target == "STOPPED" and current not in {"STOPPED", "CRASHED"}:
            api.app_stop(name)

    def _read_state(self, api: Any, inputs: dict[str, Any]) -> dict[str, Any]:
        name = inputs["app_name"]
        row = api.app_get(name, retrieve_config=False)
        if row is None:
            return {"_exists": False, "state": None, "current_version": None}
        return {
            "_exists": True,
            "state": row.get("state"),
            "current_version": row.get("version"),
        }


class CatalogAppArgs:
    """Inputs for a CatalogApp resource (resource-specific fields only).

    Connection settings are supplied via ``provider=`` (or connection kwargs)
    on the :class:`CatalogApp` constructor, not here.
    """

    def __init__(
        self,
        *,
        app_name: pulumi.Input[str],
        catalog_app: pulumi.Input[str],
        train: pulumi.Input[str],
        values: pulumi.Input[dict[str, Any]],
        version: pulumi.Input[str] | None = None,
        desired_state: pulumi.Input[str] | None = None,
        adopt_existing: bool = False,
        remove_images: bool = True,
        remove_ix_volumes: bool = False,
        force_remove_ix_volumes: bool = False,
    ) -> None:
        self.app_name = app_name
        self.catalog_app = catalog_app
        self.train = train
        self.values = values
        self.version = version
        self.desired_state = desired_state
        self.adopt_existing = adopt_existing
        self.remove_images = remove_images
        self.remove_ix_volumes = remove_ix_volumes
        self.force_remove_ix_volumes = force_remove_ix_volumes


class CatalogApp(Resource):
    """Manages an official TrueNAS catalog application."""

    state: pulumi.Output[str]
    current_version: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: CatalogAppArgs,
        *,
        provider: Provider | None = None,
        host: str | None = None,
        transport: str | None = None,
        ssh_user: str | None = None,
        api_url: str | None = None,
        api_key: object | None = None,
        api_key_env: str | None = None,
        verify_tls: bool | None = None,
        ca_cert: str | None = None,
        job_timeout_s: float | None = None,
        poll_interval_s: float | None = None,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        settings = resolve_settings(
            provider,
            host=host,
            transport=transport,
            ssh_user=ssh_user,
            api_url=api_url,
            api_key=api_key,
            api_key_env=api_key_env,
            verify_tls=verify_tls,
            ca_cert=ca_cert,
            job_timeout_s=job_timeout_s,
            poll_interval_s=poll_interval_s,
        )
        props = {
            "state": None,
            "current_version": None,
            "_exists": None,
            **vars(args),
            **settings.to_inputs(),
        }
        super().__init__(_CatalogAppProvider(), name, props, opts)
