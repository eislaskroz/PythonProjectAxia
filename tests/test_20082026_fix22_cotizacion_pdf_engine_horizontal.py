from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_cotizacion_reutiliza_motor_corporativo_axia():
    s = text("services/cotizacion_pdf.py")
    assert "BasePdfGenerator.draw_page" in s
    assert "LongTable" in s
    assert "DATOS GENERALES DE COTIZACIÓN".casefold() in s.casefold()
    assert "PARTIDAS DE COTIZACIÓN".casefold() in s.casefold()


def test_motor_selecciona_fondo_horizontal_sin_estirar_el_vertical():
    s = text("core/pdf/base_pdf.py")
    assert "BACKGROUND_LANDSCAPE_PATH" in s
    assert "FormatoFondoHorizontal.png" in s
    assert "width > height" in s
    assert (ROOT / "assets" / "FormatoFondoHorizontal.png").exists()


def test_cotizacion_sigue_siend_letter_horizontal():
    s = text("services/cotizacion_pdf.py")
    assert "pagesize=landscape(letter)" in s
    assert 'title="Cotización"' in s or 'title="Cotizacion"' in s
