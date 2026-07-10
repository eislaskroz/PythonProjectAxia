"""
=========================================================
SERVICIO DE BITÁCORAS DE AVANCE - AXIA
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

from supabase_config import supabase
from services.folios_service import asegurar_folio

TABLA_BITACORAS = "db_bitacoras"


# =====================================================
# FUNCIÓN: crear_bitacora()
# =====================================================
def crear_bitacora(datos_bitacora):
    """
    Crea una nueva bitácora operativa.
    """

    try:
        datos_bitacora = asegurar_folio(datos_bitacora, "bit_folio", "BIT")
        datos_bitacora = normalizar_campos_fecha(datos_bitacora)

        respuesta = (
            supabase
            .table(TABLA_BITACORAS)
            .insert(datos_bitacora)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="BITACORAS_OPERATIVAS",
            accion="CREAR",
            descripcion="Creación de bitácora operativa",
            registro_afectado=datos_bitacora.get("bit_folio") or respuesta.data,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al crear bitácora.")
        return None


# =====================================================
# FUNCIÓN: obtener_bitacoras()
# =====================================================
def obtener_bitacoras():
    """
    Obtiene todas las bitácoras registradas.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_BITACORAS)
            .select("*")
            .order("fecha_registro", desc=True)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="BITACORAS_OPERATIVAS",
            accion="CONSULTAR",
            descripcion="Consulta general de bitácoras operativas",
            registro_afectado=f"Total: {len(respuesta.data or [])}",
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar bitácoras.")
        return []


# =====================================================
# FUNCIÓN: obtener_bitacoras_por_aco()
# =====================================================
def obtener_bitacoras_por_aco(aco_numero):
    """
    Obtiene bitácoras relacionadas con un ACO.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_BITACORAS)
            .select("*")
            .eq("bit_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="BITACORAS_OPERATIVAS",
            accion="BUSCAR_POR_ACO",
            descripcion=f"Consulta de bitácoras por ACO: {aco_numero}",
            registro_afectado=aco_numero,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar bitácoras por ACO.")
        return []


# =====================================================
# FUNCIÓN: buscar_bitacora_por_folio()
# =====================================================
def buscar_bitacora_por_folio(folio):
    """
    Busca una bitácora por folio.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_BITACORAS)
            .select("*")
            .eq("bit_folio", folio)
            .execute()
        )

        if respuesta.data:
            registrar_movimiento_seguro(
                modulo="BITACORAS_OPERATIVAS",
                accion="BUSCAR",
                descripcion=f"Búsqueda de bitácora por folio: {folio}",
                registro_afectado=folio,
            )
            return respuesta.data[0]

        registrar_movimiento_seguro(
            modulo="BITACORAS_OPERATIVAS",
            accion="BUSCAR_SIN_RESULTADO",
            descripcion=f"Búsqueda de bitácora sin resultado: {folio}",
            registro_afectado=folio,
        )
        return None

    except Exception as error:
        logger.exception("Error al buscar bitácora.")
        return None


# =====================================================
# FUNCIÓN: actualizar_bitacora()
# =====================================================
def actualizar_bitacora(id_bitacora, datos_bitacora):
    """
    Actualiza una bitácora existente.
    """

    try:
        respuesta = (
            supabase
            .table(TABLA_BITACORAS)
            .update(datos_bitacora)
            .eq("id_bitacora", id_bitacora)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="BITACORAS_OPERATIVAS",
            accion="ACTUALIZAR",
            descripcion=f"Actualización de bitácora operativa ID: {id_bitacora}",
            registro_afectado=id_bitacora,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al actualizar bitácora.")
        return None


# =====================================================
# FUNCIÓN: obtener_estadisticas_bitacoras()
# =====================================================
def obtener_estadisticas_bitacoras():
    """
    Obtiene estadísticas generales de bitácoras.
    """

    try:
        bitacoras = obtener_bitacoras()

        total = len(bitacoras)

        pendientes = len([
            b for b in bitacoras
            if b.get("bit_estatus") == 1
        ])

        proceso = len([
            b for b in bitacoras
            if b.get("bit_estatus") == 2
        ])

        finalizadas = len([
            b for b in bitacoras
            if b.get("bit_estatus") == 3
        ])

        return total, pendientes, proceso, finalizadas

    except Exception as error:
        logger.exception("Error al obtener estadísticas de movimientos.")
        return 0, 0, 0, 0