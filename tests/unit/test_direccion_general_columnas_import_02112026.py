"""Regresión: Dirección General resuelve el gestor de columnas antes de usarlo."""
from __future__ import annotations

import ast
from pathlib import Path


def test_direccion_general_importa_gestor_columnas_de_ui():
    root = Path(__file__).resolve().parents[2]
    source = (root / "views/direccion_general_view.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.asname or alias.name: node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert imports.get("TableColumnManager") == "ui.table_columns"
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "TableColumnManager"
        for node in ast.walk(tree)
    )


def test_gestor_columnas_disponible_en_el_modulo_correcto():
    from ui.table_columns import TableColumnManager

    assert callable(TableColumnManager)
