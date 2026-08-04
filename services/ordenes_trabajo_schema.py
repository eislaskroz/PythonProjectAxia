"""Contrato central de la tabla ``db_ordenes_trabajo``.

El contrato corresponde a la migración beta_095_sync_supabase_v2.sql. Mantener
los nombres aquí evita que vistas y servicios consulten columnas inexistentes.
"""
from __future__ import annotations

TABLE = "db_ordenes_trabajo"

COLUMNS = (
    "ot_id", "id_aco", "id_sucursal", "id_contacto", "ot_folio", "ot_fecha",
    "ot_aco_numero", "ot_cliente", "ot_contacto", "ot_sucursal",
    "ot_jefe_operacion", "ot_supervisor", "ot_esi", "ot_numero_dias",
    "ot_numero_personas", "ot_asunto", "ot_partidas_json", "ot_descripcion",
    "ot_estatus", "ot_prioridad", "creado_por", "fecha_registro",
    "created_at", "updated_at",
)

SELECT_COLUMNS = ",".join(COLUMNS)
WRITABLE_COLUMNS = frozenset(COLUMNS) - {"ot_id", "fecha_registro", "created_at", "updated_at"}


def filter_payload(payload: dict | None) -> dict:
    """Devuelve solo columnas válidas y editables para INSERT/UPDATE."""
    return {k: v for k, v in dict(payload or {}).items() if k in WRITABLE_COLUMNS}


def metadata_item(folio_os: str) -> dict:
    return {"_axia_meta": {"origen_os": str(folio_os or "").strip().upper()}}


def extract_origin(value) -> str:
    """Obtiene el folio OS guardado dentro de ``ot_partidas_json``."""
    import json
    data = value
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return ""
    if not isinstance(data, list):
        return ""
    for item in data:
        if isinstance(item, dict):
            meta = item.get("_axia_meta")
            if isinstance(meta, dict) and meta.get("origen_os"):
                return str(meta["origen_os"]).strip().upper()
    return ""


def visible_partidas(value) -> list:
    """Elimina elementos internos de metadatos antes de mostrarlos en PDF/UI."""
    import json
    data = value
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and "_axia_meta" not in item]
