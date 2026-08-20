from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "views" / "cotizaciones_view.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "services" / "cotizaciones_service.py").read_text(encoding="utf-8")


def test_campos_derivados_bloqueados_en_ui():
    for campo in ["costo", "precio_venta", "precio_unitario", "importe"]:
        assert campo in VIEW
    assert '{"unidad_tipo", "cantidad", "concepto", "costo", "precio_venta", "precio_unitario", "importe"}' in VIEW


def test_formulas_comerciales_en_ui():
    assert 'costo = round(lista * utilidad / 100.0, 2)' in VIEW
    assert 'venta = round(lista + costo, 2)' in VIEW
    assert 'importe = round(venta * cantidad, 2)' in VIEW


def test_servicio_recalcula_y_no_confia_en_campos_derivados():
    assert 'costo = round(precio_lista * utilidad / 100.0, 2)' in SERVICE
    assert 'precio_venta = round(precio_lista + costo, 2)' in SERVICE
    assert 'precio_unitario = precio_venta' in SERVICE
    assert 'importe = round(precio_unitario * max(cantidad_num, 0.0), 2)' in SERVICE
