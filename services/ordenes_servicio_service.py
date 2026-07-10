"""
=========================================================
SERVICIO DE ÓRDENES DE SERVICIO - AXIA
=========================================================

Este archivo pertenece a la capa de servicios de AXIA.

Responsabilidad principal:
- Contener lógica de negocio.
- Consultar y modificar datos en Supabase.
- Devolver resultados limpios a las vistas.

Regla de arquitectura:
Las vistas en `views/` no deben hablar directamente con Supabase.
Deben llamar funciones de esta capa `services/`.
"""

from core.logger import configurar_logger
from core.date_utils import normalizar_campos_fecha

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro

# =====================================================
# IMPORTACIÓN DE SUPABASE
# =====================================================

from supabase_config import supabase
from services.folios_service import asegurar_folio


# =====================================================
# CONSTANTE DE TABLA
# =====================================================

TABLA_ORDENES = "db_ordenes_servicio"


# =====================================================
# FUNCIÓN: crear_orden_servicio()
# =====================================================
def crear_orden_servicio(datos_orden):
    """
    Crea una nueva orden de servicio.

    PARÁMETROS:
        datos_orden:
            Diccionario con los datos de la orden.

    RETORNA:
        list | None:
            Datos insertados si el registro fue exitoso.
    """

    try:
        datos_orden = asegurar_folio(datos_orden, "os_folio", "OS")
        datos_orden = normalizar_campos_fecha(datos_orden)

        respuesta = (
            supabase
            .table(TABLA_ORDENES)
            .insert(datos_orden)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="CREAR",
            descripcion="Creación de orden de servicio",
            registro_afectado=datos_orden.get("os_folio") or datos_orden.get("folio_orden") or respuesta.data,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al crear orden de servicio.")
        return None


# =====================================================
# FUNCIÓN: obtener_ordenes_servicio()
# =====================================================
def obtener_ordenes_servicio():
    """
    Consulta todas las órdenes de servicio.

    RETORNA:
        list:
            Lista de órdenes registradas.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ORDENES)
            .select("*")
            .order("fecha_registro", desc=True)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="CONSULTAR",
            descripcion="Consulta general de órdenes de servicio",
            registro_afectado=f"Total: {len(respuesta.data or [])}",
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar órdenes.")
        return []


# =====================================================
# FUNCIÓN: obtener_ordenes_por_aco()
# =====================================================
def obtener_ordenes_por_aco(aco_numero):
    """
    Consulta órdenes relacionadas con un ACO.

    PARÁMETROS:
        aco_numero:
            Número de ACO.

    RETORNA:
        list:
            Lista de órdenes relacionadas.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ORDENES)
            .select("*")
            .eq("os_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="BUSCAR_POR_ACO",
            descripcion=f"Consulta de órdenes de servicio por ACO: {aco_numero}",
            registro_afectado=aco_numero,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar órdenes por ACO.")
        return []


# =====================================================
# FUNCIÓN: buscar_orden_por_folio()
# =====================================================
def buscar_orden_por_folio(folio):
    """
    Busca una orden por folio.

    PARÁMETROS:
        folio:
            Folio único de la orden.

    RETORNA:
        dict | None:
            Datos de la orden si existe.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_ORDENES)
            .select("*")
            .eq("os_folio", folio)
            .execute()
        )

        if respuesta.data:
            registrar_movimiento_seguro(
                modulo="ORDENES_SERVICIO",
                accion="BUSCAR",
                descripcion=f"Búsqueda de orden de servicio por folio: {folio}",
                registro_afectado=folio,
            )
            return respuesta.data[0]

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="BUSCAR_SIN_RESULTADO",
            descripcion=f"Búsqueda de orden de servicio sin resultado: {folio}",
            registro_afectado=folio,
        )
        return None

    except Exception as error:
        logger.exception("Error al buscar orden.")
        return None


# =====================================================
# FUNCIÓN: actualizar_orden_servicio()
# =====================================================
def actualizar_orden_servicio(id_orden, datos_orden):
    """
    Actualiza una orden existente.

    PARÁMETROS:
        id_orden:
            ID principal de la orden.

        datos_orden:
            Campos a actualizar.

    RETORNA:
        list | None:
            Datos actualizados.
    """

    try:
        datos_orden = normalizar_campos_fecha(datos_orden)

        respuesta = (
            supabase
            .table(TABLA_ORDENES)
            .update(datos_orden)
            .eq("id_orden", id_orden)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="ORDENES_SERVICIO",
            accion="ACTUALIZAR",
            descripcion=f"Actualización de orden de servicio ID: {id_orden}",
            registro_afectado=id_orden,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al actualizar orden.")
        return None


# =====================================================
# FUNCIÓN: obtener_estadisticas_ordenes()
# =====================================================
def obtener_estadisticas_ordenes():
    """
    Obtiene estadísticas generales de órdenes.

    RETORNA:
        tuple:
            Total, pendientes, proceso y finalizadas.
    """

    try:
        ordenes = obtener_ordenes_servicio()

        total = len(ordenes)
        pendientes = len([o for o in ordenes if o.get("os_estatus") == 1])
        proceso = len([o for o in ordenes if o.get("os_estatus") == 2])
        finalizadas = len([o for o in ordenes if o.get("os_estatus") == 3])

        return total, pendientes, proceso, finalizadas

    except Exception as error:
        logger.exception("Error al obtener estadísticas de movimientos.")
        return 0, 0, 0, 0