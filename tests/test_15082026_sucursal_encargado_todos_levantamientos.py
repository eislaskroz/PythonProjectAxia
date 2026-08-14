from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_levantamiento_integra_catalogos_sucursal_contacto():
    text = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
    assert 'obtener_sucursales_por_cliente' in text
    assert 'obtener_contactos_por_sucursal' in text
    assert '"Sucursal", var_sucursal' in text
    assert '"Encargado de sucursal", var_encargado_sucursal' in text
    assert '"id_sucursal": seleccion_catalogo.get("id_sucursal")' in text
    assert '"id_contacto": seleccion_catalogo.get("id_contacto")' in text
    assert '"id_cliente": seleccion_catalogo.get("id_cliente")' in text


def test_obra_civil_integra_catalogos_sucursal_contacto():
    text = (ROOT / 'views' / 'obra_civil_view.py').read_text(encoding='utf-8')
    assert 'obtener_sucursales_por_cliente' in text
    assert 'obtener_contactos_por_sucursal' in text
    assert 'catalogo_selector("Sucursal", var_sucursal' in text
    assert 'catalogo_selector("Encargado de sucursal", var_encargado_sucursal' in text
    assert 'seleccion_catalogo.get("id_sucursal")' in text
    assert 'seleccion_catalogo.get("id_contacto")' in text
