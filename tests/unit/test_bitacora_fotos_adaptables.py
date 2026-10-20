"""Regresiones del PDF de bitácoras con evidencias adaptables."""
import io
from PIL import Image as PILImage
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate

from services.pdf_fotos_inteligentes import FotoPdf, agrupar_fotos, dimensiones_ajustadas, construir_filas_fotos


def _foto(w, h, name):
    b = io.BytesIO()
    PILImage.new('RGB', (w, h), '#dbeafe').save(b, 'PNG')
    return FotoPdf(b.getvalue(), name, w, h)


def test_dos_verticales_consecutivas_en_una_fila():
    fotos = [_foto(500, 900, '1'), _foto(300, 600, '2'), _foto(1200, 700, '3')]
    assert [[i.nombre for i in grupo] for grupo in agrupar_fotos(fotos)] == [['1', '2'], ['3']]


def test_se_respeta_orden_mezclado_y_vertical_suelta():
    fotos = [_foto(500, 900, 'A'), _foto(1200, 700, 'B'), _foto(400, 700, 'C')]
    assert [[i.nombre for i in grupo] for grupo in agrupar_fotos(fotos)] == [['A'], ['B'], ['C']]


def test_cuadradas_no_se_agrupan_y_dimensiones_sin_deformar():
    foto = _foto(900, 900, 'Cuadrada')
    assert not foto.es_vertical
    for w,h in [(4000,3000), (300,900), (900,900)]:
        imagen = _foto(w,h,'prueba')
        ancho, alto = dimensiones_ajustadas(imagen, 6.5*inch, 4.25*inch)
        assert abs(ancho / alto - w / h) < 1e-9
        assert ancho <= 6.5*inch and alto <= 4.25*inch


def test_filas_paginan_sin_recortar_dibujos(tmp_path):
    fotos = [_foto(1200,700, 'horizontal.png'), _foto(350,900, 'v1.png'),
             _foto(350,900, 'v2.png'), _foto(1200,700, 'otra.jpg')]
    filas = construir_filas_fotos(fotos, estilo_texto=ParagraphStyle('bitNormal'))
    assert len(filas) == 3
    salida = tmp_path / 'paginable.pdf'
    doc = SimpleDocTemplate(str(salida), pagesize=(612,792),
                            topMargin=96,bottomMargin=78,leftMargin=34,rightMargin=34)
    doc.build(filas)
    assert salida.read_bytes().startswith(b'%PDF')
