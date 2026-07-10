"""Servicio para módulo Obra Civil / Proyecto Ejecutivo AXIA."""

from core.logger import configurar_logger
from core.date_utils import normalizar_campos_fecha
from supabase_config import supabase
from services.folios_service import asegurar_folio
from services.movimientos_service import registrar_movimiento_seguro

logger = configurar_logger(__name__)
TABLA_OBRAS_CIVILES = "db_obras_civiles"


def crear_obra_civil(datos_obra):
    try:
        datos_obra = asegurar_folio(datos_obra, "obc_folio", "OBC")
        datos_obra = normalizar_campos_fecha(datos_obra)
        respuesta = supabase.table(TABLA_OBRAS_CIVILES).insert(datos_obra).execute()
        registrar_movimiento_seguro(
            modulo="OBRAS_CIVILES",
            accion="CREAR",
            descripcion="Creación de registro de obra civil",
            registro_afectado=datos_obra.get("obc_folio") or respuesta.data,
        )
        return respuesta.data
    except Exception:
        logger.exception("Error al crear obra civil.")
        return None


def obtener_obras_civiles():
    try:
        respuesta = supabase.table(TABLA_OBRAS_CIVILES).select("*").order("fecha_registro", desc=True).execute()
        return respuesta.data
    except Exception:
        logger.exception("Error al consultar obras civiles.")
        return []


def obtener_obras_civiles_por_aco(aco_numero):
    try:
        respuesta = (
            supabase.table(TABLA_OBRAS_CIVILES)
            .select("*")
            .eq("obc_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .execute()
        )
        return respuesta.data
    except Exception:
        logger.exception("Error al consultar obras civiles por ACO.")
        return []


def buscar_obra_civil_por_folio(folio):
    try:
        respuesta = supabase.table(TABLA_OBRAS_CIVILES).select("*").eq("obc_folio", folio).execute()
        return respuesta.data[0] if respuesta.data else None
    except Exception:
        logger.exception("Error al buscar obra civil por folio.")
        return None
