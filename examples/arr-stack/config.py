"""Consumer-side Pulumi config loader for the ARR stack example.

This shows how a *user* of ``pulumi-truenas`` reads their own stack config and
resolves the API key (Pulumi encrypted secret -> env -> .env), then builds a
``ProviderSettings`` from the library.
"""

from __future__ import annotations

import pulumi_truenas as truenas
from pulumi_truenas.secrets import resolve_api_key


def load_provider() -> truenas.Provider:
    """Build a pulumi_truenas.Provider from this stack's Pulumi config.

    Resolves the API key with precedence: Pulumi encrypted secret ->
    $TRUENAS_API_KEY -> .env, wrapping env/.env values as Pulumi secrets.
    """
    import pulumi

    cfg = pulumi.Config()
    api_key_env = cfg.get("apiKeyEnv") or "TRUENAS_API_KEY"
    config_key = cfg.get_secret("apiKey")
    resolved = resolve_api_key(env_var=api_key_env)
    if config_key is not None:
        api_key: object | None = config_key
    elif resolved is not None:
        api_key = pulumi.Output.secret(resolved)
    else:
        api_key = None

    return truenas.Provider(
        "truenas",
        transport=cfg.get("transport") or "jsonrpc",
        host=cfg.get("host") or "truenas.local",
        ssh_user=cfg.get("sshUser") or "yehia",
        api_url=cfg.get("apiUrl"),
        api_key_env=api_key_env,
        api_key=api_key,
    )
