# Authentication

## Transports

- **`jsonrpc`** (recommended): JSON-RPC 2.0 over `wss://<host>/api/current`.
  Requires a TrueNAS **API key**.
- **`midclt_ssh`**: `ssh <user>@<host> midclt call ...`. Uses your SSH
  credentials/agent; no API key needed. Also used by the `Directory` resource.

## API key precedence (jsonrpc)

The key is resolved in this order (first hit wins):

1. Explicit `api_key=` on the `Provider` (or on a resource).
2. Environment variable `$TRUENAS_API_KEY` (name configurable via
   `api_key_env`).
3. Local `.env` file: `TRUENAS_API_KEY=...` (git-ignored).

### Recommended: Pulumi encrypted secret config

Store the key as a Pulumi secret so it is encrypted at rest and in state:

```bash
pulumi config set --secret apiKey <your-key>
```

Then wire it into the provider:

```python
import pulumi
import pulumi_truenas as truenas

cfg = pulumi.Config()
nas = truenas.Provider(
    "nas",
    host=cfg.get("host"),
    transport="jsonrpc",
    api_key=cfg.get_secret("apiKey"),   # secret Output -> encrypted in state
)
```

The API key is:
- **encrypted at rest** in `Pulumi.<stack>.yaml` (`secure: v1:...`),
- **encrypted in state**, and
- **masked in logs**.

## TLS

TrueNAS ships a **self-signed certificate**, so `verify_tls` defaults to
`False`. Options:

- Trusted/public cert: `verify_tls=True` (uses the system trust store).
- Private CA: `ca_cert="/path/to/ca.pem"` (verifies against your CA).
- Default (self-signed): leave both unset.

## Getting an API key

TrueNAS UI → top-right user menu → **API Keys** → Add. Copy the key (shown
once). Rotate keys there if one is exposed.
