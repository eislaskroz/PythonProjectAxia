from pathlib import Path

SRC = Path(__file__).parents[1] / "views" / "cotizaciones_view.py"
TEXT = SRC.read_text(encoding="utf-8")


def test_jefe_operaciones_solo_tipo_2():
    assert "obtener_nombres_usuarios_por_tipos([2])" in TEXT
    assert 'add_select(general,2,2,"Jefe de Operaciones"' in TEXT


def test_layout_general_cinco_columnas():
    assert "for c in range(5): general.grid_columnconfigure(c, weight=1)" in TEXT
    assert 'add_field(general,0,4,"Contacto"' in TEXT
    assert 'add_field(general,1,4,"ESI / Ejecutiva de Ventas"' in TEXT


def test_unidad_cantidad_concepto_bloqueados():
    assert 'if key in {"unidad_tipo", "cantidad", "concepto", "costo", "precio_venta", "precio_unitario", "importe"}' in TEXT
    assert 'ent.configure(state="disabled")' in TEXT
