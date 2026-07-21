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
from core.performance import page_range

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro

# =====================================================
# IMPORTACIÓN DE SUPABASE
# =====================================================

from supabase_config import supabase
from services.folios_service import asegurar_folio
from services.query_compat import execute_select_compatible


# =====================================================
# CONSTANTE DE TABLA
# =====================================================

TABLA_ORDENES = "db_ordenes_servicio"
COLUMNAS_ORDENES = "id_orden,os_aco_numero,os_actividad,os_celular,os_cliente,os_correo,os_descripcion,os_domicilio,os_encargado,os_encargado_servicio,os_equipos_json,os_estatus,os_eval_habilidades,os_eval_otro,os_eval_trato,os_eval_velocidad,os_fecha,os_fecha_programada,os_firma_cliente,os_folio,os_hora_llegada,os_hora_salida,os_observaciones,os_prioridad,os_solicitante,os_sucursal,os_supervisor,os_tecnico,os_tecnicos,os_tipo_servicio,os_tipos_servicio_json,fecha_registro"


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
def obtener_ordenes_servicio(page=1, page_size=100):
    """
    Consulta todas las órdenes de servicio.

    RETORNA:
        list:
            Lista de órdenes registradas.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES,
            COLUMNAS_ORDENES,
            lambda query: query
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
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
def obtener_ordenes_por_aco(aco_numero, page=1, page_size=100):
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
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES,
            COLUMNAS_ORDENES,
            lambda query: query
            .eq("os_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
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
        respuesta = execute_select_compatible(
            supabase,
            TABLA_ORDENES,
            COLUMNAS_ORDENES,
            lambda query: query
            .eq("os_folio", str(folio).strip().upper())
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
        logger.exception("Error al buscar orden de servicio.")
        raise RuntimeError("No fue posible consultar la orden de servicio en Supabase.") from error


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
def obtener_estadisticas_ordenes(page=1, page_size=100):
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