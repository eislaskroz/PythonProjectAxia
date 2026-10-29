"""Versión centralizada del sistema AXIA."""
from __future__ import annotations

import re

APP_VERSION = "2.05.03"


def _version_key(value: str) -> tuple[int, int, int, int]:
    numeros = [int(x) for x in re.findall(r"\d+", str(value or ""))[:4]]
    while len(numeros) < 4:
        numeros.append(0)
    return tuple(numeros[:4])


def es_version_mas_nueva(disponible: str, actual: str = APP_VERSION) -> bool:
    return _version_key(disponible) > _version_key(actual)
