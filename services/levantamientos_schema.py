"""Contrato central de la tabla ``public.db_levantamientos``.

Este módulo es la única fuente de verdad para nombres de columnas y payloads.
Evita que vistas y servicios envíen campos inexistentes a PostgREST.
"""
from __future__ import annotations

from collections.abc import Mapping

TABLA_LEVANTAMIENTOS = "db_levantamientos"

COLUMNAS_LEVANTAMIENTOS_TUPLE = (
    "id_levantamiento",
    "id_aco",
    "lev_aco_numero",
    "id_cliente",
    "lev_cliente",
    "lev_folio",
    "lev_tipo",
    "lev_estatus",
    "lev_prioridad",
    "lev_contacto",
    "lev_telefono",
    "lev_correo",
    "lev_direccion",
    "lev_ubicacion",
    "lev_descripcion",
    "lev_requerimientos",
    "lev_observaciones",
    "lev_tecnico",
    "lev_supervisor",
    "lev_dias_trabajo",
    "lev_personas_considerar",
    "lev_fecha_programada",
    "lev_fecha_realizacion",
    "creado_por",
    "actualizado_por",
    "fecha_registro",
    "fecha_actualizacion",
    "lev_firma_cliente",
    "lev_firma_tecnico",
    "lev_pdf_url",
    "lev_qr_url",
    "id_sucursal",
    "id_contacto",
    "lev_modalidad_operativa",
    "lev_detalle_tecnico_json",
    "lev_equipos_danados_json",
    "lev_descripcion_fallas",
    "lev_anotacion_plano_json",
    "lev_evidencias_json",
)

COLUMNAS_LEVANTAMIENTOS = ",".join(COLUMNAS_LEVANTAMIENTOS_TUPLE)
COLUMNAS_LEVANTAMIENTOS_SET = frozenset(COLUMNAS_LEVANTAMIENTOS_TUPLE)

COLUMNAS_SOLO_LECTURA = frozenset({
    "id_levantamiento",
    "fecha_registro",
    "fecha_actualizacion",
})

COLUMNAS_EDITABLES = COLUMNAS_LEVANTAMIENTOS_SET - COLUMNAS_SOLO_LECTURA

COLUMNAS_FECHA = frozenset({
    "lev_fecha_programada",
    "lev_fecha_realizacion",
    "fecha_registro",
    "fecha_actualizacion",
})

# Compatibilidad controlada con nombres usados por versiones anteriores.
# Nunca se envían estas claves antiguas a Supabase.
ALIAS_LEGACY = {
    "lev_fecha": "lev_fecha_realizacion",
    "lev_firma": "lev_firma_cliente",
    "lev_motivo": "lev_descripcion_fallas",
}

CAMPOS_CONVERSION_EDITABLES = frozenset({
    "lev_aco_numero",
    "lev_cliente",
    "lev_contacto",
    "lev_correo",
    "lev_telefono",
    "lev_direccion",
    "lev_ubicacion",
    "lev_fecha_programada",
    "lev_fecha_realizacion",
    "lev_supervisor",
    "lev_tecnico",
    "lev_dias_trabajo",
    "lev_personas_considerar",
    "lev_tipo",
    "lev_modalidad_operativa",
    "lev_descripcion",
    "lev_requerimientos",
    "lev_observaciones",
    "lev_detalle_tecnico_json",
    "lev_equipos_danados_json",
    "lev_descripcion_fallas",
    "lev_anotacion_plano_json",
    "lev_evidencias_json",
    "lev_prioridad",
})


def normalizar_aliases(datos: Mapping | None) -> dict:
    """Convierte aliases históricos a columnas reales sin sobrescribir la clave real."""
    resultado = dict(datos or {})
    for alias, real in ALIAS_LEGACY.items():
        if real not in resultado and alias in resultado:
            resultado[real] = resultado[alias]
        resultado.pop(alias, None)
    return resultado


def filtrar_payload_levantamiento(
    datos: Mapping | None,
    *,
    permitir_solo_lectura: bool = False,
    campos_permitidos: frozenset[str] | set[str] | None = None,
) -> dict:
    """Devuelve únicamente columnas reales de ``db_levantamientos``.

    ``campos_permitidos`` permite restringir todavía más un flujo, por ejemplo la
    edición administrativa previa a convertir un levantamiento en OS.
    """
    normalizados = normalizar_aliases(datos)
    permitidos = COLUMNAS_LEVANTAMIENTOS_SET if permitir_solo_lectura else COLUMNAS_EDITABLES
    if campos_permitidos is not None:
        permitidos = permitidos.intersection(campos_permitidos)
    return {clave: valor for clave, valor in normalizados.items() if clave in permitidos}
