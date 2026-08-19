from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_busqueda_cotizaciones_fuerza_mayusculas():
    src = (ROOT / 'views' / 'cotizaciones_view.py').read_text(encoding='utf-8')
    assert 'def _forzar_mayusculas_busqueda' in src
    assert 'var_busqueda.trace_add("write", _forzar_mayusculas_busqueda)' in src
    assert 'actual.upper()' in src


def test_cotizaciones_recupera_validacion_parcial_sin_mostrar_no_validados():
    src = (ROOT / 'services' / 'cotizaciones_service.py').read_text(encoding='utf-8')
    assert 'def _esta_preautorizado_ventas' in src
    assert 'lev_validado_por' in src
    assert 'lev_fecha_validacion' in src
    assert 'if _esta_preautorizado_ventas(r)' in src


def test_ui_explica_validaciones_anteriores_a_fix10():
    src = (ROOT / 'views' / 'cotizaciones_view.py').read_text(encoding='utf-8')
    assert 'Los LEV validados antes de FIX10 no tenían aún la marca de preautorización' in src
