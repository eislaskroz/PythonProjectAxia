"""
=========================================================
SERVICIO DE LEVANTAMIENTOS - AXIA
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
import re
from core.error_reporting import register_error
from core.date_utils import normalizar_campos_fecha
from core.performance import page_range
from core.search_utils import normalizar_termino_busqueda, puntaje_coincidencia

logger = configurar_logger(__name__)
from services.movimientos_service import registrar_movimiento_seguro
from services.search_service import buscar_parcial_supabase

# =====================================================
# IMPORTACIÓN DE SUPABASE
# =====================================================

from supabase_config import supabase
from services.folios_service import solicitar_folio_levantamiento
from services.query_compat import execute_select_compatible
from services.levantamientos_schema import (
    TABLA_LEVANTAMIENTOS,
    COLUMNAS_LEVANTAMIENTOS,
    filtrar_payload_levantamiento,
)


# =====================================================
# CONSTANTE DE TABLA
# =====================================================



# =====================================================
# FUNCIÓN: crear_levantamiento()
# =====================================================
def _es_colision_folio(error):
    """Detecta la restricción única de lev_folio reportada por PostgreSQL/PostgREST."""
    contenido = str(getattr(error, "args", "")) + " " + str(error)
    code = getattr(error, "code", None)
    if isinstance(getattr(error, "args", None), tuple) and error.args and isinstance(error.args[0], dict):
        code = code or error.args[0].get("code")
        contenido += " " + str(error.args[0])
    return str(code or "") == "23505" and "lev_folio" in contenido.lower()


def crear_levantamiento(datos_levantamiento):
    """Crea un levantamiento usando exclusivamente el folio central de Supabase."""
    datos = filtrar_payload_levantamiento(datos_levantamiento)

    try:
        folio_actual = str(datos.get("lev_folio") or "").strip().upper()
        if not re.fullmatch(r"LEV-\d{5,}", folio_actual):
            datos["lev_folio"] = solicitar_folio_levantamiento()

        datos = normalizar_campos_fecha(datos)

        try:
            respuesta = supabase.table(TABLA_LEVANTAMIENTOS).insert(datos).execute()
        except Exception as error:
            if not _es_colision_folio(error):
                raise
            folio_rechazado = datos["lev_folio"]
            datos["lev_folio"] = solicitar_folio_levantamiento()
            logger.warning(
                "Colisión excepcional de folio. Rechazado=%s | Reintento=%s",
                folio_rechazado, datos["lev_folio"],
            )
            registrar_movimiento_seguro(
                modulo="LEVANTAMIENTOS", accion="COLISION_FOLIO",
                descripcion=f"Folio rechazado {folio_rechazado}; reasignado {datos['lev_folio']}",
                registro_afectado=datos["lev_folio"],
            )
            respuesta = supabase.table(TABLA_LEVANTAMIENTOS).insert(datos).execute()

        registrar_movimiento_seguro(
            modulo="LEVANTAMIENTOS",
            accion="CREAR",
            descripcion="Creación de levantamiento",
            registro_afectado=datos.get("lev_folio") or respuesta.data,
        )
        return respuesta.data

    except Exception as error:
        register_error(error, "Registrar levantamiento")
        logger.exception("Error al crear levantamiento.")
        return None

# =====================================================
# FUNCIÓN: obtener_levantamientos()
# =====================================================
def obtener_levantamientos(page=1, page_size=100):
    """
    Consulta todos los levantamientos registrados.

    RETORNA:
        list:
            Lista de levantamientos ordenados del más reciente
            al más antiguo.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_LEVANTAMIENTOS,
            COLUMNAS_LEVANTAMIENTOS,
            lambda query: query
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
        )

        registrar_movimiento_seguro(
            modulo="LEVANTAMIENTOS",
            accion="CONSULTAR",
            descripcion="Consulta general de levantamientos",
            registro_afectado=f"Total: {len(respuesta.data or [])}",
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar levantamientos.")
        return []


# =====================================================
# FUNCIÓN: obtener_levantamientos_por_aco()
# =====================================================
def obtener_levantamientos_por_aco(aco_numero, page=1, page_size=100):
    """
    Consulta los levantamientos relacionados con un ACO.

    PARÁMETROS:
        aco_numero:
            Número de ACO relacionado.

    RETORNA:
        list:
            Lista de levantamientos asociados al ACO.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_LEVANTAMIENTOS,
            COLUMNAS_LEVANTAMIENTOS,
            lambda query: query
            .eq("lev_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size))
        )

        registrar_movimiento_seguro(
            modulo="LEVANTAMIENTOS",
            accion="BUSCAR_POR_ACO",
            descripcion=f"Consulta de levantamientos por ACO: {aco_numero}",
            registro_afectado=aco_numero,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al consultar levantamientos por ACO.")
        return []


# =====================================================
# FUNCIÓN: buscar_levantamientos()
# =====================================================
def buscar_levantamientos(termino, limite=100):
    """Busca coincidencias parciales por folio, ACO y datos relacionados."""
    resultados = buscar_parcial_supabase(
        supabase=supabase, tabla=TABLA_LEVANTAMIENTOS,
        columnas=COLUMNAS_LEVANTAMIENTOS, termino=termino,
        campos=("lev_folio", "lev_aco_numero", "lev_cliente", "lev_ubicacion", "lev_tecnico", "lev_supervisor", "lev_estatus", "lev_tipo"),
        id_campos=("id_levantamiento", "lev_folio"), orden="fecha_registro", limite=limite,
    )
    termino_normalizado = normalizar_termino_busqueda(termino)
    registrar_movimiento_seguro(
        modulo="LEVANTAMIENTOS", accion="BUSCAR",
        descripcion=f"Búsqueda parcial de levantamientos: {termino_normalizado}",
        registro_afectado=f"Coincidencias: {len(resultados)}",
    )
    return resultados


# =====================================================
# FUNCIÓN: buscar_levantamiento_por_folio()
# =====================================================
def buscar_levantamiento_por_folio(folio):
    """
    Busca un levantamiento por folio.

    PARÁMETROS:
        folio:
            Folio único del levantamiento.

    RETORNA:
        dict | None:
            Diccionario con la información del levantamiento
            si existe, o None si no se encuentra.
    """

    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_LEVANTAMIENTOS,
            COLUMNAS_LEVANTAMIENTOS,
            lambda query: query
            .eq("lev_folio", str(folio).strip().upper())
        )

        if respuesta.data:
            registrar_movimiento_seguro(
                modulo="LEVANTAMIENTOS",
                accion="BUSCAR",
                descripcion=f"Búsqueda de levantamiento por folio: {folio}",
                registro_afectado=folio,
            )
            return respuesta.data[0]

        registrar_movimiento_seguro(
            modulo="LEVANTAMIENTOS",
            accion="BUSCAR_SIN_RESULTADO",
            descripcion=f"Búsqueda de levantamiento sin resultado: {folio}",
            registro_afectado=folio,
        )
        return None

    except Exception as error:
        logger.exception("Error al buscar levantamiento.")
        raise RuntimeError("No fue posible consultar el levantamiento en Supabase.") from error


# =====================================================
# FUNCIÓN: actualizar_levantamiento()
# =====================================================
def actualizar_levantamiento(id_levantamiento, datos_levantamiento):
    """
    Actualiza un levantamiento existente.

    PARÁMETROS:
        id_levantamiento:
            ID principal del levantamiento.

        datos_levantamiento:
            Diccionario con los campos a actualizar.

    RETORNA:
        list | None:
            Datos actualizados si la operación fue exitosa.
    """

    try:
        datos_levantamiento = filtrar_payload_levantamiento(datos_levantamiento)
        datos_levantamiento = normalizar_campos_fecha(datos_levantamiento)
        if not datos_levantamiento:
            raise ValueError("No hay campos válidos para actualizar el levantamiento.")

        respuesta = (
            supabase
            .table(TABLA_LEVANTAMIENTOS)
            .update(datos_levantamiento)
            .eq("id_levantamiento", id_levantamiento)
            .execute()
        )

        registrar_movimiento_seguro(
            modulo="LEVANTAMIENTOS",
            accion="ACTUALIZAR",
            descripcion=f"Actualización de levantamiento ID: {id_levantamiento}",
            registro_afectado=id_levantamiento,
        )
        return respuesta.data

    except Exception as error:
        logger.exception("Error al actualizar levantamiento.")
        return None


# =====================================================
# FUNCIÓN: obtener_estadisticas_levantamientos()
# =====================================================
def obtener_estadisticas_levantamientos(page=1, page_size=100):
    """
    Obtiene estadísticas generales de levantamientos.

    RETORNA:
        tuple:
            Total, pendientes, en proceso y realizados.
    """

    try:
        levantamientos = obtener_levantamientos()

        total = len(levantamientos)
        pendientes = len([l for l in levantamientos if l.get("lev_estatus") == 1])
        proceso = len([l for l in levantamientos if l.get("lev_estatus") == 2])
        realizados = len([l for l in levantamientos if l.get("lev_estatus") == 3])

        return total, pendientes, proceso, realizados

    except Exception as error:
        logger.exception("Error al obtener estadísticas de levantamientos.")
        return 0, 0, 0, 0

def actualizar_evidencias_levantamiento(id_levantamiento, evidencias) -> list | None:
    """Actualiza únicamente las evidencias fotográficas del levantamiento recién creado."""
    try:
        import json
        respuesta = (
            supabase.table(TABLA_LEVANTAMIENTOS)
            .update({"lev_evidencias_json": json.dumps(evidencias or [], ensure_ascii=False)})
            .eq("id_levantamiento", id_levantamiento)
            .execute()
        )
        registrar_movimiento_seguro(
            modulo="LEVANTAMIENTOS", accion="ACTUALIZAR_EVIDENCIAS",
            descripcion=f"Se asociaron {len(evidencias or [])} evidencia(s) fotográficas",
            registro_afectado=id_levantamiento,
        )
        return respuesta.data
    except Exception as error:
        register_error(error, "Actualizar evidencias del levantamiento")
        logger.exception("No fue posible asociar evidencias al levantamiento.")
        return None
