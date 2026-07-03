from __future__ import annotations

from typing import Any

import pulumi
from pulumi.dynamic import (
    CheckFailure,
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

# Properties we manage/diff on a dataset. Everything else ZFS reports is
# read-only context and ignored for drift purposes.
_MANAGED_PROPS = ("comments", "compression", "recordsize", "sync", "atime")


class _DatasetProvider(ResourceProvider):
    """Dynamic provider backing the Dataset (ZFS) resource.

    Conservative by design: ``delete`` is a **no-op** by default so a Pulumi
    destroy can never wipe a dataset that holds media/appdata. Set
    ``allow_destroy=True`` on the resource to opt into real destruction.
    """

    def _api(self, inputs: dict[str, Any]):
        return ProviderSettings.from_inputs(inputs).build()

    def check(self, _olds: dict[str, Any], news: dict[str, Any]) -> CheckResult:
        failures: list = []
        validation.check_connection(news, failures)
        name = news.get("name")
        if not name or not isinstance(name, str):
            failures.append(CheckFailure("name", "'name' (dataset path) is required"))
        elif "/" not in name:
            failures.append(
                CheckFailure(
                    "name",
                    "dataset 'name' must be a pool-qualified path, e.g. 'tank/media'",
                )
            )
        return CheckResult(news, failures)

    def _properties(self, inputs: dict[str, Any]) -> dict[str, Any]:
        props: dict[str, Any] = {}
        for key in _MANAGED_PROPS:
            value = inputs.get(key)
            if value is not None:
                props[key] = value
        return props

    def create(self, props: dict[str, Any]) -> CreateResult:
        inputs = props
        api = self._api(inputs)
        try:
            name = inputs["name"]
            if inputs.get("adopt_existing", True) and api.dataset_exists(name):
                update = self._properties(inputs)
                if update:
                    api.dataset_update(name, update)
            else:
                api.dataset_create(name, self._properties(inputs))
            state = self._read_state(api, inputs)
        finally:
            api.close()
        return CreateResult(id_=inputs["name"], outs={**inputs, **state})

    def read(self, id_: str, props: dict[str, Any]) -> ReadResult:
        state = props
        if not state.get("host"):
            return ReadResult(id_=id_, outs={**state, "name": id_})
        api = self._api(state)
        try:
            fresh = self._read_state(api, state)
        finally:
            api.close()
        return ReadResult(id_=id_, outs={**state, "name": id_, **fresh})

    def diff(self, _id: str, _olds: dict[str, Any], _news: dict[str, Any]) -> DiffResult:
        old, new = _olds, _news
        replaces = ["name"] if old.get("name") != new.get("name") else []
        changes = any(old.get(k) != new.get(k) for k in _MANAGED_PROPS)
        return DiffResult(changes=changes or bool(replaces), replaces=replaces)

    def update(self, _id: str, _olds: dict[str, Any], _news: dict[str, Any]) -> UpdateResult:
        api = self._api(_news)
        try:
            update = self._properties(_news)
            if update:
                api.dataset_update(_id, update)
            state = self._read_state(api, _news)
        finally:
            api.close()
        return UpdateResult(outs={**_news, **state})

    def delete(self, _id: str, _props: dict[str, Any]) -> None:
        state = _props
        if not state.get("allow_destroy", False):
            # Safety default: never destroy a dataset on Pulumi delete.
            return
        api = self._api(state)
        try:
            api.dataset_delete(
                _id,
                recursive=bool(state.get("destroy_recursive", False)),
                force=bool(state.get("destroy_force", False)),
            )
        finally:
            api.close()

    def _read_state(self, api: Any, inputs: dict[str, Any]) -> dict[str, Any]:
        row = api.dataset_get(inputs["name"])
        if row is None:
            return {"_exists": False, "dataset_type": None, "mountpoint": None}
        return {
            "_exists": True,
            "dataset_type": row.get("type"),
            "mountpoint": (row.get("mountpoint") or {}).get("value")
            if isinstance(row.get("mountpoint"), dict)
            else row.get("mountpoint"),
        }


class DatasetArgs:
    """Inputs for a Dataset (ZFS) resource (resource-specific fields only)."""

    def __init__(
        self,
        *,
        name: pulumi.Input[str],
        comments: pulumi.Input[str] | None = None,
        compression: pulumi.Input[str] | None = None,
        recordsize: pulumi.Input[str] | None = None,
        sync: pulumi.Input[str] | None = None,
        atime: pulumi.Input[str] | None = None,
        adopt_existing: bool = False,
        allow_destroy: bool = False,
        destroy_recursive: bool = False,
        destroy_force: bool = False,
    ) -> None:
        self.name = name
        self.comments = comments
        self.compression = compression
        self.recordsize = recordsize
        self.sync = sync
        self.atime = atime
        self.adopt_existing = adopt_existing
        self.allow_destroy = allow_destroy
        self.destroy_recursive = destroy_recursive
        self.destroy_force = destroy_force


class Dataset(Resource):
    """Manages a ZFS dataset on TrueNAS (create/update; safe delete)."""

    dataset_type: pulumi.Output[str]
    mountpoint: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: DatasetArgs,
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
            "dataset_type": None,
            "mountpoint": None,
            "_exists": None,
            **vars(args),
            **settings.to_inputs(),
        }
        super().__init__(_DatasetProvider(), name, props, opts)
