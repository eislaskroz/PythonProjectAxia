"""Utilidades de rendimiento para consultas, caché y trabajo en segundo plano."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from core.logger import configurar_logger

logger = configurar_logger(__name__)
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


def page_range(page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> tuple[int, int]:
    page = max(1, int(page or 1))
    page_size = min(MAX_PAGE_SIZE, max(1, int(page_size or DEFAULT_PAGE_SIZE)))
    start = (page - 1) * page_size
    return start, start + page_size - 1


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int = 120):
        self.ttl_seconds = ttl_seconds
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
            self._items[key] = _CacheEntry(value, time.monotonic() + self.ttl_seconds)

    def clear(self):
        with self._lock:
            self._items.clear()


def run_in_background(task: Callable[[], Any], *, widget=None, on_success=None, on_error=None, name="AXIA-worker"):
    """Ejecuta red/PDF fuera del hilo Tk y devuelve callbacks al hilo visual."""
    def dispatch(callback, *args):
        if not callback:
            return
        if widget is not None and hasattr(widget, "after"):
            widget.after(0, lambda: callback(*args))
        else:
            callback(*args)

    def worker():
        try:
            result = task()
            dispatch(on_success, result)
        except Exception as exc:
            logger.exception("Falló una tarea en segundo plano: %s", name)
            dispatch(on_error, exc)

    thread = threading.Thread(target=worker, name=name, daemon=True)
    thread.start()
    return thread
