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
    assert [item.nombre for group in agrupar_fotos(fotos) for item in group] == ['1', '2', '3']
    assert len(agrupar_fotos(fotos)) <= 2


def test_se_respeta_orden_mezclado_y_vertical_suelta():
    fotos = [_foto(500, 900, 'A'), _foto(1200, 700, 'B'), _foto(400, 700, 'C')]
    assert [item.nombre for group in agrupar_fotos(fotos) for item in group] == ['A', 'B', 'C']
    assert any(len(g) > 1 for g in agrupar_fotos(fotos))


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
    assert 1 <= len(filas) <= 3
    salida = tmp_path / 'paginable.pdf'
    doc = SimpleDocTemplate(str(salida), pagesize=(612,792),
                            topMargin=96,bottomMargin=78,leftMargin=34,rightMargin=34)
    doc.build(filas)
    assert salida.read_bytes().startswith(b'%PDF')


def test_tres_verticales_sin_marco_ni_pies(tmp_path):
    fotos = [_foto(400, 850, f"Captura-{i}.png") for i in range(3)]
    assert [len(g) for g in agrupar_fotos(fotos)] == [3]
    filas = construir_filas_fotos(fotos, estilo_texto=ParagraphStyle('normal'))
    assert len(filas) == 1
    salida = tmp_path / 'tres.pdf'
    doc = SimpleDocTemplate(str(salida), pagesize=(612, 792), topMargin=96,
                            bottomMargin=78, leftMargin=34, rightMargin=34)
    doc.build(filas)
    assert salida.read_bytes().startswith(b'%PDF')
    import fitz
    pdf = fitz.open(salida)
    assert len(pdf) == 1
    assert len([b for b in pdf[0].get_text("dict")["blocks"] if b["type"] == 1]) == 3
    assert not pdf[0].get_text().strip()


def test_mezclas_sin_perder_orden_ni_fotos(tmp_path):
    import fitz
    medidas = [(1200, 700), (450, 900), (390, 900), (1100, 700),
               (900, 900), (450, 950), (430, 950), (450, 950)]
    fotos = [_foto(w, h, str(i)) for i, (w, h) in enumerate(medidas)]
    grupos = agrupar_fotos(fotos)
    assert [f.nombre for grupo in grupos for f in grupo] == [str(i) for i in range(len(fotos))]
    assert all(1 <= len(grupo) <= 3 for grupo in grupos)
    filas = construir_filas_fotos(fotos, estilo_texto=ParagraphStyle('normal'))
    ruta = tmp_path / 'mixto.pdf'
    doc = SimpleDocTemplate(str(ruta), pagesize=(612, 792), topMargin=96,
                            bottomMargin=78, leftMargin=34, rightMargin=34)
    doc.build(filas)
    pdf = fitz.open(ruta)
    assert sum(len([b for b in p.get_text('dict')['blocks'] if b['type'] == 1]) for p in pdf) == len(fotos)


def test_carga_grande_orden_y_complejidad():
    foto = _foto(400, 850, 'repetida')
    grupos = agrupar_fotos([foto] * 120)
    assert sum(map(len, grupos)) == 120
    assert len(grupos) <= 60
