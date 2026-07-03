# pulumi-truenas

[![CI](https://github.com/yehia2amer/pulumi-truenas/actions/workflows/ci.yml/badge.svg)](https://github.com/yehia2amer/pulumi-truenas/actions/workflows/ci.yml)

A [Pulumi](https://www.pulumi.com/) component library for managing
[TrueNAS](https://www.truenas.com/) **apps** and supporting **filesystem
resources** as code, from Python.

> Status: **beta** (`0.x`). Python-only component library. Verified against
> TrueNAS 25.10.x.

## Install

```bash
pip install pulumi-truenas
```

## Quickstart

```python
import pulumi_truenas as truenas

# One provider carries the connection settings for all resources.
nas = truenas.Provider("nas", host="nas.local", transport="jsonrpc")

# Install an official catalog app.
truenas.CatalogApp(
    "jellyfin",
    truenas.CatalogAppArgs(
        app_name="jellyfin",
        catalog_app="jellyfin",
        train="stable",
        values={  # opaque, app-specific values (see "Discovering values")
            "TZ": "UTC",
            "network": {"web_port": {"port_number": 30013}},
        },
    ),
    provider=nas,
)
```

Every resource accepts `provider=<Provider>` or, as an escape hatch, the
individual connection kwargs (`host=`, `transport=`, `ssh_user=`, `api_key=`).

## Resources

| Resource | Manages | Delete safety |
|----------|---------|---------------|
| `CatalogApp` | Official TrueNAS catalog apps | `remove_ix_volumes=False` by default |
| `CustomApp` | Custom apps from Docker Compose YAML | not force-removed by default |
| `Dataset` | ZFS datasets (`pool.dataset.*`) | **no-op** unless `allow_destroy=True` |
| `Directory` | Host directories (SSH `mkdir`/`chown`/`chmod`) | **no-op** (never deletes data) |

## Transports

Two interchangeable adapters talk to the TrueNAS middleware:

- **`jsonrpc`** (recommended): JSON-RPC 2.0 over `wss://<host>/api/current`,
  API-key auth, job polling. Self-signed TLS handled by default.
- **`midclt_ssh`**: `ssh <user>@<host> midclt call ...` — bootstrap/fallback.

## Authentication (jsonrpc)

API key precedence (first hit wins):

1. Explicit `api_key=` argument
2. Environment variable `$TRUENAS_API_KEY`
3. Local `.env` file (`TRUENAS_API_KEY=...`)

Pass keys as Pulumi secrets so they are encrypted in state.

## Discovering `values`

Catalog `values` schemas are **per-app and per-version**. This library passes
`values` through unchanged; it does not validate them. To discover the exact
schema for an installed app:

```bash
midclt call app.config <app_name>          # over SSH
# or use the bundled scripts/preflight.py
```

## Importing existing resources

Bring apps/datasets/directories that already exist under management via
`pulumi import` (recommended) or `adopt_existing=True`. See
[`docs/importing.md`](docs/importing.md).

## Input validation

Every resource validates its inputs before apply (`check`): required fields,
the TrueNAS `app_name` regex, transport, `desired_state`, dataset pool-path,
and absolute directory paths. `pulumi preview` shows field-level `values` diffs.

## Safety defaults

- ix-volumes are **not** removed on delete.
- `Directory` / `Dataset` deletes are **no-ops** unless explicitly enabled.
- App-internal state (media, indexers, DBs) is out of scope.

## Documentation

- [Resource reference](docs/resources.md)
- [Authentication](docs/authentication.md)
- [Operating notes](docs/operations.md) (concurrency, timeouts, TLS)
- [Importing existing resources](docs/importing.md)
- [Releasing](docs/releasing.md)

## Examples

See [`examples/`](examples/):
- [`minimal/`](examples/minimal/) — a single catalog app
- [`custom-app/`](examples/custom-app/) — a Compose-based custom app
- [`arr-stack/`](examples/arr-stack/) — full media stack (flagship)

## License

Apache-2.0
