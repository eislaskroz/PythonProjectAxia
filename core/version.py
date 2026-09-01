"""Versión centralizada del sistema AXIA."""
from __future__ import annotations

import re

APP_VERSION = "2.03.4"


def _version_key(value: str) -> tuple[int, int, int, int]:
    """Convierte una versión de AXIA en una tupla comparable.

    Se toleran formatos como ``2.02.0``, ``2.2.0.1`` o sufijos de
    pre-lanzamiento. Los primeros cuatro grupos numéricos son suficientes
    para el esquema de versiones que usa actualmente AXIA.
    """
    numeros = [int(x) for x in re.findall(r"\d+", str(value or ""))[:4]]
    while len(numeros) < 4:
        numeros.append(0)
    return tuple(numeros[:4])


def es_version_mas_nueva(disponible: str, actual: str = APP_VERSION) -> bool:
    return _version_key(disponible) > _version_key(actual)
