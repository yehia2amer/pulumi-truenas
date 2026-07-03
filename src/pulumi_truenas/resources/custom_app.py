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
    UpdateResult,
)

from pulumi_truenas import validation
from pulumi_truenas.config import ProviderSettings
from pulumi_truenas.provider import Provider, resolve_settings


def _stably_exists(api: Any, name: str, *, checks: int = 2, delay_s: float = 1.5) -> bool:
    """True only if the app is present on consecutive checks (delete race guard)."""
    for i in range(checks):
        if not api.app_exists(name):
            return False
        if i < checks - 1:
            time.sleep(delay_s)
    return True


class _CustomAppProvider(ResourceProvider):
    """Dynamic provider backing the CustomApp resource (Compose YAML)."""

    def _api(self, inputs: dict[str, Any]):
        return ProviderSettings.from_inputs(inputs).build()

    def check(self, _olds: dict[str, Any], news: dict[str, Any]) -> CheckResult:
        failures: list = []
        validation.check_connection(news, failures)
        validation.check_app_name(news, failures)
        validation.check_desired_state(news, failures)
        if not news.get("compose_yaml"):
            from pulumi.dynamic import CheckFailure

            failures.append(CheckFailure("compose_yaml", "'compose_yaml' is required"))
        return CheckResult(news, failures)

    def create(self, props: dict[str, Any]) -> CreateResult:
        inputs = props
        api = self._api(inputs)
        try:
            name = inputs["app_name"]
            if inputs.get("adopt_existing", True) and _stably_exists(api, name):
                api.app_update_custom(name, inputs["compose_yaml"])
            else:
                api.app_create_custom(app_name=name, compose_yaml=inputs["compose_yaml"])
            self._reconcile_power(api, name, inputs.get("desired_state"))
            state = self._read_state(api, inputs)
        finally:
            api.close()
        return CreateResult(id_=name, outs={**inputs, **state})

    def read(self, id_: str, props: dict[str, Any]) -> ReadResult:
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
        replaces: list[str] = []
        if old.get("app_name") != new.get("app_name"):
            replaces.append("app_name")
        changes = any(old.get(k) != new.get(k) for k in ("compose_yaml", "desired_state"))
        return DiffResult(
            changes=changes or bool(replaces),
            replaces=replaces,
            delete_before_replace=True,
        )

    def update(self, _id: str, _olds: dict[str, Any], _news: dict[str, Any]) -> UpdateResult:
        new = _news
        api = self._api(new)
        try:
            api.app_update_custom(_id, new["compose_yaml"])
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
                force_remove_custom_app=bool(state.get("force_remove_custom_app", False)),
            )
        finally:
            api.close()

    def _reconcile_power(self, api: Any, name: str, desired_state: str | None) -> None:
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
        row = api.app_get(inputs["app_name"], retrieve_config=False)
        if row is None:
            return {"_exists": False, "state": None}
        return {"_exists": True, "state": row.get("state")}


class CustomAppArgs:
    """Inputs for a CustomApp resource (resource-specific fields only)."""

    def __init__(
        self,
        *,
        app_name: pulumi.Input[str],
        compose_yaml: pulumi.Input[str],
        desired_state: pulumi.Input[str] | None = None,
        adopt_existing: bool = False,
        remove_images: bool = True,
        remove_ix_volumes: bool = False,
        force_remove_ix_volumes: bool = False,
        force_remove_custom_app: bool = False,
    ) -> None:
        self.app_name = app_name
        self.compose_yaml = compose_yaml
        self.desired_state = desired_state
        self.adopt_existing = adopt_existing
        self.remove_images = remove_images
        self.remove_ix_volumes = remove_ix_volumes
        self.force_remove_ix_volumes = force_remove_ix_volumes
        self.force_remove_custom_app = force_remove_custom_app


class CustomApp(Resource):
    """Manages a TrueNAS custom (Compose YAML) application."""

    state: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: CustomAppArgs,
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
        props = {"state": None, "_exists": None, **vars(args), **settings.to_inputs()}
        super().__init__(_CustomAppProvider(), name, props, opts)
