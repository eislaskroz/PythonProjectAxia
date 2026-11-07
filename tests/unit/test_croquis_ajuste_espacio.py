"""Regresión aislada de ajuste responsive del editor de croquis.

Se extrae la función pura por AST: los test corren en CI Linux sin CTk/Windows.
"""
import ast
from pathlib import Path


def _layout_function():
    path = Path(__file__).resolve().parents[2] / 'views' / 'croquis_editor_view.py'
    module = ast.parse(path.read_text(encoding='utf8'))
    function = next(n for n in module.body
                    if isinstance(n, ast.FunctionDef) and n.name == 'calcular_zoom_para_lienzo')
    namespace = {'WIDTH': 980, 'HEIGHT': 460}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['calcular_zoom_para_lienzo']


def test_ventana_amplia_aprovecha_lienzo_sobre_100_por_ciento():
    fit = _layout_function()
    zoom = fit(1290, 655)
    assert 1.25 < zoom < 1.35  # Ya no está limitado a 1.0.
    assert 980 * zoom <= 1290 - 12
    assert 460 * zoom <= 655 - 12
    assert 980 * zoom >= (1290 - 12) * .99


def test_ventana_estrecha_no_recorta_ni_estira_el_documento():
    fit = _layout_function()
    for w, h in [(800, 580), (1100, 480), (1440, 710), (2200, 1200)]:
        zoom = fit(w, h)
        assert 980 * zoom <= w - 12
        assert 460 * zoom <= h - 12


def test_la_funcion_admite_4k_y_tamano_inicial_sin_geometria():
    fit = _layout_function()
    assert 3.0 < fit(3400, 2000) <= 4.0
    assert fit(1, 1) == .8


def test_reajuste_mantiene_zoom_manual_y_guardar_visible():
    text = (Path(__file__).resolve().parents[2] / 'views' / 'croquis_editor_view.py').read_text(encoding='utf8')
    assert '"fit_to_window": True' in text
    assert 'if not por_ajuste:' in text
    assert 'drawing.bind("<Configure>", ajustar_despues_de_redimensionar)' in text
    assert 'win.after(180, fit_zoom)' in text
    assert text.index('bottom.pack(side="bottom"') < text.index('body.pack(fill="both"')
    assert 'text="Guardar croquis"' in text
    assert 'variable_base64.set(doc.export_base64())' in text
