"""Regresión: Color/Modelo/Otros en LEV y OBC, controles y PDF de canalización."""
from pathlib import Path
from services.pdf_canalizacion_agrupada import agrupar_partidas_canalizacion, ENCABEZADOS_CANALIZACION

ROOT = Path(__file__).resolve().parents[2]


def test_pdf_rescata_color_modelo_y_no_imprime_aproximado():
    filas = [
        {"familia": "Conductores y Canalización", "material": "Tubo", "tipo": "EMT",
         "tamano_calibre_especificacion": '1/2" (13 mm)', "color_modelo": "Gris / ZX45",
         "cantidad": "2", "unidad": "Pieza(s)", "aproximado": "6 metros"},
        {"familia": "Conductores y Canalización", "material": "Cable", "tipo": "UTP Cat6",
         "cantidad": "4", "unidad": "Metro(s)"},
    ]
    grupos = agrupar_partidas_canalizacion(filas)
    assert len(grupos) == 1
    assert ENCABEZADOS_CANALIZACION == (
        "Material", "Tipo", "Tamaño / calibre", "Color/Modelo/Otros", "Cantidad", "Unidad")
    assert grupos[0][1][0]["Color/Modelo/Otros"] == "Gris / ZX45"
    assert grupos[0][1][1]["Color/Modelo/Otros"] == ""
    assert all("Aproximado" not in row for _, rows in grupos for row in rows)


def test_lev_tiene_nueva_columna_guardado_y_restauracion():
    view = (ROOT / "views/levantamiento_view.py").read_text(encoding="utf-8")
    assert '"Tamaño/calibre", "Color/Modelo/Otros", "Cantidad"' in view
    assert '"color_modelo": item["color_modelo"].get().strip()' in view
    assert '("color_modelo","color_modelo")' in view
    assert 'text="✕", width=34' in view
    assert 'column=8, padx=3' in view


def test_obra_civil_tiene_nueva_columna_guardado_y_restauracion():
    view = (ROOT / "views/obra_civil_view.py").read_text(encoding="utf-8")
    assert '"Color/Modelo/Otros", "Cantidad"' in view
    assert '"color_modelo": item["color_modelo"].get().strip()' in view
    assert 'item["color_modelo"].set(str(fila.get("color_modelo")' in view
    assert '"color_modelo": fila["color_modelo"].get()' in view
    assert '"Color/Modelo/Otros": m.get("color_modelo", "")' in view
    assert 'text="✕", width=34' in view


def test_pdf_y_conversion_ot_conservan_modelo():
    pdf = (ROOT / "services/levantamiento_seguridad_pdf.py").read_text(encoding="utf-8")
    conversion = (ROOT / "services/ordenes_trabajo_schema.py").read_text(encoding="utf-8")
    assert pdf.count('[1.20*inch, 1.60*inch, 1.38*inch, 1.10*inch, .64*inch, .98*inch]') == 2
    assert 'modelo=item.get("color_modelo")' in conversion
