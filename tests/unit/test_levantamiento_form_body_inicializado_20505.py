"""Regresión: el catálogo solo se carga después de construir el formulario.

En 2.05.04 se invocaba form_body.after() antes de crear form_body,
causando UnboundLocalError al abrir un levantamiento.
"""
import ast
from pathlib import Path

VIEW = Path(__file__).resolve().parents[2] / 'views' / 'levantamiento_view.py'


def test_catalogo_se_programa_despues_de_crear_form_body():
    tree = ast.parse(VIEW.read_text(encoding='utf-8'))
    mostrar = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name == 'mostrar_levantamiento')
    creaciones = [n.lineno for n in ast.walk(mostrar) if isinstance(n, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == 'form_body'
                          for target in n.targets)]
    agenda = [n.lineno for n in ast.walk(mostrar) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == 'after'
              and isinstance(n.func.value, ast.Name) and n.func.value.id == 'form_body'
              and any(isinstance(arg, ast.Name) and arg.id == 'cargar_referencias_almacen'
                      for arg in n.args)]
    assert len(creaciones) == 1
    assert len(agenda) == 1
    assert min(creaciones) < agenda[0], 'Se intenta usar form_body antes de inicializarlo'


def test_catalogo_se_agenda_despues_de_terminar_interfaz():
    code = VIEW.read_text(encoding='utf-8')
    assert code.index('enfocar_inicio_formulario(card)') < code.index('form_body.after(300, cargar_referencias_almacen)')
