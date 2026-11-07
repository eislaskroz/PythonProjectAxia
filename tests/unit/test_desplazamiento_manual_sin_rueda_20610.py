"""Regresiones de AXIA: barra lateral sí, rueda del mouse no."""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import Mock

from ui.manual_scroll_policy import install_manual_scroll_only, _ignore_wheel


def test_desactivar_rueda_customtkinter_sin_alterar_scrollbars(monkeypatch):
    class FakeScrollableFrame:
        def _mouse_wheel_all(self, event):
            self._parent_canvas.yview_scroll(5, "units")

    fake_pkg = types.ModuleType("customtkinter.windows.widgets.ctk_scrollable_frame")
    fake_pkg.CTkScrollableFrame = FakeScrollableFrame
    monkeypatch.setitem(sys.modules, "customtkinter", types.ModuleType("customtkinter"))
    monkeypatch.setitem(sys.modules, "customtkinter.windows", types.ModuleType("customtkinter.windows"))
    monkeypatch.setitem(sys.modules, "customtkinter.windows.widgets", types.ModuleType("customtkinter.windows.widgets"))
    monkeypatch.setitem(sys.modules, "customtkinter.windows.widgets.ctk_scrollable_frame", fake_pkg)

    root = Mock()
    root._axia_manual_scroll_only = False
    install_manual_scroll_only(root)
    events = {(call.args[0], call.args[1]) for call in root.bind_class.call_args_list}
    assert ("Treeview", "<MouseWheel>") in events
    assert ("Text", "<Button-4>") in events
    assert ("TCombobox", "<MouseWheel>") in events
    assert ("Canvas", "<Shift-MouseWheel>") in events
    assert getattr(root, "_axia_manual_scroll_only") is True
    test_canvas = Mock()
    scroll_frame = FakeScrollableFrame()
    scroll_frame._parent_canvas = test_canvas
    assert scroll_frame._mouse_wheel_all(None) is None
    test_canvas.yview_scroll.assert_not_called()
    assert _ignore_wheel(None) == "break"

    initial = root.bind_class.call_count
    install_manual_scroll_only(root)
    assert root.bind_class.call_count == initial


def test_barra_manual_conservada_y_rueda_sidebar_neutralizada():
    sidebar = Path("ui/app_sidebar.py").read_text(encoding="utf-8")
    assert "command=menu_scroll.yview" in sidebar
    assert "menu_scroll.configure(yscrollcommand=barra_scroll.set)" in sidebar
    assert 'canvas.yview_scroll(paso, "units")' not in sidebar


def test_no_auto_foco_formularios_y_scroll_horiz_manual():
    helpers = Path("views/formato_helpers.py").read_text(encoding="utf-8")
    assert "def enfocar_inicio_formulario" in helpers
    body = helpers.split("def enfocar_inicio_formulario", 1)[1].split("def generar_pdf_preview_async", 1)[0]
    assert "focus_set()" not in body

    tabla = Path("ui/table_columns.py").read_text(encoding="utf-8")
    bloque = tabla.split("def _wheel_horizontal", 1)[1].split("\n    def ", 1)[0]
    assert "xview_scroll" not in bloque
    assert 'return "break"' in bloque
