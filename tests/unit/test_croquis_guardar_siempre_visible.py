"""Regresiones del acceso a Guardar croquis cuando el pie se recorta en Windows."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / 'views' / 'croquis_editor_view.py'


def _save_function():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    popup = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == 'anotacion_plano_popup')
    # Buscar dentro de la función exterior la función compartida de guardado.
    save_nodes = [n for n in ast.walk(popup) if isinstance(n, ast.FunctionDef)
                  and n.name == 'save']
    assert len(save_nodes) == 1
    return save_nodes[0]


def _invoke_save(should_fail=False):
    class FakeDoc:
        def export_base64(self):
            return 'PNG-BASE64-VALIDO'

    class FakeVar:
        def __init__(self): self.value = None
        def set(self, new):
            if should_fail: raise RuntimeError('fallo simulado')
            self.value = new

    class FakeWin:
        def __init__(self): self.closed = False
        def destroy(self): self.closed = True

    class FakeMessageBox:
        def __init__(self): self.messages = []
        def showerror(self, title, detail, parent=None):
            self.messages.append((title, detail, parent))

    var, win, messages, notifications = FakeVar(), FakeWin(), FakeMessageBox(), []
    ns = dict(variable_base64=var, doc=FakeDoc(), on_change=lambda: notifications.append(True),
              win=win, messagebox=messages)
    code = compile(ast.Module(body=[_save_function()], type_ignores=[]), str(SOURCE), 'exec')
    exec(code, ns)
    ns['save']()
    return var, win, notifications, messages


def test_guardar_superior_e_inferior_usan_la_misma_funcion():
    src = SOURCE.read_text(encoding='utf-8')
    assert 'CTkButton(commands_right, text="Guardar croquis"' in src
    assert 'CTkButton(bottom, text="Guardar croquis"' in src
    assert src.count('command=save).pack(') == 2
    assert src.index('CTkButton(commands_right, text="Guardar croquis"') < src.index('def fit_zoom():')
    assert 'win.bind("<Control-s>", lambda ev: save())' in src
    assert src.index('commands.pack(') < src.index('body.pack(')


def test_guardar_png_y_notificar_funciona_antes_de_cerrar():
    var, win, notifications, messages = _invoke_save()
    assert var.value == 'PNG-BASE64-VALIDO'
    assert notifications == [True]
    assert win.closed
    assert not messages.messages


def test_fallo_de_guardado_no_cierra_ni_confirma_un_cambio():
    var, win, notifications, messages = _invoke_save(should_fail=True)
    assert var.value is None
    assert not notifications
    assert not win.closed
    assert len(messages.messages) == 1
    assert 'fallo simulado' in messages.messages[0][1]
