"""Regression checks for the footer overlay reported in AXIA Desktop.

These checks intentionally inspect the view source without importing the GUI or
connecting to the backend: they can run in a headless build environment.
"""
from pathlib import Path
import ast

VIEW = Path(__file__).resolve().parents[2] / 'views' / 'levantamiento_view.py'


def _source():
    return VIEW.read_text(encoding='utf-8-sig')


def test_pending_button_separated_from_main_action_bar():
    source = _source()
    assert 'barra_botones, text="Ver campos pendientes"' not in source
    assert 'fila_estado_preview, text="Ver campos pendientes"' in source
    assert 'btn_ver_pendientes.grid(row=0, column=1, sticky="e")' in source
    assert 'lbl_faltantes_preview.grid(row=0, column=0' in source
    assert 'barra_botones,\n        text="Cancelar"' in source
    # The single bottom action row reserves four distinct columns.
    for col in range(4):
        assert f'.grid(row=0, column={col}, padx=4)' in source


def test_footer_grows_for_status_row_and_retains_help_action():
    source = _source()
    tree = ast.parse(source)
    assert 'height=106' in source
    assert 'fila_estado_preview.grid_columnconfigure(0, weight=1)' in source
    assert 'fila_estado_preview.bind("<Configure>", ajustar_ancho_aviso_preview' in source
    assert 'command=mostrar_campos_pendientes' in source
    assert 'btn_ver_pendientes.configure(state="normal" if faltantes else "disabled")' in source
    assert any(isinstance(node, ast.FunctionDef) and node.name == 'actualizar_estado_preview'
               for node in ast.walk(tree))
