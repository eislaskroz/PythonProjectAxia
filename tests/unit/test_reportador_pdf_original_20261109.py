"""Pruebas sin red de la réplica de pdf_service.php; no usa entorno Windows."""
import sys
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import fitz
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.reportador_fotografico_pdf import generar_pdf_bytes
from services.reportador_fotografico_service import ErrorReportador


def foto(w, h, col):
    out = BytesIO()
    Image.new('RGB', (w, h), col).save(out, 'JPEG')
    return out.getvalue()


def modelo(os_count=2):
    claves = [str(uuid4()), str(uuid4())]
    acts = [
        {'clave': claves[0], 'titulo':'Instalación y pruebas de CCTV',
         'descripcion':'Revisión de equipos en sitio', 'cantidad_fotos':3},
        {'clave': claves[1], 'titulo':'Verificación de enlace',
         'descripcion':'Evidencia de trabajo terminado', 'cantidad_fotos':2},
    ]
    fotos = [dict(clave_actividad=a['clave'], numero=n)
             for a in acts for n in range(1, a['cantidad_fotos'] + 1)]
    detalle = dict(reporte={'id_reporte':100, 'aco':'ACO-2026-067', 'cliente':'Cliente de prueba',
                          'sucursal':'Sucursal Norte', 'nombre_servicio':'Instalación',
                          'tecnico_responsable':'Ingeniero de pruebas',
                          'fecha_servicio':'2026-11-09', 'observaciones':'Equipo instalado',
                          'cantidad_os': os_count, 'estado':'BORRADOR', 'autor_nombre':'Autor original'},
                   actividades=acts, fotos=fotos,
                   ordenes=[{'numero':n} for n in range(1, os_count + 1)])
    pictures = {(claves[0],1):foto(1500,900,'red'),
                (claves[0],2):foto(650,1000,'blue'),
                (claves[0],3):foto(650,1000,'green'),
                (claves[1],1):foto(1600,900,'yellow'),
                (claves[1],2):foto(800,1100,'purple')}
    orders = {num:foto(900,1500,'gray') for num in range(1, os_count+1)}
    def fetch(id, num, key=None, *, os=False):
        assert id==100
        return orders[num] if os else pictures[(key,num)]
    return detalle, fetch


def test_formato_y_autor_original():
    detalle, fetch = modelo()
    raw = generar_pdf_bytes(detalle, fetch)
    assert raw[:4] == b'%PDF'
    with fitz.open(stream=raw, filetype='pdf') as doc:
        assert doc.page_count >= 3
        assert all(page.rect.width==612 and page.rect.height==792 for page in doc)
        text = '\n'.join(page.get_text() for page in doc)
        for item in ('REPORTE FOTOGRÁFICO','ACO-2026-067','ACTIVIDAD 1',
                     'ACTIVIDAD 2','Autor original','ORDEN DE SERVICIO 1', 'ORDEN DE SERVICIO 2'):
            assert item in text, item
        assert 'Pendiente' not in text
        assert sum(len(page.get_images()) for page in doc) >= 7
        assert all(len(doc[-i].get_images())>=1 for i in (1,2))
        # Imagen de orden de servicio por página, siempre después de actividades.
        assert 'ORDEN DE SERVICIO 1' in doc[-2].get_text()
        assert 'ORDEN DE SERVICIO 2' in doc[-1].get_text()


def test_fotos_faltantes_bloquean_pdf():
    detalle, fetch = modelo()
    detalle['fotos'].pop()
    with pytest.raises(ErrorReportador, match='faltan fotografías'):
        generar_pdf_bytes(detalle, fetch)


def test_os_faltante_bloquea_pdf():
    detalle, fetch = modelo()
    detalle['ordenes'] = [{'numero':1}]
    with pytest.raises(ErrorReportador, match='Faltan Órdenes'):
        generar_pdf_bytes(detalle, fetch)


def test_sin_autor_bloquea_pdf():
    detalle, fetch = modelo()
    detalle['reporte']['autor_nombre'] = ''
    with pytest.raises(ErrorReportador, match='autor original'):
        generar_pdf_bytes(detalle, fetch)


def test_reporte_en_borrador_completo_si_permita_pdf():
    detalle, fetch = modelo(os_count=1)
    assert generar_pdf_bytes(detalle, fetch)[:4] == b'%PDF'
