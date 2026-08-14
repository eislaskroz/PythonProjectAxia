"""Catálogo Supabase de conceptos de Obra Civil AXIA."""

from core.logger import configurar_logger
from supabase_config import supabase
from services.query_compat import execute_select_compatible

logger = configurar_logger(__name__)

TABLA_OBRA_CONCEPTOS = "db_obra_conceptos"
COLUMNAS_OBRA_CONCEPTOS = (
    "id_obra_concepto,obra_catalogo_ref,obra_tipo,obra_partida,obra_unidad,"
    "obra_concepto,obra_precio_unitario,obra_activo"
)


def obtener_conceptos_obra(activos=True):
    """Devuelve el catálogo de conceptos ordenado por tipo, partida e id.

    Si la migración aún no fue ejecutada, devuelve una lista vacía para no romper
    el formulario de levantamiento.
    """
    try:
        def aplicar(query):
            if activos:
                query = query.eq("obra_activo", True)
            return query.order("obra_tipo").order("obra_partida").order("id_obra_concepto")

        respuesta = execute_select_compatible(
            supabase,
            TABLA_OBRA_CONCEPTOS,
            COLUMNAS_OBRA_CONCEPTOS,
            aplicar,
        )
        return respuesta.data or []
    except Exception:
        logger.exception("No fue posible consultar el catálogo de conceptos de obra civil.")
        return []


def obtener_tipos_concepto_obra(conceptos=None):
    conceptos = conceptos if conceptos is not None else obtener_conceptos_obra()
    return sorted(
        {str(item.get("obra_tipo") or "").strip() for item in conceptos if str(item.get("obra_tipo") or "").strip()},
        key=str.casefold,
    )


def filtrar_conceptos_por_tipo(tipo, conceptos=None):
    conceptos = conceptos if conceptos is not None else obtener_conceptos_obra()
    tipo_norm = str(tipo or "").strip()
    return [item for item in conceptos if str(item.get("obra_tipo") or "").strip() == tipo_norm]
