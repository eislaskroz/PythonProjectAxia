"""La barra de búsqueda y reimpresión del Kárdex ocupa una sola fila."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "views/almacen_view.py"


def _llamadas(nombre):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    return [node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == nombre]


def _grid(nombre):
    for node in _llamadas(nombre):
        if node.func.attr == "grid":
            return {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords}
    raise AssertionError(f"Falta .grid para {nombre}")


def test_acciones_kardex_en_una_sola_fila():
    for name, column in [("buscar_k_wrap", 0), ("btn_consultar_k", 1),
                         ("btn_reimprimir_etiqueta", 2), ("btn_reimprimir_ticket", 3)]:
        assert _grid(name)["row"] == 0
        assert _grid(name)["column"] == column
        assert _grid(name)["sticky"] == "ew"


def test_tabla_se_extiende_sin_fila_extra():
    assert _grid("tabla_k")["row"] == 1
    assert _grid("kardex_info")["row"] == 2
    assert _grid("navegacion_k")["row"] == 3
    source = SOURCE.read_text(encoding="utf-8")
    assert "fila_comprobantes" not in source


def test_botones_conservan_reimpresion_solo_lectura():
    source = SOURCE.read_text(encoding="utf-8")
    assert "servicio.comprobante_kardex(movimiento_id)" in source
    assert "command=lambda: reimprimir_kardex('ENTRADA')" in source
    assert "command=lambda: reimprimir_kardex('SALIDA')" in source
