"""Pruebas estructurales de seguridad y conservación de borradores."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]


def test_el_guardado_prepara_borrador_antes_de_abrir_red():
    src=(ROOT/'views/obra_civil_view.py').read_text(encoding='utf-8')
    comienzo=src.index('    def guardar_obra():')
    guardar=src[comienzo:src.index('    def _snapshot_borrador_obra()',comienzo)]
    assert guardar.index('if not proteger_captura():') < guardar.index('peticion_obra_civil(')
    assert guardar.index('peticion_obra_civil(') < guardar.index('subir_evidencias_obra_civil(')
    assert 'guardado_servidor["solicitud"]' in guardar
    assert 'CatalogoAxiaLevantamientos' in guardar


def test_seguridad_del_gateway_falla_sin_sesion_y_no_expone_claves():
    code=(ROOT/'services/obra_civil_gateway.py').read_text(encoding='utf-8')
    assert 'obtener_token_sesion_catalogo' in code
    assert 'X-Axia-Almacen-Session' in code
    assert 'SUPABASE_SERVICE_ROLE_KEY' not in code
    assert 'if not token:' in code


def test_cierre_rls_no_elimina_datos():
    sql=(ROOT/'supabase/sql/AXIA_OBRA_CIVIL_CIERRE_RLS_20510.sql').read_text(encoding='utf-8')
    assert 'DROP POLICY IF EXISTS axia_obras_insert_temporal' in sql
    assert 'REVOKE ALL ON FUNCTION public.axia_obc_consultar_solicitud(uuid)' in sql
    assert 'GRANT EXECUTE ON FUNCTION public.axia_obc_consultar_solicitud(uuid) TO service_role' in sql
    assert 'DROP TABLE' not in sql
    assert 'DELETE FROM' not in sql


def test_ventana_obra_sigue_compilando():
    for relative in ['views/obra_civil_view.py','services/obras_civiles_service.py',
                     'services/obra_civil_gateway.py']:
        ast.parse((ROOT/relative).read_text(encoding='utf-8'))
