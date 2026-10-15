"""Regresión: abrir o editar un levantamiento no puede disparar NameError.

Prueba el código real de los callbacks extraído por AST, sin crear una
ventana Tk ni conectarse a Supabase. Simula restauración de StringVar y
varios cambios rápidos después de construir el formulario.
"""
from __future__ import annotations
import ast
from pathlib import Path

VIEW = Path(__file__).resolve().parents[2] / 'views' / 'levantamiento_view.py'
TEXT = VIEW.read_text(encoding='utf-8-sig')
TREE = ast.parse(TEXT)
FORM = next(n for n in TREE.body if isinstance(n, ast.FunctionDef)
            and n.name == 'mostrar_levantamiento')


def _pos(name):
    return min(n.lineno for n in ast.walk(FORM)
               if isinstance(n, ast.FunctionDef) and n.name == name)


def test_planificador_declarado_antes_de_los_traces_y_restauracion():
    callbacks_trace = [n.lineno for n in ast.walk(FORM)
                       if isinstance(n, ast.Lambda)
                       and any(isinstance(ref, ast.Name)
                               and ref.id == 'programar_actualizacion_estado_preview'
                               for ref in ast.walk(n))]
    assert callbacks_trace, 'No se identificaron observadores de cambios.'
    assert _pos('programar_actualizacion_estado_preview') < min(callbacks_trace)
    assert _pos('actualizar_estado_preview') < _pos('programar_actualizacion_estado_preview')
    assert _pos('_actualizar_estado_preview_impl') > _pos('programar_actualizacion_estado_preview')
    assert '_preview_lista_activa = True\n    actualizar_estado_preview()' in TEXT


def test_planificador_no_se_ejecuta_durante_restauracion_y_tiene_debounce():
    callbacks = [n for n in FORM.body if isinstance(n, ast.FunctionDef)
                 and n.name in {'actualizar_estado_preview', 'programar_actualizacion_estado_preview'}]
    assert len(callbacks) == 2
    class Frame:
        def __init__(self):
            self.jobs = {}
            self.cancelled = []
        def after(self, delay, fn):
            id_ = len(self.jobs) + 1
            self.jobs[id_] = fn
            return id_
        def after_cancel(self, id_):
            self.cancelled.append(id_)
            self.jobs.pop(id_, None)
    frame = Frame()
    class Logger:
        def debug(self, *args, **kwargs): pass
    # Cuerpo extraído literalmente del módulo de producción.
    # Las funciones comparten el cierre local igual que en mostrar_levantamiento.
    body = '\n'.join('    ' + line for n in callbacks
                     for line in ast.get_source_segment(TEXT, n).splitlines())
    source = '''def harness():
    form_body = frame
    _preview_lista_activa = False
    _preview_after_id = None
    calls = []
    def _actualizar_estado_preview_impl():
        calls.append('validado')
''' + body + '''
    programar_actualizacion_estado_preview()  # restauración de datos
    actualizar_estado_preview()  # callbacks de elementos condicionales
    assert not frame.jobs and not calls
    _preview_lista_activa = True
    actualizar_estado_preview()  # validación inicial
    programar_actualizacion_estado_preview()  # escribir dato
    programar_actualizacion_estado_preview()  # segunda tecla
    assert len(frame.jobs) == 1 and len(frame.cancelled) == 1
    list(frame.jobs.values())[0]()
    return calls
'''
    namespace = {'frame': frame, 'logger': Logger()}
    exec(source, namespace)
    assert namespace['harness']() == ['validado', 'validado']
