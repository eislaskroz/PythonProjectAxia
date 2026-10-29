"""Evitar que reaparezca el panel gris sin utilidad del Catálogo AXIA."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_catalogo_sin_panel_inferior_y_con_tabla_expandible():
    vista = (ROOT / "views" / "almacen_view.py").read_text(encoding="utf-8")
    assert "Selecciona una fila de la tabla." not in vista
    assert "detalle_maestro" not in vista
    assert "seleccionado_txt" not in vista
    assert "t_catalogo.grid_rowconfigure(3, weight=1)" in vista
    assert "tabla.grid(row=3, column=0, sticky='nsew'" in vista
    assert "tabla._on_select = seleccionar" in vista
    assert "for formulario, _ in entradas.values():" in vista


def test_version_compilador_e_instalador_coinciden():
    from core.version import APP_VERSION
    instalador = (ROOT / "installer" / "AXIA.iss").read_text(encoding="utf-8")
    assert APP_VERSION == "2.04.11"
    assert f'#define MyAppVersion "{APP_VERSION}"' in instalador
