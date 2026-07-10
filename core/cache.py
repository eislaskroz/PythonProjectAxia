"""
=========================================================
CORE: CACHE LIGERO EN MEMORIA
=========================================================

Uso:
- Evitar consultas repetidas a Supabase para catálogos y combos.
- Mantener la interfaz más fluida en equipos limitados.

Regla:
- No usar para datos críticos que cambian cada segundo.
- Invalidar cache después de crear/actualizar registros.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable

_CACHE: dict[str, tuple[float, Any]] = {}


def _make_key(nombre: str, args: tuple, kwargs: dict) -> str:
    return f"{nombre}:{repr(args)}:{repr(sorted(kwargs.items()))}"


def ttl_cache(ttl_seconds: int = 60) -> Callable:
    """Decorador simple de cache con tiempo de vida."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_key(func.__module__ + "." + func.__name__, args, kwargs)
            now = time.time()
            cached = _CACHE.get(key)
            if cached:
                expires_at, value = cached
                if now < expires_at:
                    return value
            value = func(*args, **kwargs)
            _CACHE[key] = (now + ttl_seconds, value)
            return value

        return wrapper

    return decorator


def clear_cache(prefix: str | None = None) -> None:
    """
    Limpia la cache completa o solo entradas cuyo identificador inicia con prefix.
    """
    if not prefix:
        _CACHE.clear()
        return
    for key in list(_CACHE.keys()):
        if key.startswith(prefix):
            _CACHE.pop(key, None)
