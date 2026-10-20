"""Consultas Supabase tolerantes a diferencias controladas de esquema.

Mantiene selecciones explícitas (nunca ``select('*')``) y, cuando PostgREST
reporta que una columna opcional no existe, la retira, registra la diferencia
y reintenta. Los demás errores se propagan.
"""
from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from core.logger import configurar_logger

logger = configurar_logger(__name__)

_COLUMN_PATTERNS = (
    re.compile(r"Could not find the ['\"](?P<column>[A-Za-z_][A-Za-z0-9_]*)['\"] column", re.I),
    re.compile(r"column ['\"]?(?:[A-Za-z_][A-Za-z0-9_]*\.)?(?P<column>[A-Za-z_][A-Za-z0-9_]*)['\"]? does not exist", re.I),
    re.compile(r"column (?P<column>[A-Za-z_][A-Za-z0-9_]*) does not exist", re.I),
)


def _missing_column(error: Exception) -> str | None:
    text = str(error)
    for pattern in _COLUMN_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group("column")
    return None


def es_error_conexion_transitoria(error: Exception) -> bool:
    """Solo errores de transporte recuperables, nunca errores SQL o de permisos."""
    # Ejemplos: <ConnectionTerminated error_code:1 ...> (HTTP/2),
    # RemoteProtocolError, desconexión remota y cortes temporales de red.
    tipo = type(error).__name__.lower()
    texto = str(error).lower()
    return any(
        marca in tipo or marca in texto
        for marca in (
            "connectionterminated", "remoteprotocolerror", "readerror",
            "connecterror", "connectionreset", "connectionaborted",
            "server disconnected", "connection closed", "connection terminated",
            "remotedisconnected", "readtimeout", "connecttimeout",
        )
    )


def ejecutar_lectura_con_reintento(consulta, *, intentos: int = 3, espera: float = 0.35):
    """Reintenta SOLO lecturas idempotentes, reconstruyendo cada consulta.

    `consulta` debe ser una función sin argumentos que cree y ejecute
    nuevamente el SELECT. No utilizar jamás para INSERT/UPDATE/DELETE.
    """
    for intento in range(max(1, int(intentos))):
        try:
            return consulta()
        except Exception as error:
            if not es_error_conexion_transitoria(error) or intento >= intentos - 1:
                raise
            pausa = espera * (2 ** intento)
            logger.warning(
                "Consulta de lectura interrumpida (%s). Reintento %s/%s en %.2fs.",
                type(error).__name__, intento + 1, intentos - 1, pausa,
            )
            time.sleep(pausa)


def execute_select_compatible(
    client: Any,
    table: str,
    columns: str | list[str] | tuple[str, ...],
    configure: Callable[[Any], Any] | None = None,
    *,
    max_schema_retries: int = 12,
):
    """Ejecuta una consulta explícita y tolera columnas opcionales ausentes.

    ``configure`` recibe el query builder después de ``select`` y debe devolver
    el builder configurado con filtros, orden y paginación.
    """
    active = [c.strip() for c in (columns.split(",") if isinstance(columns, str) else columns) if c.strip()]
    if not active:
        raise ValueError("La consulta requiere al menos una columna explícita.")

    removed: list[str] = []
    for _attempt in range(max_schema_retries + 1):
        try:
            def leer():
                query = client.table(table).select(",".join(active))
                if configure is not None:
                    query = configure(query)
                return query.execute()

            response = ejecutar_lectura_con_reintento(leer)
            if removed:
                logger.warning(
                    "Esquema compatible aplicado en %s; columnas ausentes omitidas: %s",
                    table,
                    ", ".join(removed),
                )
            return response
        except Exception as error:
            column = _missing_column(error)
            if not column or column not in active or len(active) == 1:
                raise
            active.remove(column)
            removed.append(column)
            logger.warning(
                "La columna %s no existe en %s; reintentando consulta sin ella.",
                column,
                table,
            )

    raise RuntimeError(f"No fue posible estabilizar la consulta de {table}.")
