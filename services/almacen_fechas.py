from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    ZONA_MEXICO = ZoneInfo("America/Mexico_City")
except ZoneInfoNotFoundError:
    ZONA_MEXICO = timezone(timedelta(hours=-6), "America/Mexico_City")


def fecha_kardex_mexico(valor: object) -> str:
    if valor is None or str(valor).strip() == "":
        return ""
    if isinstance(valor, datetime):
        fecha = valor
    else:
        texto = str(valor).strip()
        try:
            fecha = datetime.fromisoformat(texto.replace("Z", "+00:00").replace("z", "+00:00"))
        except (ValueError, OverflowError):
            return texto
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(ZONA_MEXICO).strftime("%d/%m/%Y %H:%M:%S")
