"""
=========================================================
SERVICIO DE ÓRDENES DE TRABAJO - AXIA
=========================================================

Nueva capa de negocio para el formato Orden de Trabajo.
La vista no consulta Supabase directamente; todo pasa por este servicio.
"""

from core.logger import configurar_logger
from core.date_utils import normalizar_campos_fecha
from supabase_config import supabase
from services.folios_service import asegurar_folio

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro

TABLA_ORDENES_TRABAJO = "db_ordenes_trabajo"


def crear_orden_trabajo(datos_orden):
    """
    Crea una orden de trabajo.
    Si no viene folio, genera automáticamente OT-0001, OT-0002, etc.
    """

    try:
        datos_orden = asegurar_folio(datos_orden, "ot_folio", "OT")
        datos_orden = normalizar_campos_fecha(datos_orden)

        respuesta = (
            supabase
            .table(TABLA_ORDENES_TRABAJO)
            .insert(datos_orden)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_TRABAJO",
            accion="CREAR",
            descripcion="Creación de orden de trabajo",
            registro_afectado=datos_orden.get("ot_folio") or respuesta.data,
        )
        return respuesta.data

    except Exception:
        logger.exception("Error al crear orden de trabajo.")
        return None


def obtener_ordenes_trabajo():
    """
    Consulta todas las órdenes de trabajo registradas.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ORDENES_TRABAJO)
            .select("*")
            .order("fecha_registro", desc=True)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_TRABAJO",
            accion="CONSULTAR",
            descripcion="Consulta general de órdenes de trabajo",
            registro_afectado=f"Total: {len(respuesta.data or [])}",
        )
        return respuesta.data

    except Exception:
        logger.exception("Error al consultar órdenes de trabajo.")
        return []


def obtener_ordenes_trabajo_por_aco(aco_numero):
    """
    Consulta órdenes de trabajo asociadas a un ACO.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ORDENES_TRABAJO)
            .select("*")
            .eq("ot_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_TRABAJO",
            accion="BUSCAR_POR_ACO",
            descripcion=f"Consulta de órdenes de trabajo por ACO: {aco_numero}",
            registro_afectado=aco_numero,
        )
        return respuesta.data

    except Exception:
        logger.exception("Error al consultar órdenes de trabajo por ACO.")
        return []


def buscar_orden_trabajo_por_folio(folio):
    """
    Busca una orden de trabajo por folio.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ORDENES_TRABAJO)
            .select("*")
            .eq("ot_folio", folio)
            .execute()
        )

        if respuesta.data:
            registrar_movimiento_seguro(
                modulo="ORDENES_TRABAJO",
                accion="BUSCAR",
                descripcion=f"Búsqueda de orden de trabajo por folio: {folio}",
                registro_afectado=folio,
            )
            return respuesta.data[0]

        registrar_movimiento_seguro(
            modulo="ORDENES_TRABAJO",
            accion="BUSCAR_SIN_RESULTADO",
            descripcion=f"Búsqueda de orden de trabajo sin resultado: {folio}",
            registro_afectado=folio,
        )
        return None

    except Exception:
        logger.exception("Error al buscar orden de trabajo.")
        return None


def obtener_estadisticas_ordenes_trabajo():
    """
    Estadísticas simples para reportes administrativos.
    """

    try:
        ordenes = obtener_ordenes_trabajo()
        total = len(ordenes)
        pendientes = len([o for o in ordenes if o.get("ot_estatus") == 1])
        proceso = len([o for o in ordenes if o.get("ot_estatus") == 2])
        finalizadas = len([o for o in ordenes if o.get("ot_estatus") == 3])
        return total, pendientes, proceso, finalizadas

    except Exception:
        logger.exception("Error al obtener estadísticas de órdenes de trabajo.")
        return 0, 0, 0, 0
