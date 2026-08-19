from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "views" / "cotizaciones_view.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "services" / "cotizaciones_service.py").read_text(encoding="utf-8")


def test_se_omite_encabezado_visual_de_costo_servicio():
    assert 'scroll, text="Costo del servicio"' not in VIEW
    assert 'Ventas puede ajustar el concepto del servicio y capturar su costo total.' not in VIEW
    assert 'text="Concepto del servicio"' in VIEW


def test_tabla_incluye_precio_unitario_antes_del_total():
    assert '"Precio por pieza/unidad/metro", "Costo total MXN"' in VIEW
    assert '"precio_var": var_precio' in VIEW
    assert 'precio * cantidad' in VIEW


def test_cotizacion_persiste_precio_unitario_en_jsonb():
    assert '"precio_unitario": precio_unitario_num' in SERVICE
    assert '"version": 3' in SERVICE
    assert '.update({"lev_cotizacion_json": cotizacion})' in SERVICE
