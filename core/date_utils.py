
"""Utilidades centralizadas para normalizar fechas antes de enviar a Supabase."""
from __future__ import annotations

from core.logger import configurar_logger

logger = configurar_logger(__name__)
from datetime import datetime

_FORMATOS_FECHA = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d%m%Y",
    "%Y/%m/%d",
)

def normalizar_fecha_supabase(valor):
    if valor in (None, ""):
        return None
    valor = str(valor).strip()
    if not valor:
        return None
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            logger.debug("Excepción recuperable controlada.", exc_info=True)
    return valor

def normalizar_campos_fecha(datos):
    if not isinstance(datos, dict):
        return datos
    normalizados = dict(datos)
    for campo, valor in list(normalizados.items()):
        if "fecha" in str(campo).lower():
            normalizados[campo] = normalizar_fecha_supabase(valor)
    return normalizados


# Las fechas de la base conservan su valor y tipo original. Este formato
# es EXCLUSIVAMENTE para mostrar información en la aplicación.
from datetime import date as _date, timezone as _timezone
import re as _re

_FECHA_VISUAL = "%d/%m/%Y %H:%M:%S"


def es_campo_fecha(nombre):
    """Detecta columnas de fecha; excluye horas aisladas y fechas en texto libre."""
    n = str(nombre or "").lower().strip()
    return ("fecha" in n or n in ("created_at", "updated_at", "timestamp", "date"))


def formatear_fecha_visual(valor):
    """YYYY-MM-DD[THH:MM:SS[Z/offset]] -> DD/MM/AAAA HH:MM:SS.

    Las fechas sin hora se representan como 00:00:00. Fechas con zona UTC
    se llevan a la zona local del equipo; los valores sin zona no se desplazan.
    Nunca transforma cadenas no reconocidas ni modifica el valor almacenado.
    """
    if valor is None or valor == "":
        return ""
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, _date):
        dt = datetime.combine(valor, datetime.min.time())
    elif isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return ""
        try:
            dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            dt = None
        if dt is None:
            for fmt in (_FECHA_VISUAL, "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    dt = datetime.strptime(texto, fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            return valor
    else:
        return valor
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.strftime(_FECHA_VISUAL)


def fecha_para_vista(campo, valor):
    """Solo formatea columnas de fecha y deja intactos los demás datos."""
    return formatear_fecha_visual(valor) if es_campo_fecha(campo) else valor


def fecha_desde_vista(texto, valor_original):
    """Vuelve al formato del valor original solo si hubo edición explícita.

    Evita actualizar campos cuando únicamente se abrió el editor.
    Para date se conserva YYYY-MM-DD; para timestamp se conserva ISO 8601.
    """
    texto = str(texto or "").strip()
    if texto == str(formatear_fecha_visual(valor_original) or "").strip():
        return valor_original
    if not texto:
        return None
    try:
        dt = datetime.strptime(texto, _FECHA_VISUAL)
    except ValueError:
        # El calendario antiguo devuelve ISO y debe seguir siendo compatible.
        try:
            dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError("Fecha inválida. Usa DD/MM/AAAA HH:MM:SS.") from e
    original = str(valor_original or "")
    if _re.fullmatch(r"\d{4}-\d{2}-\d{2}", original) or not valor_original:
        return dt.strftime("%Y-%m-%d")
    if original.endswith("Z") or _re.search(r"[+-]\d\d:\d\d$", original):
        return dt.astimezone().isoformat(timespec="seconds")
    return dt.isoformat(timespec="seconds")
