"""Regresión Tk: grid_columnconfigure exige pesos enteros para cada columna."""
from pathlib import Path
import ast
import pytest

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = (60, 40, 60, 33, 32, 18, 25, 20, 0)


@pytest.mark.parametrize('archivo', ['levantamiento_view.py', 'obra_civil_view.py'])
def test_distribucion_canalizacion_no_envia_pesos_decimales_a_tk(archivo):
    codigo = (ROOT / 'views' / archivo).read_text(encoding='utf-8')
    arbol = ast.parse(codigo)
    pesos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.For) or not isinstance(nodo.iter, ast.Call):
            continue
        if not isinstance(nodo.iter.func, ast.Name) or nodo.iter.func.id != 'enumerate':
            continue
        if not nodo.iter.args or not isinstance(nodo.iter.args[0], ast.Tuple):
            continue
        try:
            valores = ast.literal_eval(nodo.iter.args[0])
        except (ValueError, TypeError):
            continue
        if len(valores) == 9 and any(isinstance(v, (float, int)) for v in valores):
            pesos.append(valores)
    assert pesos == [EXPECTED]
    assert all(isinstance(p, int) and p >= 0 for p in pesos[0])


def test_tk_real_acepta_pesos_enteros():
    """Prueba real con Tk ejecutada con Xvfb en Linux/Windows con GUI."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        panel = tk.Frame(root)
        for col, weight in enumerate(EXPECTED):
            panel.grid_columnconfigure(col, weight=weight)
        assert [int(panel.grid_columnconfigure(col)['weight']) for col in range(9)] == list(EXPECTED)
    finally:
        root.destroy()
