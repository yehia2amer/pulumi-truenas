# Example: ARR media stack

The flagship example for `pulumi-truenas`: a full media automation stack
(qBittorrent, Sonarr, Radarr, Prowlarr, Bazarr, Seerr, FlareSolverr, and a
Configarr custom app) plus the TRaSH directory layout.

This is a **consumer** of the library — it shows how to:

- read your own Pulumi stack config (`config.py`) and resolve the API key,
- build app `values` payloads (`app_values.py`),
- declare your desired apps/ports/mounts/directories (`stack.py`),
- wire it all together in `__main__.py`.

## Files

| File | Purpose |
|------|---------|
| `__main__.py` | Pulumi program: directories + apps |
| `stack.py` | Desired state: apps, ports, mounts, directory list |
| `app_values.py` | TrueNAS catalog-app `values` builders |
| `config.py` | Reads Pulumi config + resolves API key |
| `scripts/preflight.py` | Read-only connectivity + config dump |
| `scripts/diff_values.py` | Read-only desired-vs-live diff |

## Run

```bash
cd examples/arr-stack
uv sync
pulumi config set transport jsonrpc
pulumi config set host <your-nas>
pulumi config set --secret apiKey <your-key>   # jsonrpc
pulumi preview
pulumi up
```

> Adjust `stack.py` (ports, paths, UID/GID, timezone) to match your NAS before
> applying. The values here target a specific home deployment.
