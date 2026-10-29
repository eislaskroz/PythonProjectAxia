"""Formato local de fechas del Kárdex AXIA (saldos/fechas sin mutar).

La base utiliza ``timestamptz`` y PostgREST devuelve marcas ISO-8601 con
zona horaria (habitualmente UTC). La vista muestra hora de Ciudad de México.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# En Windows Python puede no disponer de la base IANA del sistema. Para las
# operaciones contemporáneas (México, desde 2023) la zona es UTC-06:00.
try:
    ZONA_MEXICO = ZoneInfo("America/Mexico_City")
except ZoneInfoNotFoundError:
    ZONA_MEXICO = timezone(timedelta(hours=-6), "America/Mexico_City")


def fecha_kardex_mexico(valor: object) -> str:
    """Convierte un timestamp ISO-8601 de Supabase a dd/mm/aaaa HH:MM:SS.

    No cambia el dato en la base ni supone que la hora UTC mostrada es local.
    Los timestamps antiguos sin zona se interpretan como UTC, que es la
    convención de almacenamiento usada por la tabla de movimientos.
    """
    if valor is None or str(valor).strip() == "":
        return ""
    if isinstance(valor, datetime):
        fecha = valor
    else:
        texto = str(valor).strip()
        try:
            fecha = datetime.fromisoformat(texto.replace("Z", "+00:00").replace("z", "+00:00"))
        except (ValueError, OverflowError):
            return texto  # Conserva dato desconocido; nunca oculta el movimiento.
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(ZONA_MEXICO).strftime("%d/%m/%Y %H:%M:%S")
