from __future__ import annotations

from typing import Any

import orjson


def dumps(value: Any) -> str:
    """Serialize a Python value to a compact JSON string."""
    return orjson.dumps(value).decode()


def loads(value: str | bytes) -> Any:
    """Deserialize a JSON string/bytes to a Python value."""
    return orjson.loads(value)
