"""Utilidades JSON comunes para los formularios y servicios AXIA."""
from __future__ import annotations

import json
from typing import Any


def dumps_db(value: Any) -> str:
    """Serializa datos para columnas JSON/texto conservando acentos."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads_db(value: Any, default: Any = None) -> Any:
    """Deserializa de forma tolerante valores JSON ya parseados o en texto."""
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default
