"""Consultas Supabase tolerantes a diferencias controladas de esquema.

Mantiene selecciones explícitas (nunca ``select('*')``) y, cuando PostgREST
reporta que una columna opcional no existe, la retira, registra la diferencia
y reintenta. Los demás errores se propagan.
"""
from __future__ import annotations

import re
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
            query = client.table(table).select(",".join(active))
            if configure is not None:
                query = configure(query)
            response = query.execute()
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
