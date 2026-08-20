"""Respaldo cifrado y restauración controlada de datos operativos AXIA.

Usa la clave Fernet de AXIA para proteger el archivo local. No sustituye los
backups administrados de PostgreSQL/Supabase, pero ofrece un respaldo portable
de aplicación para contingencias y migraciones controladas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet, InvalidToken
from core.deployment import load_deployment_config
from core.environment import cargar_entorno
from supabase_config import supabase

cargar_entorno()

TABLES = {
    "db_usuarios": ("id_usuario", "id_usuario,usu_nickname,usu_nombre,usu_apellido,usu_rfc,usu_curp,usu_imss,usu_ine,usu_fechanac,usu_telefono,usu_correo,usu_calle,usu_numero,usu_colonia,usu_municipio,usu_estado,usu_cp,usu_regimen,usu_depto,usu_puesto,usu_tipo,usu_auth_id,fecha_registro"),
    "db_clientes": ("id_cliente", "id_cliente,cli_tipo,cli_estatus,cli_razonsocial,cli_rfc,cli_contacto,cli_telefono,cli_correo,cli_calle,cli_numero,cli_colonia,cli_municipio,cli_estado,cli_cp,cli_notas,fecha_registro"),
    "db_clientes_sucursales": ("suc_id", "suc_id,id_cliente,suc_nombre,suc_calle_numero,suc_colonia,suc_municipio,suc_estado,suc_codigo_postal,suc_telefono,suc_correo,suc_domicilio,suc_estatus,fecha_registro"),
    "db_clientes_sucursal_contactos": ("con_id", "con_id,suc_id,con_nombre,con_puesto,con_correo,con_telefono,con_estatus,fecha_registro"),
    "db_acos": ("id_aco", "id_aco,aco_numero,aco_cliente,aco_sucursal,aco_contacto,aco_descripcion,aco_estatus,aco_fecha,fecha_registro"),
    "db_levantamientos": ("id_levantamiento", "id_levantamiento,id_aco,lev_aco_numero,id_cliente,lev_cliente,lev_folio,lev_tipo,lev_estatus,lev_prioridad,lev_contacto,lev_telefono,lev_correo,lev_direccion,lev_ubicacion,lev_descripcion,lev_requerimientos,lev_observaciones,lev_tecnico,lev_supervisor,lev_fecha_programada,lev_fecha_realizacion,creado_por,actualizado_por,fecha_registro,fecha_actualizacion,lev_firma_cliente,lev_firma_tecnico,lev_pdf_url,lev_qr_url,id_sucursal,id_contacto,lev_modalidad_operativa,lev_detalle_tecnico_json,lev_equipos_danados_json,lev_descripcion_fallas,lev_validado_ventas,lev_validado_por,lev_fecha_validacion,lev_cotizacion_json"),
    "db_cotizaciones": ("id_cotizacion", "id_cotizacion,cot_folio,id_levantamiento,lev_folio,id_cliente,cot_cliente,id_sucursal,cot_sucursal,cot_contacto,cot_asunto,cot_fecha,cot_esi,cot_esi_correo,cot_esi_telefono,cot_jefe_operaciones,cot_supervisor,cot_dias,cot_personas,cot_plan_pagos,cot_vigencia,cot_descuento_pct,cot_iva_pct,cot_partidas_json,cot_subtotal,cot_descuento,cot_subtotal_descuento,cot_iva,cot_total,cot_estatus,creado_por,actualizado_por,fecha_registro,fecha_actualizacion"),
    "db_ordenes_servicio": ("id_orden", "id_orden,os_aco_numero,os_actividad,os_celular,os_cliente,os_correo,os_descripcion,os_domicilio,os_encargado,os_encargado_servicio,os_equipos_json,os_estatus,os_eval_habilidades,os_eval_otro,os_eval_trato,os_eval_velocidad,os_fecha,os_fecha_programada,os_firma_cliente,os_folio,os_hora_llegada,os_hora_salida,os_observaciones,os_prioridad,os_solicitante,os_sucursal,os_supervisor,os_tecnico,os_tecnicos,os_tipo_servicio,os_tipos_servicio_json,fecha_registro"),
    "db_ordenes_trabajo": ("ot_id", "ot_id,id_aco,id_sucursal,id_contacto,ot_folio,ot_fecha,ot_aco_numero,ot_cliente,ot_contacto,ot_sucursal,ot_jefe_operacion,ot_supervisor,ot_esi,ot_numero_dias,ot_numero_personas,ot_asunto,ot_partidas_json,ot_descripcion,ot_estatus,ot_prioridad,creado_por,fecha_registro,created_at,updated_at"),
    "db_bitacoras": ("id_bitacora", "id_bitacora,bit_aco_numero,bit_cliente,bit_descripcion,bit_direccion_sucursal,bit_encargado_proyecto_axia,bit_estatus,bit_fecha,bit_folio,bit_hora_llegada,bit_hora_salida,bit_observaciones,bit_porcentaje_avance,bit_tecnico,bit_tecnico_sitio,fecha_registro"),
    "db_obras_civiles": ("id_obra_civil", "id_obra_civil,obc_aco_numero,obc_cliente,obc_contacto,obc_direccion,obc_ejecucion_json,obc_entrega_formal,obc_estatus,obc_etapa_acabados,obc_evidencias_json,obc_fecha,obc_fecha_entrega,obc_firma_cliente_base64,obc_firma_tecnico_base64,obc_folio,obc_generacion_planos,obc_nombre_proyecto,obc_obra_blanca,obc_observaciones_finales,obc_observaciones_iniciales,obc_permisos,obc_planos_acabados,obc_planos_arquitectonicos,obc_preentrega_observaciones,obc_preentrega_resultado,obc_pruebas_observaciones,obc_pruebas_resultado,obc_requiere_maquinaria,obc_responsable_axia,obc_sucursal,obc_superficie_adecuada,obc_superficie_disponible,obc_supervisor,obc_tipo_giro,fecha_registro"),
}


def _fernet() -> Fernet:
    key = (os.getenv("AXIA_DATA_KEY") or "").strip().encode()
    if not key:
        raise RuntimeError("AXIA_DATA_KEY es obligatoria para respaldar o restaurar.")
    return Fernet(key)


def _fetch_all(table: str, columns: str, page_size: int = 500) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        response = supabase.table(table).select(columns).range(start, start + page_size - 1).execute()
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        start += page_size


def create_backup(output_dir: Path) -> Path:
    config = load_deployment_config()
    payload = {
        "format": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "environment": config.environment,
        "project_ref": config.project_ref,
        "tables": {},
    }
    for table, (_, columns) in TABLES.items():
        payload["tables"][table] = _fetch_all(table, columns)
        print(f"{table}: {len(payload['tables'][table])} registros")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encrypted = _fernet().encrypt(raw)
    digest = hashlib.sha256(encrypted).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"AXIA_backup_{config.environment}_{stamp}.axbak"
    path.write_bytes(encrypted)
    path.with_suffix(path.suffix + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return path


def restore_backup(path: Path, allow_production: bool) -> None:
    config = load_deployment_config()
    if config.environment == "production" and not allow_production:
        raise RuntimeError("Restauración en producción bloqueada. Usa --allow-production y confirma el project ref.")
    try:
        payload = json.loads(_fernet().decrypt(path.read_bytes()).decode("utf-8"))
    except InvalidToken as exc:
        raise RuntimeError("No se pudo descifrar el respaldo: llave incorrecta o archivo alterado.") from exc
    source_ref = payload.get("project_ref")
    print(f"Origen: {payload.get('environment')} / {source_ref}")
    print(f"Destino: {config.environment} / {config.project_ref}")
    confirmation = input(f"Escribe el project ref de destino ({config.project_ref}) para restaurar: ").strip()
    if confirmation != config.project_ref:
        raise RuntimeError("Confirmación incorrecta. Restauración cancelada.")
    for table, rows in payload.get("tables", {}).items():
        if table not in TABLES:
            continue
        pk, _ = TABLES[table]
        for start in range(0, len(rows), 100):
            batch = rows[start:start + 100]
            if batch:
                supabase.table(table).upsert(batch, on_conflict=pk).execute()
        print(f"{table}: {len(rows)} restaurados/verificados")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    backup = sub.add_parser("backup")
    backup.add_argument("--output", default="backups")
    restore = sub.add_parser("restore")
    restore.add_argument("file")
    restore.add_argument("--allow-production", action="store_true")
    args = parser.parse_args()
    if args.command == "backup":
        path = create_backup(Path(args.output))
        print(f"Respaldo creado: {path}")
        return 0
    restore_backup(Path(args.file), args.allow_production)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
