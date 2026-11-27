import io
import sys
from types import SimpleNamespace
from unittest.mock import Mock
from collections.abc import Mapping
from pathlib import Path
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from services import desktop_historical_evidence as svc
from services import levantamiento_seguridad_pdf as renderer
from services.desktop_evidence_access import EvidenciaNoDisponible

BASE = 'https://example.supabase.co'
LEV = 'LEV-00122'
OBC = 'OBC-0001'
PHOTO = 'levantamientos/' + LEV + '/0123456789abcdef0123456789abcdef_foto.png'
PDF = 'levantamientos-archivos/' + LEV + '/0123456789abcdef0123456789abcdef_plano.pdf'
OBCPHOTO = 'obras-civiles/' + OBC + '/0123456789abcdef0123456789abcdef_foto.png'


def item(path, mime):
    return {'storage_path': path, 'url': BASE + '/storage/v1/object/public/bitacoras-evidencias/' + path, 'mime': mime}


def image_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (123, 87), 'blue').save(buf, 'PNG')
    return buf.getvalue()


def pdf_bytes():
    buf = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def secure(monkeypatch):
    monkeypatch.setenv('AXIA_HISTORICAL_EVIDENCE_SECURE', '1')
    monkeypatch.setitem(sys.modules, 'supabase_config', SimpleNamespace(SUPABASE_URL=BASE, SUPABASE_KEY='test'))


@pytest.mark.parametrize('path,folio', [(PHOTO, LEV), (PDF, LEV), (OBCPHOTO, OBC)])
def test_new_paths(path, folio):
    assert svc.ruta_historica(item(path, ''), folio, BASE) == path


def test_wrong_document():
    with pytest.raises(EvidenciaNoDisponible):
        svc.ruta_historica(item(OBCPHOTO, ''), 'OBC-0002', BASE)


def test_lev_pdf_historical_photo_and_attachment(secure, monkeypatch, tmp_path):
    fetch = Mock(side_effect={PHOTO: image_bytes(), PDF: pdf_bytes()}.__getitem__)
    monkeypatch.setattr(renderer, 'descargar_archivo_historico', lambda path, folio: fetch(path))
    registro = dict(lev_folio=LEV, lev_tipo_levantamiento='General', lev_cliente='Prueba', lev_evidencias_json=[item(PHOTO, 'image/png')], lev_archivos_adjuntos_json=[item(PDF, 'application/pdf')])
    out = tmp_path / 'result.pdf'
    assert renderer.generar_pdf_levantamiento_maestro(registro, ruta_salida=out) == str(out)
    pages = PdfReader(out).pages
    assert float(pages[-1].mediabox.width) == 200
    sizes = set()
    for page in pages:
        res = page.get('/Resources')
        if res:
            obj = res.get_object().get('/XObject')
            if obj:
                sizes.update((v.get_object().get('/Width'), v.get_object().get('/Height')) for v in obj.get_object().values())
    assert (123, 87) in sizes
    assert fetch.call_count == 2


def test_lev_denied_preserves_existing_pdf(secure, monkeypatch, tmp_path):
    monkeypatch.setattr(renderer, 'descargar_archivo_historico', Mock(side_effect=EvidenciaNoDisponible('denied')))
    registro = dict(lev_folio=LEV, lev_evidencias_json=[item(PHOTO,'image/png')])
    dest = tmp_path / 'result.pdf'
    dest.write_bytes(b'existing')
    with pytest.raises(EvidenciaNoDisponible):
        renderer.generar_pdf_levantamiento_maestro(registro, ruta_salida=dest)
    assert dest.read_bytes() == b'existing'


def test_obc_preparation(secure, monkeypatch):
    raw = image_bytes()
    fetch = Mock(return_value=raw)
    monkeypatch.setattr(svc, 'descargar_foto_historica', fetch)
    prepared = svc.preparar_evidencias_obra_civil([item(OBCPHOTO,'image/png')], OBC)
    assert prepared[0].contenido == raw
    fetch.assert_called_once_with(OBCPHOTO,OBC)
    assert svc.preparar_evidencias_obra_civil(prepared,OBC) == prepared


def test_obc_denied(secure, monkeypatch):
    monkeypatch.setattr(svc, 'descargar_foto_historica', Mock(side_effect=EvidenciaNoDisponible('denied')))
    with pytest.raises(EvidenciaNoDisponible):
        svc.preparar_evidencias_obra_civil([item(OBCPHOTO,'image/png')], OBC)
