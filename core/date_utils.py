
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
