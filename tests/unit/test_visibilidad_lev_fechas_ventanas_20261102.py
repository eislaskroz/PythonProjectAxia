"""Regresiones: visibilidad de LEV, representación de fechas y ventanas AXIA."""
from __future__ import annotations
import ast
from pathlib import Path
from datetime import datetime

from core.date_utils import formatear_fecha_visual, fecha_desde_vista, fecha_para_vista
from security.permissions import obtener_tipo_usuario, JEFE_OPERACIONES, SUPERVISOR

ROOT = Path(__file__).resolve().parents[2]


def _funcion_aislada(nombre):
    codigo = ast.parse((ROOT / 'services/levantamientos_service.py').read_text(encoding='utf8'))
    nodes = [n for n in codigo.body if isinstance(n, ast.FunctionDef) and n.name == nombre]
    assert len(nodes) == 1
    scope = {'obtener_usuario_actual': lambda: None, 'obtener_tipo_usuario': obtener_tipo_usuario,
             'JEFE_OPERACIONES': JEFE_OPERACIONES, 'SUPERVISOR': SUPERVISOR}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<lev>', 'exec'), scope)
    return scope[nombre]


def test_unicamente_jefe_y_supervisor_ven_todos():
    policy = _funcion_aislada('_filtro_autor_levantamiento')
    for role in (2, 3):
        assert policy({'id_usuario': 10, 'usuario': 'usuario_a', 'usu_tipo': role}) == (None, True)
    for role in (1, 4, 5, 6, 7, 8):
        assert policy({'id_usuario': 10, 'usuario': 'usuario_a', 'usu_tipo': role}) == ('usuario_a', True)
    assert policy({'id_usuario': None, 'usuario': 'usuario_a', 'usu_tipo': 3}) == (None, False)
    assert policy({'id_usuario': 10, 'usuario': 'DESCONOCIDO', 'usu_tipo': 2}) == (None, False)


def test_el_filtro_se_agrega_al_query_antes_de_buscar():
    aplicar = _funcion_aislada('_aplicar_filtro_autor')
    class Query:
        def __init__(self): self.filtros=[]
        def eq(self, col, value): self.filtros.append((col,value)); return self
    q=Query()
    assert aplicar(q,'erick') is q
    assert q.filtros == [('creado_por','erick')]
    q2=Query()
    assert aplicar(q2,None) is q2 and not q2.filtros
    fuente=(ROOT / 'services/search_service.py').read_text(encoding='utf8')
    assert fuente.index('query = filtro_query(query)') < fuente.index('query = query.ilike(')


def test_fecha_lectura_iso_fecha_espania_y_no_fecha():
    assert formatear_fecha_visual('2026-11-02') == '02/11/2026 00:00:00'
    assert formatear_fecha_visual('2026-11-02T14:35:08') == '02/11/2026 14:35:08'
    assert formatear_fecha_visual('02/11/2026') == '02/11/2026 00:00:00'
    assert fecha_para_vista('lev_cliente', '2026-11-02') == '2026-11-02'
    assert formatear_fecha_visual('dato no válido') == 'dato no válido'
    assert formatear_fecha_visual(None) == ''


def test_fecha_editor_no_cambia_si_no_se_modifico():
    assert fecha_desde_vista('02/11/2026 00:00:00','2026-11-02') == '2026-11-02'
    assert fecha_desde_vista('03/11/2026 00:00:00','2026-11-02') == '2026-11-03'
    assert fecha_desde_vista('03/11/2026 14:45:10','2026-11-02T14:33:00') == '2026-11-03T14:45:10'


def test_modal_admin_tiene_centrado():
    source = (ROOT / 'views/admin_registros_view.py').read_text(encoding='utf8')
    assert 'centrar_ventana(ventana, 920, 710, padre=root)' in source
    assert 'centrar_ventana(win, 980, 520, padre=root)' in source
