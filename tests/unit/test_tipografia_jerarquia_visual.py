"""Guardas de regresión para la jerarquía tipográfica de AXIA DESKTOP.

Estas pruebas no crean ventanas ni requieren un servidor.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _module_ast(filename):
    return ast.parse((ROOT / filename).read_text(encoding="utf-8-sig"))


def _constant_tuple(filename, name):
    module = _module_ast(filename)
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            if isinstance(node.value, ast.Tuple):
                return node.value.elts
    raise AssertionError(f"No se encontró el estilo {name}")


def test_botones_globales_sin_negrita():
    assert not any(isinstance(v, ast.Constant) and v.value == "bold" for v in _constant_tuple("ui/fonts.py", "BUTTON_FONT"))


def test_titulos_principales_y_secciones_conservan_jerarquia():
    for name in ("TITLE_XL", "TITLE_LG", "TITLE_MD", "TITLE_SM", "SECTION_FONT"):
        assert any(isinstance(v, ast.Constant) and v.value == "bold" for v in _constant_tuple("ui/fonts.py", name))


def test_menu_lateral_sin_negritas_en_opciones():
    content = (ROOT / "ui/app_sidebar.py").read_text(encoding="utf-8-sig")
    assert 'font=("Segoe UI", 11, "normal")' in content
    assert '"bold" if tipo == "cabecera" or activo' not in content


def test_tablas_sin_negritas_pero_colores_y_zebra_conservados():
    native = (ROOT / "ui/native_table.py").read_text(encoding="utf-8-sig")
    theme = (ROOT / "ui/theme_manager.py").read_text(encoding="utf-8-sig")
    assert 'font=("Segoe UI", 10)' in native
    assert '"fila_azul"' in native and '#EAF3FF' in native
    assert 'font=(cls.FONT_FAMILY, cls.BASE_FONT_SIZE),' in theme
    assert '"Treeview.Heading"' in theme


def test_etiquetas_de_formulario_ligeras_secciones_en_negrita():
    labels = _constant_tuple("views/formato_helpers.py", "LABEL_FONT")
    sections = _constant_tuple("views/formato_helpers.py", "SECTION_FONT")
    assert not any(isinstance(v, ast.Constant) and v.value == "bold" for v in labels)
    assert any(isinstance(v, ast.Constant) and v.value == "bold" for v in sections)
