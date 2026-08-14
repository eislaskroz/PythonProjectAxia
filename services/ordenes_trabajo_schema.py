"""Contrato central de la tabla ``db_ordenes_trabajo``.

El contrato corresponde a la migración beta_095_sync_supabase_v2.sql. Mantener
los nombres aquí evita que vistas y servicios consulten columnas inexistentes.
"""
from __future__ import annotations

TABLE = "db_ordenes_trabajo"

COLUMNS = (
    "ot_id", "id_aco", "id_sucursal", "id_contacto", "id_levantamiento",
    "ot_folio_levantamiento", "ot_folio", "ot_fecha",
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


def metadata_item(folio: str, tipo: str = "os") -> dict:
    """Crea metadato interno de trazabilidad sin exponerlo en PDF/UI."""
    tipo = str(tipo or "os").strip().lower()
    clave = "origen_lev" if tipo in {"lev", "levantamiento"} else "origen_os"
    return {"_axia_meta": {clave: str(folio or "").strip().upper()}}


def extract_origin(value, tipo: str = "os") -> str:
    """Obtiene el folio de origen guardado dentro de ``ot_partidas_json``."""
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
            if isinstance(meta, dict):
                tipo_norm = str(tipo or "os").strip().lower()
                clave = "origen_lev" if tipo_norm in {"lev", "levantamiento"} else "origen_os"
                if meta.get(clave):
                    return str(meta[clave]).strip().upper()
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



def partidas_desde_detalle_levantamiento(detalle) -> list[dict]:
    """Extrae partidas operativas reales desde el JSON técnico de un LEV.

    Solo toma colecciones de MATERIALES, EQUIPOS y MISCELÁNEOS/CONSUMIBLES.
    Nunca convierte resúmenes narrativos, diagnóstico, alcance, servicio ni
    conceptos generales del levantamiento en partidas del PDF de OT.
    """
    import json
    from collections.abc import Mapping

    if isinstance(detalle, str):
        try:
            detalle = json.loads(detalle) if detalle.strip() else {}
        except Exception:
            detalle = {}
    if not isinstance(detalle, Mapping):
        return []

    rows = []
    seen = set()

    def text(value):
        return str(value or "").strip()

    def add(*, unidad="", cantidad="", modelo="", marca="", concepto="", grupo="Materiales"):
        concepto = text(concepto)
        if not concepto:
            return
        row = {
            "partida": str(len(rows) + 1),
            "unidad": text(unidad),
            "cantidad": text(cantidad),
            "modelo": text(modelo),
            "marca": text(marca),
            "concepto": concepto,
            "_grupo": text(grupo) or "Materiales",
        }
        signature = tuple(row[k].casefold() for k in ("unidad", "cantidad", "modelo", "marca", "concepto"))
        if signature in seen:
            return
        seen.add(signature)
        rows.append(row)

    def walk(node):
        if not isinstance(node, Mapping):
            return
        for key, value in node.items():
            key_norm = str(key or "").strip().casefold()
            if isinstance(value, str) and value.strip()[:1] in "[{":
                try:
                    value = json.loads(value)
                except Exception:
                    pass

            if isinstance(value, (list, tuple)) and value and all(isinstance(x, Mapping) for x in value):
                if key_norm in {"canalizacion_materiales", "canalizacion_cableado_materiales", "partidas_canalizacion"} or "canalizacion" in key_norm:
                    for item in value:
                        spec = text(item.get("tamano_calibre_especificacion") or item.get("tamano") or item.get("calibre") or item.get("especificacion"))
                        concepto = " - ".join(filter(None, [text(item.get("categoria")), text(item.get("tipo")), spec]))
                        add(unidad=item.get("unidad"), cantidad=item.get("cantidad"), concepto=concepto, grupo="Materiales")
                    continue
                if key_norm in {"equipos_principales", "equipos", "equipos_requeridos"} or "equipos_principales" in key_norm:
                    for item in value:
                        base = " - ".join(filter(None, [text(item.get("familia")), text(item.get("subfamilia"))]))
                        car = text(item.get("caracteristicas") or item.get("caracteristicas_tecnicas"))
                        concepto = base + (f" - {car}" if car else "")
                        add(unidad=item.get("unidad") or "Pieza(s)", cantidad=item.get("cantidad"), modelo=item.get("modelo"), marca=item.get("marca"), concepto=concepto, grupo="Equipos")
                    continue
                if key_norm in {"materiales_miscelaneos", "materiales_misceláneos", "consumibles", "materiales"} or "miscel" in key_norm:
                    for item in value:
                        material = text(item.get("material") or item.get("concepto") or item.get("descripcion"))
                        spec = text(item.get("especificacion") or item.get("medida"))
                        concepto = material + (f" - {spec}" if spec and spec.casefold() not in {"n/a", "no aplica"} else "")
                        add(unidad=item.get("unidad"), cantidad=item.get("cantidad"), modelo=item.get("modelo"), marca=item.get("marca"), concepto=concepto, grupo="Misceláneos")
                    continue
                # Cualquier otra lista (diagnóstico, alcance, actividades, conceptos
                # generales, etc.) se ignora deliberadamente para la tabla de OT.
                for item in value:
                    walk(item)
            elif isinstance(value, Mapping):
                # Algunas variantes guardan materiales/canalización dentro de un
                # objeto con una colección ``partidas``. Solo se acepta cuando el
                # nombre de la sección identifica inequívocamente materiales.
                nested = value.get("partidas")
                es_materiales = (
                    "canalizacion" in key_norm or "material" in key_norm or
                    "miscel" in key_norm or "consumible" in key_norm
                )
                if es_materiales and isinstance(nested, (list, tuple)) and nested and all(isinstance(x, Mapping) for x in nested):
                    for item in nested:
                        spec = text(item.get("tamano_calibre_especificacion") or item.get("tamano") or item.get("calibre") or item.get("especificacion"))
                        material = text(item.get("material") or item.get("concepto") or item.get("descripcion"))
                        concepto = material or " - ".join(filter(None, [text(item.get("categoria")), text(item.get("tipo")), spec]))
                        if material and spec and spec.casefold() not in {"n/a", "no aplica"}:
                            concepto = f"{material} - {spec}"
                        grupo = "Misceláneos" if ("miscel" in key_norm or "consumible" in key_norm) else "Materiales"
                        add(unidad=item.get("unidad"), cantidad=item.get("cantidad"), modelo=item.get("modelo"), marca=item.get("marca"), concepto=concepto, grupo=grupo)
                walk(value)

    walk(detalle)
    for index, row in enumerate(rows, 1):
        row["partida"] = str(index)
    return rows
