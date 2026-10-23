"""Servicio para módulo Obra Civil / Proyecto Ejecutivo AXIA."""

from core.logger import configurar_logger
from core.error_reporting import register_error
from core.date_utils import normalizar_campos_fecha
from core.performance import page_range
from supabase_config import supabase
from services.query_compat import execute_select_compatible
from services.movimientos_service import registrar_movimiento_seguro
from services.search_service import buscar_parcial_supabase

logger = configurar_logger(__name__)
TABLA_OBRAS_CIVILES = "db_obras_civiles"
COLUMNAS_OBRAS_CIVILES = "obc_id,obc_aco_numero,obc_anotacion_plano_json,obc_cliente,obc_contacto,obc_direccion,obc_ejecucion_json,obc_entrega_formal,obc_estatus,obc_etapa_acabados,obc_evidencias_json,obc_archivos_adjuntos_json,obc_fecha,obc_fecha_entrega,obc_firma_cliente_base64,obc_firma_tecnico_base64,obc_folio,obc_generacion_planos,obc_nombre_proyecto,obc_obra_blanca,obc_observaciones_finales,obc_observaciones_iniciales,obc_permisos,obc_planos_acabados,obc_planos_arquitectonicos,obc_preentrega_observaciones,obc_preentrega_resultado,obc_pruebas_observaciones,obc_pruebas_resultado,obc_requiere_maquinaria,obc_responsable_axia,obc_sucursal,obc_dias_trabajo,obc_personas_considerar,obc_superficie_adecuada,obc_superficie_disponible,obc_supervisor,obc_tipo_giro,fecha_registro"


def _consultar_solicitud(solicitud: str):
    """Consulta por token opaco; no exige SELECT público sobre Obras Civiles."""
    respuesta = supabase.rpc("axia_obc_consultar_solicitud", {"p_solicitud": str(solicitud)}).execute()
    filas = getattr(respuesta, "data", None) or []
    if isinstance(filas, dict):
        filas = [filas]
    if not isinstance(filas, list):
        raise RuntimeError("Respuesta inesperada al verificar la solicitud de Obra Civil.")
    return filas


def crear_obra_civil(datos_obra):
    """INSERT idempotente por solicitud; nunca recrear un folio calculado."""
    try:
        from uuid import UUID
        datos_obra = dict(datos_obra or {})
        solicitud = str(UUID(str(datos_obra["obc_request_id"])))
        datos_obra["obc_request_id"] = solicitud
        datos_obra.pop("obc_folio", None)
        datos_obra = normalizar_campos_fecha(datos_obra)
        # Antes de insertar, comprueba si esta misma captura ya fue recibida.
        confirmados = _consultar_solicitud(solicitud)
        if confirmados:
            return confirmados
        try:
            respuesta = supabase.table(TABLA_OBRAS_CIVILES).insert(datos_obra).execute()
            registros = getattr(respuesta, "data", None) or []
            if isinstance(registros, list) and registros and registros[0].get("obc_folio") and registros[0].get("obc_id"):
                registrar_movimiento_seguro(
                    modulo="OBRAS_CIVILES", accion="CREAR",
                    descripcion="Creación de registro de obra civil",
                    registro_afectado=registros[0]["obc_folio"],
                )
                return registros
        except Exception:
            # La petición pudo confirmarse en BD antes de perder la red.
            logger.warning("INSERT de Obra Civil sin confirmación: verificando token.", exc_info=True)
        # Incluye respuesta vacía, duplicado del token y conexiones cortadas.
        # Si la consulta RPC también falla, se devuelve None (fail closed).
        confirmados = _consultar_solicitud(solicitud)
        return confirmados or None
    except Exception as error:
        register_error(error, "Registrar obra civil")
        logger.exception("No fue posible verificar o registrar Obra Civil.")
        return None


def obtener_obras_civiles(page=1, page_size=100):
    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_OBRAS_CIVILES,
            COLUMNAS_OBRAS_CIVILES,
            lambda query: query.order("fecha_registro", desc=True).range(*page_range(page, page_size)),
        )
        return respuesta.data
    except Exception:
        logger.exception("Error al consultar obras civiles.")
        return []


def obtener_obras_civiles_por_aco(aco_numero, page=1, page_size=100):
    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_OBRAS_CIVILES,
            COLUMNAS_OBRAS_CIVILES,
            lambda query: query.eq("obc_aco_numero", aco_numero)
            .order("fecha_registro", desc=True)
            .range(*page_range(page, page_size)),
        )
        return respuesta.data
    except Exception:
        logger.exception("Error al consultar obras civiles por ACO.")
        return []


def buscar_obra_civil_por_folio(folio):
    try:
        respuesta = execute_select_compatible(
            supabase,
            TABLA_OBRAS_CIVILES,
            COLUMNAS_OBRAS_CIVILES,
            lambda query: query.eq("obc_folio", str(folio).strip().upper()),
        )
        return respuesta.data[0] if respuesta.data else None
    except Exception as error:
        logger.exception("Error al buscar obra civil por folio.")
        raise RuntimeError("No fue posible consultar la obra civil en Supabase.") from error


# Búsqueda parcial unificada
def buscar_obras_civiles(termino, limite=100):
    resultados = buscar_parcial_supabase(
        supabase=supabase, tabla=TABLA_OBRAS_CIVILES, columnas=COLUMNAS_OBRAS_CIVILES, termino=termino,
        campos=('obc_folio', 'obc_aco_numero', 'obc_cliente', 'obc_sucursal', 'obc_supervisor', 'obc_responsable_axia', 'obc_estatus', 'obc_nombre_proyecto'), id_campos=('obc_id', 'obc_folio'), orden='fecha_registro', limite=limite,
    )
    registrar_movimiento_seguro(
        modulo='OBRAS_CIVILES', accion="BUSCAR",
        descripcion=f"Búsqueda parcial: {str(termino).strip().upper()}",
        registro_afectado=f"Coincidencias: {len(resultados)}",
    )
    return resultados


def actualizar_evidencias_obra_civil(obc_id, evidencias) -> list | None:
    """Asocia metadatos de fotografías de Supabase Storage a la obra civil."""
    try:
        import json
        respuesta = (
            supabase.table(TABLA_OBRAS_CIVILES)
            .update({"obc_evidencias_json": json.dumps(evidencias or [], ensure_ascii=False)})
            .eq("obc_id", obc_id)
            .execute()
        )
        registrar_movimiento_seguro(
            modulo="OBRAS_CIVILES", accion="ACTUALIZAR_EVIDENCIAS",
            descripcion=f"Se asociaron {len(evidencias or [])} evidencia(s) fotográficas",
            registro_afectado=obc_id,
        )
        return respuesta.data
    except Exception as error:
        register_error(error, "Actualizar evidencias de obra civil")
        logger.exception("No fue posible asociar evidencias a obra civil.")
        return None


def actualizar_archivos_obra_civil(obc_id, archivos) -> list | None:
    """Asocia metadatos de PDF/planos de Supabase Storage a la obra civil."""
    try:
        import json
        respuesta = (
            supabase.table(TABLA_OBRAS_CIVILES)
            .update({"obc_archivos_adjuntos_json": json.dumps(archivos or [], ensure_ascii=False)})
            .eq("obc_id", obc_id)
            .execute()
        )
        registrar_movimiento_seguro(
            modulo="OBRAS_CIVILES", accion="ACTUALIZAR_ARCHIVOS",
            descripcion=f"Se asociaron {len(archivos or [])} archivo(s) técnico(s)",
            registro_afectado=obc_id,
        )
        return respuesta.data
    except Exception as error:
        register_error(error, "Actualizar archivos de obra civil")
        logger.exception("No fue posible asociar archivos técnicos a obra civil.")
        return None
