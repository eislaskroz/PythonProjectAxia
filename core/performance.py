"""Infraestructura de rendimiento de AXIA.

Incluye medición ligera, caché TTL, paginación y ejecución segura de tareas
fuera del hilo visual. Ninguna utilidad debe impedir el arranque de AXIA si
el registro de métricas falla.
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from core.logger import configurar_logger

logger = configurar_logger(__name__)
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
_PERF_ENABLED = os.getenv("AXIA_ENABLE_PERFORMANCE_LOG", "0").strip().lower() in {
    "1", "true", "yes", "on",
}
_START_MONOTONIC = time.perf_counter()


def page_range(page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> tuple[int, int]:
    """Convierte número/tamaño de página al rango inclusivo de Supabase."""
    page = max(1, int(page or 1))
    page_size = min(MAX_PAGE_SIZE, max(1, int(page_size or DEFAULT_PAGE_SIZE)))
    start = (page - 1) * page_size
    return start, start + page_size - 1


def mark(label: str) -> float:
    """Registra una marca temporal y devuelve segundos desde el arranque.

    El registro detallado se activa con ``AXIA_ENABLE_PERFORMANCE_LOG=1``.
    La función existe siempre para que la instrumentación nunca rompa AXIA.
    """
    elapsed = time.perf_counter() - _START_MONOTONIC
    if _PERF_ENABLED:
        logger.info("PERF mark | %s | %.3f s", label, elapsed)
    else:
        logger.debug("PERF mark | %s | %.3f s", label, elapsed)
    return elapsed


@contextmanager
def measure(label: str, *, warning_ms: float = 750.0) -> Iterator[None]:
    """Mide un bloque sin ocultar sus excepciones.

    Los bloques lentos se registran como advertencia. Las excepciones se
    propagan intactas después de registrar la duración, evitando convertir
    esta herramienta en una fuente de fallos silenciosos.
    """
    started = time.perf_counter()
    try:
        yield
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        logger.exception("PERF error | %s | %.2f ms", label, elapsed_ms)
        raise
    else:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if elapsed_ms >= warning_ms:
            logger.warning("PERF lento | %s | %.2f ms", label, elapsed_ms)
        elif _PERF_ENABLED:
            logger.info("PERF medida | %s | %.2f ms", label, elapsed_ms)
        else:
            logger.debug("PERF medida | %s | %.2f ms", label, elapsed_ms)


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Caché en memoria segura para acceso concurrente."""

    def __init__(self, ttl_seconds: float = 120):
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds no puede ser negativo")
        self.ttl_seconds = float(ttl_seconds)
        self._items: dict[Any, _CacheEntry] = {}
        self._lock = threading.RLock()

    def get(self, key: Any):
        with self._lock:
            item = self._items.get(key)
            if not item or item.expires_at <= time.monotonic():
                self._items.pop(key, None)
                return None
            return item.value

    def set(self, key: Any, value: Any):
        with self._lock:
            self._items[key] = _CacheEntry(
                value=value,
                expires_at=time.monotonic() + self.ttl_seconds,
            )

    def invalidate(self, key: Any) -> None:
        with self._lock:
            self._items.pop(key, None)

    def clear(self):
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            now = time.monotonic()
            expired = [key for key, item in self._items.items() if item.expires_at <= now]
            for key in expired:
                self._items.pop(key, None)
            return len(self._items)


def run_in_background(
    task: Callable[[], Any],
    *,
    widget=None,
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    name: str = "AXIA-worker",
) -> threading.Thread:
    """Ejecuta red/PDF fuera del hilo Tk y devuelve callbacks al hilo visual."""

    def dispatch(callback, *args):
        if callback is None:
            return
        if widget is not None and hasattr(widget, "after"):
            try:
                widget.after(0, lambda: callback(*args))
                return
            except Exception:
                logger.exception("No fue posible devolver callback al hilo visual: %s", name)
        callback(*args)

    def worker():
        with measure(name):
            try:
                result = task()
            except Exception as exc:
                logger.exception("Falló una tarea en segundo plano: %s", name)
                dispatch(on_error, exc)
                return
            dispatch(on_success, result)

    thread = threading.Thread(target=worker, name=name, daemon=True)
    thread.start()
    return thread
