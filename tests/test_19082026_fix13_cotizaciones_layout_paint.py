from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "views" / "cotizaciones_view.py").read_text(encoding="utf-8")


def test_franja_superior_es_dos_columnas_busqueda_y_bandeja():
    assert 'superior.grid(row=0, column=0, sticky="ew"' in VIEW
    assert 'superior.grid_columnconfigure(0, weight=1, uniform="top")' in VIEW
    assert 'superior.grid_columnconfigure(1, weight=1, uniform="top")' in VIEW
    assert 'cabecera.grid(row=0, column=0, sticky="nsew"' in VIEW
    assert 'bandeja.grid(row=0, column=1, sticky="nsew"' in VIEW


def test_detalle_ocupa_ancho_completo_debajo():
    assert 'detalle_card.grid(row=1, column=0, sticky="nsew")' in VIEW
    assert 'root.grid_rowconfigure(1, weight=1)' in VIEW


def test_bandeja_superior_es_compacta():
    assert 'height=3' in VIEW
    assert 'text="📥 Cargar seleccionado"' in VIEW
