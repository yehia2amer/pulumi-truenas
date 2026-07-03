"""API key resolution with a clear precedence chain.

Resolution order (first hit wins):

  1. Pulumi encrypted secret config  ``truenas-pulumi:apiKey``  (best practice)
  2. Environment variable            ``$TRUENAS_API_KEY``       (CI / shells)
  3. Local dotenv file               ``.env`` -> ``TRUENAS_API_KEY=...``  (dev)

The dynamic providers run out-of-process during ``pulumi up`` and cannot read
Pulumi config, so the *resolved* key is passed into resources as a Pulumi
secret (encrypted in state, masked in logs). At the API layer the key may also
be read directly from the environment (used by the standalone scripts).
"""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_ENV_VAR = "TRUENAS_API_KEY"


def _read_dotenv(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() != key:
            continue
        value = value.strip()
        # Strip optional surrounding quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        return value or None
    return None


def resolve_api_key(
    *,
    config_value: str | None = None,
    env_var: str = _DEFAULT_ENV_VAR,
    dotenv_path: str | Path | None = ".env",
) -> str | None:
    """Return the API key using the documented precedence chain.

    ``config_value`` is the (already decrypted) value from Pulumi secret
    config, resolved by the caller in the Pulumi program.
    """
    if config_value:
        return config_value
    env_value = os.environ.get(env_var)
    if env_value:
        return env_value
    if dotenv_path is not None:
        return _read_dotenv(Path(dotenv_path), env_var)
    return None
