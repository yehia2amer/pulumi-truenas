# Resource reference

All resources accept connection settings via `provider=<Provider>` or the
individual connection kwargs (`host=`, `transport=`, `ssh_user=`, `api_url=`,
`api_key=`, `api_key_env=`, `verify_tls=`). Resource-specific inputs go in the
matching `*Args` object.

---

## `Provider`

Connection holder shared by resources.

```python
truenas.Provider(
    "nas",
    host="nas.local",             # required
    transport="jsonrpc",          # "jsonrpc" | "midclt_ssh"
    ssh_user=None,                # midclt_ssh only
    api_url=None,                 # defaults to wss://<host>/api/current
    api_key=None,                 # jsonrpc; pass a Pulumi secret
    api_key_env="TRUENAS_API_KEY",
    verify_tls=False,             # TrueNAS self-signed cert by default
    ca_cert=None,                # verify against a private CA bundle instead
    job_timeout_s=None,          # jsonrpc: max wait for a job (default ~1800s)
    poll_interval_s=None,        # jsonrpc: job status poll cadence
)
```

See [operations.md](operations.md) for concurrency, timeout, and TLS tuning.

---

## `CatalogApp`

Manages an official TrueNAS catalog application.

**Inputs (`CatalogAppArgs`)**

| Input | Type | Notes |
|-------|------|-------|
| `app_name` | str (required) | must match `^[a-z]([-a-z0-9]*[a-z0-9])?$`, ≤40 |
| `catalog_app` | str (required) | catalog item name |
| `train` | str (required) | e.g. `community`, `stable` |
| `values` | dict (required) | opaque, app/version-specific (see below) |
| `version` | str? | pin a version; change triggers `app.upgrade` |
| `desired_state` | `"RUNNING"`/`"STOPPED"`? | reconciled on create/update |
| `adopt_existing` | bool = False | reconcile in place if it already exists |
| `remove_images` | bool = True | on delete |
| `remove_ix_volumes` | bool = False | on delete (safety) |
| `force_remove_ix_volumes` | bool = False | on delete (safety) |

**Outputs:** `state`, `current_version`.

**Lifecycle:** create → `app.create` (or reconcile if adopting); update →
`app.update` (+ `app.upgrade` on version change); delete → `app.delete` (with
conservative volume defaults). Changing `app_name`/`catalog_app` replaces
(delete-before-replace).

```python
truenas.CatalogApp(
    "sonarr",
    truenas.CatalogAppArgs(
        app_name="sonarr", catalog_app="sonarr", train="community",
        values={"TZ": "UTC", "network": {"web_port": {"port_number": 30113}}},
        desired_state="RUNNING",
    ),
    provider=nas,
)
```

---

## `CustomApp`

Manages a custom app from Docker Compose YAML.

**Inputs (`CustomAppArgs`)**

| Input | Type | Notes |
|-------|------|-------|
| `app_name` | str (required) | app-name rules as above |
| `compose_yaml` | str (required) | Docker Compose config |
| `desired_state` | `"RUNNING"`/`"STOPPED"`? | |
| `adopt_existing` | bool = False | |
| `remove_images` | bool = True | on delete |
| `remove_ix_volumes` | bool = False | on delete |
| `force_remove_ix_volumes` | bool = False | on delete |
| `force_remove_custom_app` | bool = False | on delete |

**Outputs:** `state`.

---

## `Dataset`

Manages a ZFS dataset via `pool.dataset.*`.

**Inputs (`DatasetArgs`)**

| Input | Type | Notes |
|-------|------|-------|
| `name` | str (required) | pool-qualified path, e.g. `tank/media` |
| `comments` | str? | |
| `compression` | str? | e.g. `LZ4` |
| `recordsize` | str? | e.g. `1M` |
| `sync` | str? | `STANDARD`/`ALWAYS`/`DISABLED`/`INHERIT` |
| `atime` | str? | `ON`/`OFF`/`INHERIT` |
| `adopt_existing` | bool = False | |
| `allow_destroy` | bool = False | **delete is a no-op unless True** |
| `destroy_recursive` | bool = False | when destroying |
| `destroy_force` | bool = False | when destroying |

**Outputs:** `dataset_type`, `mountpoint`.

> Safety: `delete` never destroys the dataset unless `allow_destroy=True`.

---

## `Directory`

Ensures a host directory exists (SSH `mkdir`/`chown`/`chmod`). Uses the
`midclt_ssh`-style connection (needs SSH access to the host).

**Inputs (`DirectoryArgs`)**

| Input | Type | Notes |
|-------|------|-------|
| `path` | str (required) | absolute path |
| `owner` | int/str? | uid or name |
| `group` | int/str? | gid or name |
| `mode` | str? | octal, e.g. `"0775"` |

**Outputs:** `actual_owner`, `actual_group`, `actual_mode`.

> Safety: `delete` is a **no-op** — the directory (and any data) is never
> removed. Ownership/mode changes are applied only when they drift, with a
> `sudo -n` fallback.

---

## Discovering `values` for catalog apps

`values` schemas are per-app and per-version. This library passes them through
unchanged. To learn the schema for an app:

```bash
# on the NAS (or via ssh):
midclt call app.config <app_name>

# or with the bundled script:
python scripts/preflight.py --host nas.local --app <app_name>
```
