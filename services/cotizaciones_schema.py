"""Contrato de persistencia de cotizaciones comerciales AXIA."""

TABLA_COTIZACIONES = "db_cotizaciones"

COLUMNAS_COTIZACIONES_TUPLE = (
    "id_cotizacion", "cot_folio", "id_levantamiento", "lev_folio", "id_cliente",
    "cot_cliente", "id_sucursal", "cot_sucursal", "cot_contacto", "cot_asunto",
    "cot_fecha", "cot_esi", "cot_esi_correo", "cot_esi_telefono",
    "cot_jefe_operaciones", "cot_supervisor", "cot_dias", "cot_personas",
    "cot_plan_pagos", "cot_vigencia", "cot_descuento_pct", "cot_iva_pct",
    "cot_partidas_json", "cot_subtotal", "cot_descuento", "cot_subtotal_descuento",
    "cot_iva", "cot_total", "cot_estatus", "cot_finalizado_por",
    "cot_fecha_finalizacion", "creado_por", "actualizado_por",
    "fecha_registro", "fecha_actualizacion",
)

COLUMNAS_COTIZACIONES = ",".join(COLUMNAS_COTIZACIONES_TUPLE)
