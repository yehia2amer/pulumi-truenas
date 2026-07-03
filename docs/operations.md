# Operating notes

## Concurrency

TrueNAS middleware serializes many app operations internally and can reject or
mis-handle overlapping app jobs (create/update/delete running at once). For
app-heavy stacks, run Pulumi with reduced parallelism:

```bash
pulumi up --parallel 1
```

Directory and dataset operations are generally safe in parallel. If you see
intermittent job errors on large `up` runs, `--parallel 1` is the first thing
to try.

## Timeouts & retries (jsonrpc)

Catalog app creates pull container images, which can take minutes. Tune per
`Provider`:

```python
truenas.Provider(
    "nas",
    host="nas.local",
    job_timeout_s=3600,     # wait up to 1h for a job (default ~1800s)
    poll_interval_s=5,      # status poll cadence
)
```

The jsonrpc transport also retries the initial WebSocket connection on
transient failures (3 attempts with linear backoff) before giving up.

## TLS

- Default: `verify_tls=False` (TrueNAS self-signed cert).
- Private CA: `ca_cert="/path/to/ca.pem"` — verifies against your CA.
- Public/trusted cert: `verify_tls=True` — uses system trust store.

```python
truenas.Provider("nas", host="nas.local", ca_cert="/etc/ssl/truenas-ca.pem")
```

## Secrets in logs

API keys are Pulumi secrets (encrypted in state, masked in Pulumi output) and
are additionally redacted from any API error message the library raises.

## Disaster recovery

This library provisions **infrastructure** (apps, datasets, directories). It
does **not** manage app-internal state (media libraries, indexers, databases).
A full recovery is two steps:

1. `pulumi up` — recreate apps/datasets/directories.
2. Restore app-internal state with your own tooling (e.g. app config/db
   backups).
