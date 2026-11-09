"""El Reportador nativo debe reutilizar el fondo corporativo vertical de Desktop."""
from pathlib import Path
import sys
from io import BytesIO
from PIL import Image
import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.reportador_fotografico_pdf import _OriginalStylePDF, generar_pdf_bytes


def test_fondo_compartido_por_defecto():
    r={'aco':'ACO-PRUEBA'}
    pdf=_OriginalStylePDF(BytesIO(),r)
    assert pdf.background == ROOT / 'assets' / 'FormatoFondo.png'
    assert pdf.background.is_file()
    assert pdf.using_corporate_background


def test_plantilla_externa_tiene_prioridad(tmp_path):
    fondo=tmp_path/'fondo.png'
    Image.new('RGB',(620,800),'white').save(fondo)
    pdf=_OriginalStylePDF(BytesIO(),{'aco':'PRUEBA'},background_path=str(fondo))
    assert pdf.background==fondo
    assert not pdf.using_corporate_background


def test_dibuja_fondo_en_todas_las_paginas():
    import importlib.util
    file = ROOT / 'tests' / 'unit' / 'test_reportador_pdf_original_20261109.py'
    spec = importlib.util.spec_from_file_location('pdf_original_20261109',file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    modelo=module.modelo
    detail,fetch=modelo()
    raw=generar_pdf_bytes(detail,fetch)
    with fitz.open(stream=raw,filetype='pdf') as doc:
        assert doc.page_count >= 3
        # Las páginas de actividades y las hojas adicionales de OS
        # contienen el fondo además de las evidencias.
        assert all(len(page.get_images())>=2 for page in doc)
        for page in doc:
            matches=[info for info in page.get_images(full=True) if info[2] >= 800 and info[3]>=1000]
            assert matches, 'Falta FormatoFondo en una página'
