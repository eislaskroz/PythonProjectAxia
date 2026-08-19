from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "views" / "cotizaciones_view.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "services" / "cotizaciones_service.py").read_text(encoding="utf-8")


def test_cotizaciones_layout_conserva_bandeja_compacta_y_detalle_expandible():
    assert 'bandeja = ctk.CTkFrame' in VIEW
    assert 'detalle_card.grid(row=1, column=0, sticky="nsew")' in VIEW
    assert 'height=3' in VIEW


def test_cotizacion_incluye_servicio_editable_y_total():
    assert 'text="Concepto del servicio"' in VIEW
    assert 'seleccion["servicio_costo"]' in VIEW
    assert 'servicio={"concepto": concepto_servicio, "costo_total": costo_servicio}' in VIEW
    assert '"servicio": {' in SERVICE
    assert '"total_partidas": round(total_partidas, 2)' in SERVICE
    assert 'total_general = round(total_partidas + costo_servicio, 2)' in SERVICE


def test_servicio_se_guarda_en_json_existente_sin_nueva_columna():
    assert '.update({"lev_cotizacion_json": cotizacion})' in SERVICE
