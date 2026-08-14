"""Servicio para módulo Obra Civil / Proyecto Ejecutivo AXIA."""

from core.logger import configurar_logger
from core.error_reporting import register_error
from core.date_utils import normalizar_campos_fecha
from core.performance import page_range
from supabase_config import supabase
from services.folios_service import asegurar_folio
from services.query_compat import execute_select_compatible
from services.movimientos_service import registrar_movimiento_seguro
from services.search_service import buscar_parcial_supabase

logger = configurar_logger(__name__)
TABLA_OBRAS_CIVILES = "db_obras_civiles"
COLUMNAS_OBRAS_CIVILES = "id_obra_civil,obc_aco_numero,obc_anotacion_plano_json,obc_cliente,obc_contacto,obc_direccion,obc_ejecucion_json,obc_entrega_formal,obc_estatus,obc_etapa_acabados,obc_evidencias_json,obc_fecha,obc_fecha_entrega,obc_firma_cliente_base64,obc_firma_tecnico_base64,obc_folio,obc_generacion_planos,obc_nombre_proyecto,obc_obra_blanca,obc_observaciones_finales,obc_observaciones_iniciales,obc_permisos,obc_planos_acabados,obc_planos_arquitectonicos,obc_preentrega_observaciones,obc_preentrega_resultado,obc_pruebas_observaciones,obc_pruebas_resultado,obc_requiere_maquinaria,obc_responsable_axia,obc_sucursal,obc_dias_trabajo,obc_personas_considerar,obc_superficie_adecuada,obc_superficie_disponible,obc_supervisor,obc_tipo_giro,fecha_registro"


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
    except Exception as error:
        register_error(error, "Registrar obra civil")
        logger.exception("Error al crear obra civil.")
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
        campos=('obc_folio', 'obc_aco_numero', 'obc_cliente', 'obc_sucursal', 'obc_supervisor', 'obc_responsable_axia', 'obc_estatus', 'obc_nombre_proyecto'), id_campos=('id_obra_civil', 'obc_folio'), orden='fecha_registro', limite=limite,
    )
    registrar_movimiento_seguro(
        modulo='OBRAS_CIVILES', accion="BUSCAR",
        descripcion=f"Búsqueda parcial: {str(termino).strip().upper()}",
        registro_afectado=f"Coincidencias: {len(resultados)}",
    )
    return resultados


def actualizar_evidencias_obra_civil(id_obra_civil, evidencias) -> list | None:
    """Asocia metadatos de fotografías de Supabase Storage a la obra civil."""
    try:
        import json
        respuesta = (
            supabase.table(TABLA_OBRAS_CIVILES)
            .update({"obc_evidencias_json": json.dumps(evidencias or [], ensure_ascii=False)})
            .eq("id_obra_civil", id_obra_civil)
            .execute()
        )
        registrar_movimiento_seguro(
            modulo="OBRAS_CIVILES", accion="ACTUALIZAR_EVIDENCIAS",
            descripcion=f"Se asociaron {len(evidencias or [])} evidencia(s) fotográficas",
            registro_afectado=id_obra_civil,
        )
        return respuesta.data
    except Exception as error:
        register_error(error, "Actualizar evidencias de obra civil")
        logger.exception("No fue posible asociar evidencias a obra civil.")
        return None
