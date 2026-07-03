# Importing existing TrueNAS resources

There are two ways to bring resources that already exist on your TrueNAS into
Pulumi management.

## 1. `pulumi import` (recommended)

Import adopts an existing resource into your stack state by calling the
provider's read-only `read`. The resource **id** is:

| Resource | Import id |
|----------|-----------|
| `CatalogApp` | the app name (e.g. `sonarr`) |
| `CustomApp` | the app name (e.g. `configarr`) |
| `Dataset` | the dataset path (e.g. `tank/media`) |
| `Directory` | the absolute path (e.g. `/mnt/tank/appdata`) |

Because these are **dynamic** resources, first declare the resource in your
program (with its connection settings / `provider=`), then import it:

```bash
pulumi import \
  "pulumi-python:dynamic:Resource" \
  sonarr \
  sonarr
```

Then fill in the resource's inputs in code to match the live config (use
`scripts/preflight.py --app sonarr` to dump the current `values`) and run
`pulumi preview` until it reports no changes.

> Note: on import, `read` runs with only the id (no connection settings), so it
> returns the id-derived identity. The first `pulumi up`/`preview` with your
> declared `provider=` reconciles the full live state.

## 2. Adopt-on-create

Each app/dataset resource accepts `adopt_existing=True`. When set, `create`
detects an already-present resource and **reconciles it in place** instead of
failing. This is convenient for first-time onboarding of a whole stack:

```python
truenas.CatalogApp(
    "sonarr",
    truenas.CatalogAppArgs(
        app_name="sonarr", catalog_app="sonarr", train="community",
        values={...}, adopt_existing=True,
    ),
    provider=nas,
)
```

`adopt_existing` defaults to **False** for predictability. Prefer
`pulumi import` for production; use `adopt_existing=True` for bulk onboarding of
an existing deployment (as the `arr-stack` example does).
