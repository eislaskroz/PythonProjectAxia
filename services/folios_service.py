"""
=========================================================
SERVICIO DE FOLIOS AUTOMÁTICOS - AXIA
=========================================================

Genera folios consecutivos por módulo sin pedir captura manual.

Formatos actuales:
- LEV-00001 Levantamientos (generado centralmente por Supabase RPC)
- OS-00001  Órdenes de servicio
- OT-00001  Órdenes de trabajo
- BIT-00001 Bitácoras operativas
- OBC-0001  Obras civiles / Proyecto ejecutivo

IMPORTANTE:
Los folios LEV se generan exclusivamente mediante la función RPC
public.generar_folio_levantamiento() de Supabase. Los demás módulos
conservan temporalmente el mecanismo heredado hasta su homologación.
"""

import re

from core.logger import configurar_logger
from supabase_config import supabase

logger = configurar_logger(__name__)


class FolioCentralError(RuntimeError):
    """Error al solicitar o validar un folio centralizado en Supabase."""


def _extraer_valor_rpc(data):
    """Normaliza la respuesta de supabase-py para una RPC escalar."""
    if isinstance(data, str):
        return data
    if isinstance(data, list) and data:
        value = data[0]
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("generar_folio_levantamiento", "folio", "value"):
                if value.get(key):
                    return value[key]
    if isinstance(data, dict):
        for key in ("generar_folio_levantamiento", "folio", "value"):
            if data.get(key):
                return data[key]
    return None


def solicitar_folio_levantamiento():
    """Solicita a Supabase el siguiente folio único con formato LEV-XXXXX."""
    try:
        respuesta = supabase.rpc("generar_folio_levantamiento").execute()
    except Exception as error:
        logger.exception("No fue posible solicitar el folio centralizado de levantamiento.")
        raise FolioCentralError(
            "No fue posible obtener un folio desde Supabase. "
            "Verifica que la migración de folios centralizados esté ejecutada y que exista conexión."
        ) from error

    folio = str(_extraer_valor_rpc(getattr(respuesta, "data", None)) or "").strip().upper()
    if not re.fullmatch(r"LEV-\d{5,}", folio):
        raise FolioCentralError(
            f"Supabase devolvió un folio inválido: {folio or 'VACÍO'}. "
            "Se esperaba el formato LEV-XXXXX."
        )
    return folio


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
    """Construye el folio con el ancho definido para cada módulo.

    OS, OT y BIT usan cinco dígitos. OBC conserva cuatro.
    LEV se genera por RPC y ya utiliza cinco dígitos.
    """
    prefijo = prefijo.upper().strip()
    ancho = 5 if prefijo in {"LEV", "OS", "OT", "BIT"} else 4
    return f"{prefijo}-{int(consecutivo):0{ancho}d}"


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

    if prefijo == "LEV":
        return solicitar_folio_levantamiento()

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
