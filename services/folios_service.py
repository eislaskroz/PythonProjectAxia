"""
=========================================================
SERVICIO DE FOLIOS AUTOMÁTICOS - AXIA
=========================================================

Genera folios consecutivos por módulo sin pedir captura manual.

Formatos actuales:
- LEV-0001  Levantamientos
- OS-0001   Órdenes de servicio
- OT-0001   Órdenes de trabajo
- BIT-0001  Bitácoras operativas
- OBC-0001  Obras civiles / Proyecto ejecutivo

IMPORTANTE:
Este servicio calcula el siguiente consecutivo leyendo el último
folio existente en Supabase. Para producción multiusuario de alto
volumen, lo ideal será crear una tabla de consecutivos con bloqueo
transaccional o una función RPC en PostgreSQL.
"""

import re

from core.logger import configurar_logger
from supabase_config import supabase

logger = configurar_logger(__name__)


CONFIG_FOLIOS = {
    "LEV": {
        "tabla": "db_levantamientos",
        "campo": "lev_folio",
    },
    "OS": {
        "tabla": "db_ordenes_servicio",
        "campo": "os_folio",
    },
    "OT": {
        "tabla": "db_ordenes_trabajo",
        "campo": "ot_folio",
    },
    "BIT": {
        "tabla": "db_bitacoras",
        "campo": "bit_folio",
    },
    "OBC": {
        "tabla": "db_obras_civiles",
        "campo": "obc_folio",
    },
}


def extraer_consecutivo(folio, prefijo):
    """
    Extrae el número final de un folio tipo LEV-0001.
    Si el formato no coincide, retorna 0.
    """

    if not folio:
        return 0

    patron = rf"^{re.escape(prefijo)}-(\d+)$"
    coincidencia = re.match(patron, str(folio).strip(), re.IGNORECASE)

    if not coincidencia:
        return 0

    try:
        return int(coincidencia.group(1))
    except ValueError:
        return 0


def formatear_folio(prefijo, consecutivo):
    """
    Construye un folio con cuatro dígitos mínimos.
    Ejemplo: formatear_folio("LEV", 1) -> LEV-0001
    """

    return f"{prefijo.upper()}-{int(consecutivo):04d}"


def obtener_ultimo_folio(prefijo):
    """
    Consulta Supabase para obtener el último folio registrado
    de acuerdo con la configuración del prefijo.
    """

    config = CONFIG_FOLIOS.get(prefijo.upper())

    if not config:
        raise ValueError(f"Prefijo de folio no configurado: {prefijo}")

    tabla = config["tabla"]
    campo = config["campo"]

    respuesta = (
        supabase
        .table(tabla)
        .select(campo)
        .like(campo, f"{prefijo.upper()}-%")
        .order(campo, desc=True)
        .limit(1)
        .execute()
    )

    if not respuesta.data:
        return None

    return respuesta.data[0].get(campo)


def generar_siguiente_folio(prefijo):
    """
    Genera el siguiente folio disponible para el módulo indicado.

    Retorna:
        str: Folio generado, por ejemplo LEV-0001.
    """

    prefijo = prefijo.upper().strip()

    try:
        ultimo_folio = obtener_ultimo_folio(prefijo)
        ultimo_consecutivo = extraer_consecutivo(ultimo_folio, prefijo)
        return formatear_folio(prefijo, ultimo_consecutivo + 1)

    except Exception:
        logger.exception("Error al generar folio automático para %s.", prefijo)
        # Fallback seguro para no bloquear la UI si la tabla está vacía o hay error puntual.
        return formatear_folio(prefijo, 1)


def asegurar_folio(datos, campo, prefijo):
    """
    Garantiza que un diccionario tenga folio.
    Si el campo viene vacío, genera uno automáticamente.
    """

    datos = dict(datos or {})

    if not datos.get(campo):
        datos[campo] = generar_siguiente_folio(prefijo)

    return datos
