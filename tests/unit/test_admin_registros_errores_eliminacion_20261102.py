"""Validaciones locales: describir errores de eliminación sin modificar datos reales."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]

def _formateador():
    ruta = ROOT / 'services/admin_registros_service.py'
    arbol = ast.parse(ruta.read_text(encoding='utf-8'))
    funcion = next(n for n in arbol.body if isinstance(n, ast.FunctionDef)
                   and n.name == '_mensaje_error_servidor')
    ns = {}
    exec(compile(ast.Module(body=[funcion], type_ignores=[]), str(ruta), 'exec'), ns)
    return ns['_mensaje_error_servidor']


def test_error_postgrest_objeto_con_codigo():
    f = _formateador()
    mensaje = f({'error': {'message': 'Registro relacionado', 'code': '23503'}}, 409)
    assert mensaje == 'Registro relacionado (código 23503)'


def test_error_backend_actual_con_codigo():
    f = _formateador()
    mensaje = f({'error': 'No se puede eliminar: relacionado', 'codigo': 'P0001'}, 409)
    assert 'No se puede eliminar' in mensaje
    assert '(código P0001)' in mensaje


def test_error_antiguo_object_object_sugiere_actualizar_edge():
    f = _formateador()
    mensaje = f({'error': '[object Object]'}, 409)
    assert '[object Object]' not in mensaje
    assert 'Actualiza la Edge Function' in mensaje


def test_error_sin_detalle_no_muestra_objetos_python():
    f = _formateador()
    assert 'HTTP 409' in f([], 409)
    assert 'Actualiza' in f({'error': {'code': '23503'}}, 409)


def test_edge_trata_postgrest_como_objeto_y_no_fuerza_eliminaciones():
    edge = (ROOT / 'supabase/functions/axia-admin-registros/index.ts').read_text(encoding='utf-8')
    sql = (ROOT / 'migrations/20261102_admin_registros.sql').read_text(encoding='utf-8')
    assert 'function errorAdministrativo(err: unknown)' in edge
    assert 'return respond(errorAdministrativo(err),409)' in edge
    assert "case '23503'" in edge
    assert 'String(err)' not in edge.split('Deno.serve(async (req)=>{')[1]
    assert 'No se puede eliminar: existen registros relacionados' in sql
    assert 'DELETE FROM public' in sql
