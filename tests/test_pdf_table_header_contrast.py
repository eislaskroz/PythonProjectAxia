from pathlib import Path
from reportlab.lib import colors


def test_pdf_table_header_style_is_white():
    from core.pdf.base_pdf import BasePdfGenerator

    style = BasePdfGenerator.styles()["table_header"]
    assert style.textColor == colors.white
    assert style.fontName == "Helvetica-Bold"


def test_formato_helpers_uses_dedicated_table_header_style():
    source = (Path(__file__).resolve().parents[1] / "views" / "formato_helpers.py").read_text(encoding="utf-8")
    assert 'estilo_encabezado_tabla = estilos_axia["table_header"]' in source
    assert 'Paragraph(str(c), estilo_encabezado_tabla)' in source
