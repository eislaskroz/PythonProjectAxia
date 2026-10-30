"""Comprobar el contrato real de Obra Civil contra el esquema recibido en CSV."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
REAL_COLUMNS = {
    "obc_id", "obc_folio", "obc_fecha", "obc_aco_numero", "obc_cliente", "obc_contacto",
    "obc_sucursal", "obc_direccion", "obc_responsable_axia", "obc_supervisor", "obc_tipo_giro",
    "obc_nombre_proyecto", "obc_superficie_disponible", "obc_superficie_adecuada",
    "obc_planos_arquitectonicos", "obc_requiere_maquinaria", "obc_permisos",
    "obc_observaciones_iniciales", "obc_ejecucion_json", "obc_pruebas_resultado",
    "obc_pruebas_observaciones", "obc_planos_acabados", "obc_generacion_planos",
    "obc_etapa_acabados", "obc_obra_blanca", "obc_evidencias_json",
    "obc_preentrega_resultado", "obc_preentrega_observaciones", "obc_entrega_formal",
    "obc_fecha_entrega", "obc_observaciones_finales", "obc_firma_cliente_base64",
    "obc_firma_tecnico_base64", "obc_estatus", "creado_por", "fecha_registro",
    "created_at", "updated_at", "id_aco", "id_sucursal", "id_contacto",
    "obc_dias_trabajo", "obc_personas_considerar", "obc_anotacion_plano_json",
    "obc_archivos_adjuntos_json",
}


def test_servicio_consulta_solo_columnas_del_esquema_real():
    s = (ROOT / "services/obras_civiles_service.py").read_text(encoding="utf-8")
    node = ast.parse(s)
    column_value = next(
        n.value.value for n in node.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "COLUMNAS_OBRAS_CIVILES" for t in n.targets)
    )
    assert set(column_value.split(',')) <= REAL_COLUMNS
    assert '"obc_id"' in s
    assert '"id_obra_civil"' not in s


def test_migracion_rpc_devuelve_pk_correcta_y_no_borra_datos():
    sql = (ROOT / "supabase/migrations/20261023_obras_civiles_folio_idempotente.sql").read_text(encoding="utf-8")
    assert "RETURNS TABLE (obc_id text, obc_folio text)" in sql
    assert "SELECT oc.obc_id::text, oc.obc_folio::text" in sql
    assert "id_obra_civil" not in sql.replace('PK inexistente id_obra_civil', '')
    assert "DROP TABLE" not in sql.upper()
    assert "DELETE FROM public.db_obras_civiles" not in sql


def test_service_view_and_backup_use_pk_of_real_table():
    for path in (
        "services/obras_civiles_service.py",
        "views/obra_civil_view.py",
        "tools/backup_restore.py",
    ):
        source = (ROOT / path).read_text(encoding="utf-8")
        assert "id_obra_civil" not in source
        assert "obc_id" in source
    backups = (ROOT / 'tools/backup_restore.py').read_text(encoding='utf-8')
    assert '"db_obras_civiles": ("obc_id", "obc_id,' in backups
    assert 'obc_request_id' in backups


def test_pk_in_response_for_retry():
    src = (ROOT / 'services/obras_civiles_service.py').read_text(encoding='utf-8')
    assert "peticion_obra_civil('guardar'" in src
    edge = (ROOT / 'supabase/functions/axia-obras-civiles/index.ts').read_text(encoding='utf-8')
    assert "select('obc_id,obc_folio,obc_request_id')" in edge
    assert '"obc_id"' in (ROOT / 'views/obra_civil_view.py').read_text(encoding='utf-8')
