import io
from PIL import Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from services.pdf_fotos_inteligentes import FotoPdf, construir_filas_fotos, agrupar_fotos


def _foto(ancho, alto, nombre):
    buffer = io.BytesIO()
    Image.new('RGB', (ancho, alto), '#c3d8e4').save(buffer, 'PNG')
    return FotoPdf(buffer.getvalue(), nombre, ancho, alto)


def test_bitacoras_alinean_filas_automaticas_al_mismo_margen(tmp_path):
    import fitz
    ancho_total = 6.55 * inch
    fotos = [
        _foto(1581, 688, 'captura-1'),
        _foto(739, 1600, 'movil-1'),
        _foto(454, 594, 'movil-2'),
        _foto(1503, 277, 'panoramica'),
        _foto(281, 779, 'vertical'),
        _foto(1484, 278, 'ancha'),
        _foto(942, 901, 'cuadrada'),
        _foto(1587, 862, 'otra'),
    ]
    filas = construir_filas_fotos(
        fotos,
        estilo_texto=ParagraphStyle('photo-test'),
        ancho_total=ancho_total,
        alineacion='LEFT',
    )
    assert sum(len(grupo) for grupo in agrupar_fotos(fotos, ancho_total)) == len(fotos)
    assert all(fila.hAlign == 'LEFT' for fila in filas)
    for fila in filas:
        assert sum(fila._colWidths) <= ancho_total + 0.01
    salida = tmp_path / 'bitacora_fotos_alineadas.pdf'
    encabezado = Table([[Paragraph('EVIDENCIA FOTOGRÁFICA', ParagraphStyle('hdr'))]], colWidths=[ancho_total], hAlign='LEFT')
    encabezado.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#1F4E79'))]))
    doc = SimpleDocTemplate(str(salida), pagesize=(612,792), leftMargin=34, rightMargin=34, topMargin=96, bottomMargin=78)
    doc.build([encabezado, Spacer(1, 5), *filas])
    lector = fitz.open(salida)
    rects = []
    for pagina in lector:
        rects.extend([b['bbox'] for b in pagina.get_text('dict')['blocks'] if b['type'] == 1])
    assert len(rects) == len(fotos)
    assert all(39 <= box[0] < 39 + ancho_total for box in rects)
    assert all(box[2] <= 40 + ancho_total + 0.1 for box in rects)
    assert min(box[0] for box in rects) < 40.1


def test_otros_modulos_conservan_alineacion_predeterminada():
    fotos = [_foto(1503, 277, 'a'), _foto(1000, 500, 'b')]
    filas = construir_filas_fotos(fotos, estilo_texto=ParagraphStyle('normal'))
    assert all(fila.hAlign == 'CENTER' for fila in filas)
