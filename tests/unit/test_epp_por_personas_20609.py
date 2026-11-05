"""Regresiones: descripción del servicio y EPP automático por cuadrilla."""
from __future__ import annotations

import ast
from pathlib import Path

from services.recursos_epp import EPP_BASICO, personas_para_epp, partidas_epp_basico

ROOT = Path(__file__).resolve().parents[2]


class Variable:
    def __init__(self, value):
        self.value = str(value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = str(value)


def extraer_funcion(path, nombre, globals_dict):
    arbol = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    nodo = next(n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef) and n.name == nombre)
    scope = dict(globals_dict)
    exec(compile(ast.Module(body=[nodo], type_ignores=[]), str(path), "exec"), scope)
    return scope[nombre]


def test_epp_basico_una_partida_por_equipo_y_persona():
    assert len(EPP_BASICO) == 4
    assert [p['cantidad'] for p in partidas_epp_basico('2')] == ['2'] * 4
    assert [p['cantidad'] for p in partidas_epp_basico('5')] == ['5'] * 4
    assert 'Lentes de seguridad' in [p['epp'] for p in partidas_epp_basico('2')]
    assert personas_para_epp('0') == 1  # Valor provisional antes de validar formulario
    assert personas_para_epp('no ingresado') == 1
    assert personas_para_epp('-3') == 1


def test_levantamiento_epp_por_personas_incluye_extras_sin_cambiar_su_cantidad():
    personas, requiere = Variable('2'), Variable('Sí')
    extras = [{'epp': Variable('Guantes dieléctricos'),
               'cantidad': Variable('7'), 'observaciones': Variable('Riesgo eléctrico')}]
    fn = extraer_funcion('views/levantamiento_view.py', 'obtener_epp_json', {
        'tipo_levantamiento': 'Redes Voz y Datos',
        'var_personas_considerar_general': personas,
        'var_requiere_epp': requiere,
        'partidas_epp_basico': partidas_epp_basico,
        'epp_items': extras,
    })
    datos = fn()
    assert len(datos) == 5
    assert [d['cantidad'] for d in datos[:4]] == ['2'] * 4
    assert datos[4]['cantidad'] == '7'
    personas.set('5')
    assert [d['cantidad'] for d in fn()[:4]] == ['5'] * 4
    assert fn()[4]['cantidad'] == '7'
    requiere.set('No')
    assert len(fn()) == 4  # EPP base siempre, extras condicionales


def test_tecnologia_respeta_excepcion_de_epp_que_ya_existia():
    fn = extraer_funcion('views/levantamiento_view.py', 'obtener_epp_json', {
        'tipo_levantamiento': 'Tecnología, Equipos y Periféricos',
        'var_personas_considerar_general': Variable('3'),
        'var_requiere_epp': Variable('No'),
        'partidas_epp_basico': partidas_epp_basico,
        'epp_items': [],
    })
    assert fn() == []


def test_obracivil_epp_automatico_se_recalcula_y_extra_permanece():
    personas = Variable('2')
    items = [dict(epp=Variable(nombre), cantidad=Variable('1'),
                  observaciones=Variable(''), automatico=True) for nombre in EPP_BASICO]
    items.append(dict(epp=Variable('Arnés de cuerpo completo'),
                      cantidad=Variable('1'), observaciones=Variable('Alturas'), automatico=False))
    env = dict(var_requiere_epp=Variable('Sí'), var_personas_considerar=personas,
               epp_items=items, personas_para_epp=personas_para_epp)
    fn = extraer_funcion('views/obra_civil_view.py', 'obtener_epp_obra', env)
    assert [p['cantidad'] for p in fn()] == ['2', '2', '2', '2', '1']
    personas.set('6')
    assert [p['cantidad'] for p in fn()] == ['6', '6', '6', '6', '1']
    assert fn()[-1]['observaciones'] == 'Alturas'
    env['var_requiere_epp'].set('No')
    assert fn() == []


def test_etiqueta_visible_unificada_y_columna_json_sin_renombrar():
    lev = (ROOT / 'views/levantamiento_view.py').read_text(encoding='utf-8')
    obc = (ROOT / 'views/obra_civil_view.py').read_text(encoding='utf-8')
    assert 'titulo_observaciones = "Descripción detallada del servicio"' in lev
    assert 'campo_texto("Descripción detallada del servicio"' in lev
    assert 'textbox("Descripción detallada del servicio"' in obc
    assert '"lev_observaciones":' in lev
    assert '"obc_observaciones_finales":' in obc


def test_pdf_obra_civil_no_pierde_cantidades_y_etiqueta():
    src = (ROOT / 'services/obras_civiles_universal.py').read_text(encoding='utf-8')
    assert "p.get('cantidad')" in src
    assert "'Descripción detallada del servicio': obra.get('obc_observaciones_finales')" in src
