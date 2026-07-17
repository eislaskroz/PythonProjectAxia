"""Medición ligera de rendimiento para AXIA.

Se activa con AXIA_PERF_LOG=1. Los tiempos se escriben en el logger y permiten
identificar cuellos de botella sin agregar dependencias externas.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Iterator

from core.logger import configurar_logger

logger = configurar_logger("axia.performance")
_ENABLED = os.getenv("AXIA_PERF_LOG", "1").strip().lower() not in {"0", "false", "no"}
_START = time.perf_counter()


def elapsed_ms() -> float:
    return (time.perf_counter() - _START) * 1000.0


def mark(label: str) -> None:
    if _ENABLED:
        logger.info("PERF %-38s %9.1f ms desde inicio", label, elapsed_ms())


@contextmanager
def measure(label: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        if _ENABLED:
            duration = (time.perf_counter() - start) * 1000.0
            logger.info("PERF %-38s %9.1f ms", label, duration)
