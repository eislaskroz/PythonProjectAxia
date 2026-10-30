"""Regresiones de Obra Civil: captura manual sin depender del catálogo."""
from __future__ import annotations

import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / 'views' / 'obra_civil_view.py'
TEXT = SOURCE.read_text(encoding='utf-8')
TREE = ast.parse(TEXT)
FORM = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'mostrar_obra_civil')


def nested_function(name):
    item = next(n for n in FORM.body if isinstance(n, ast.FunctionDef) and n.name == name)
    env = {}
    exec(compile(ast.Module(body=[item], type_ignores=[]), str(SOURCE), 'exec'), env)
    return env[name]


class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


def test_concepto_otros_serializa_una_partida_sin_catalogo():
    # Se prueba el código real de serialización, no una copia de su algoritmo.
    node = next(n for n in FORM.body if isinstance(n, ast.FunctionDef) and n.name == 'obtener_conceptos_obra_seleccionados')
    globals_ = {
        'TIPO_CONCEPTO_OTROS': 'OTROS',
        'conceptos_obra_items': [{
            'tipo': Var('OTROS'), 'concepto_label': Var('Pintura especial a solicitud del cliente'),
            'unidad': Var('m²'), 'cantidad': Var('12.5'), 'registro': {},
        }],
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), globals_)
    row = globals_['obtener_conceptos_obra_seleccionados']()[0]
    assert row['tipo'] == 'OTROS'
    assert row['concepto'] == 'Pintura especial a solicitud del cliente'
    assert row['unidad'] == 'm²'
    assert row['cantidad'] == '12.5'
    assert row['id_obra_concepto'] is None
    assert row['catalogo_ref'] is None


def test_concepto_catalogado_no_pierde_sus_referencias():
    node = next(n for n in FORM.body if isinstance(n, ast.FunctionDef) and n.name == 'obtener_conceptos_obra_seleccionados')
    globals_ = {
        'TIPO_CONCEPTO_OTROS': 'OTROS',
        'conceptos_obra_items': [{
            'tipo': Var('ACABADOS'), 'cantidad': Var('2'),
            'registro': {'id_obra_concepto': 3, 'obra_catalogo_ref': 'ACA-03',
                         'obra_tipo': 'ACABADOS', 'obra_partida': 'ACA-03',
                         'obra_unidad': 'm²', 'obra_concepto': 'Pintura',
                         'obra_precio_unitario': 55},
        }],
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), globals_)
    row = globals_['obtener_conceptos_obra_seleccionados']()[0]
    assert row['id_obra_concepto'] == 3
    assert row['catalogo_ref'] == 'ACA-03'
    assert row['cantidad'] == '2'


def test_formulario_mantiene_captura_otros_y_respaldo():
    for fragment in (
        'OPCION_CLIENTE_OTROS = "Otros"',
        'activar_captura_manual(conservar_datos=True)',
        '"cliente_manual": modo_manual_cliente["activo"]',
        '"conceptos_obra": obtener_conceptos_obra_seleccionados()',
        'eunidad.configure(state="normal")',
        'TIPO_CONCEPTO_OTROS = "OTROS"',
    ):
        assert fragment in TEXT


def test_separacion_folio_e_identificadores_manual():
    assert 'entry("Folio OBC", var_folio, 1, 0, "Automático", state="disabled"' in TEXT
    assert '"id_sucursal": (None if modo_manual_cliente["activo"] else' in TEXT
    assert '"id_contacto": (None if modo_manual_cliente["activo"] else' in TEXT
