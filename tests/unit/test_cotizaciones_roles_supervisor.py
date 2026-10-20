"""Regresión: roles de ESI, Supervisor y Jefe de Operaciones en Cotizaciones."""
import ast
from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / 'views' / 'cotizaciones_view.py'
CODIGO = RUTA.read_text(encoding='utf-8')
ARBOL = ast.parse(CODIGO)


def _funcion(anidada):
    return next(n for n in ast.walk(ARBOL) if isinstance(n, ast.FunctionDef) and n.name == anidada)


def _invocaciones(nombre, funcion):
    return [n for n in ast.walk(_funcion(funcion)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == nombre]


def test_selectores_consultan_exclusivamente_supervisor_3_y_jefe_2():
    fragmento = ast.get_source_segment(CODIGO, _funcion('render'))
    assert 'supervisores = obtener_nombres_usuarios_por_tipos([3])' in fragmento
    assert 'jefes_operaciones = obtener_nombres_usuarios_por_tipos([2])' in fragmento
    assert 'estado["supervisores_validos"] = frozenset(supervisores)' in fragmento
    assert 'placeholder="SELECCIONA UN SUPERVISOR"' in fragmento


def test_esi_y_sus_datos_son_campos_inmutables_no_desplegables():
    llamadas = _invocaciones('add_field', 'render')
    claves = {'cot_esi', 'cot_esi_correo', 'cot_esi_telefono'}
    for call in llamadas:
        if len(call.args) >= 7 and isinstance(call.args[5], ast.Constant) and call.args[5].value in claves:
            assert isinstance(call.args[7], ast.Constant) and call.args[7].value is True
    assert not any(
        len(c.args) > 5 and isinstance(c.args[5], ast.Constant) and c.args[5].value == 'cot_esi'
        for c in _invocaciones('add_select', 'render')
    )


def test_usuarios_no_validos_no_pueden_pasarse_como_supervisores():
    fuente = ast.get_source_segment(CODIGO, _funcion('validar_captura_completa'))
    assert 'supervisor not in supervisores_validos' in fuente
    assert 'finalizada_previa and supervisor == supervisor_historico' in fuente


def test_seleccion_supervisor_no_asigna_primero_por_defecto_y_admite_vacio():
    fuente = ast.get_source_segment(CODIGO, _funcion('add_select'))
    assert 'opciones.insert(0, placeholder if hay_personal else "SIN SUPERVISORES REGISTRADOS")' in fuente
    assert 'if not hay_personal:' in fuente
    assert 'menu.configure(state="disabled")' in fuente


def test_guardado_recopila_campos_y_autoria_de_cotizacion_existente():
    fuente = ast.get_source_segment(CODIGO, _funcion('collect'))
    assert 'estado["vars"].items()' in fuente
    render = ast.get_source_segment(CODIGO, _funcion('render'))
    assert 'base.update({k:v for k,v in cot.items() if v is not None})' in render
