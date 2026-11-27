import hashlib
import io
import sys
import types
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock

import pytest
from PIL import Image
from pypdf import PdfReader
from reportlab.pdfgen.canvas import Canvas
from services import desktop_historical_evidence as historico
from services import obra_civil_pdf_anexos as anexos
from services.desktop_evidence_access import EvidenciaNoDisponible


BASE = 'https://example.supabase.co'
FOLIO = 'OBC-0018'


def pdf(*paginas):
    stream = io.BytesIO()
    canvas = Canvas(stream)
    for texto, dimensiones in paginas:
        canvas.setPageSize(dimensiones)
        canvas.drawString(30, 40, texto)
        canvas.showPage()
    canvas.save()
    return stream.getvalue()


def registro(raw, ext='pdf'):
    return dict(bucket=historico.BUCKET, storage_path=f'obras-civiles-archivos/EDICION-{uuid4()}/{uuid4()}_archivo.{ext}', url='', nombre='Anexo.'+ext, mime='application/pdf' if ext=='pdf' else 'image/vnd.dwg', size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setenv('AXIA_HISTORICAL_EVIDENCE_SECURE', '1')
    monkeypatch.setitem(sys.modules,'supabase_config',types.SimpleNamespace(SUPABASE_URL=BASE, SUPABASE_KEY='test'))


def test_merge_todas_paginas_y_progreso(entorno, monkeypatch, tmp_path):
    uno=pdf(('ANEXO UNO P1',(300,500)),('ANEXO UNO P2',(500,300)))
    dos=pdf(('ANEXO DOS',(612,792)))
    a,b=registro(uno),registro(dos)
    fuente={a['storage_path']:uno,b['storage_path']:dos}
    fetch=Mock(side_effect=lambda ruta,folio: fuente[ruta])
    monkeypatch.setattr(historico,'descargar_archivo_historico',fetch)
    eventos=Mock(); monkeypatch.setattr(anexos,'progreso_pdf',eventos)
    out=tmp_path/'obra.pdf'
    assert anexos.generar_con_anexos_obra_civil(out,[a,b],FOLIO,lambda p:p.write_bytes(pdf(('OBRA AXIA',(612,792)))))==str(out)
    paginas=PdfReader(out).pages
    assert len(paginas)==4
    assert [p.extract_text().strip() for p in paginas]==['OBRA AXIA','ANEXO UNO P1','ANEXO UNO P2','ANEXO DOS']
    assert [(float(p.mediabox.width),float(p.mediabox.height)) for p in paginas[1:]]==[(300,500),(500,300),(612,792)]
    assert fetch.call_count==2
    assert [c.args[1:] for c in eventos.call_args_list if c.args[0].startswith('Incorporando páginas')]==[(0,3),(1,3),(2,3),(3,3)]
    assert not list(tmp_path.glob('.axia_obc_*'))


@pytest.mark.parametrize('causa',['denegado','corrupto','hash','tamano','cifrado'])
def test_error_no_sobrescribe(entorno,monkeypatch,tmp_path,causa):
    raw=pdf(('ANEXO',(300,500)))
    if causa=='corrupto': raw=b'%PDF-1.7\narchivo corrupto'
    if causa=='cifrado':
        from pypdf import PdfWriter
        w=PdfWriter(); w.add_blank_page(200,300); w.encrypt('clave'); buf=io.BytesIO(); w.write(buf); raw=buf.getvalue()
    meta=registro(raw)
    if causa=='hash': meta['sha256']='0'*64
    if causa=='tamano': meta['size_bytes']+=1
    fetch=Mock(side_effect=EvidenciaNoDisponible('denegado')) if causa=='denegado' else Mock(return_value=raw)
    monkeypatch.setattr(historico,'descargar_archivo_historico',fetch)
    out=tmp_path/'obra.pdf'; out.write_bytes(b'original')
    render=Mock()
    with pytest.raises(EvidenciaNoDisponible): anexos.generar_con_anexos_obra_civil(out,[meta],FOLIO,render)
    assert out.read_bytes()==b'original' and not list(tmp_path.glob('.axia_obc_*'))
    render.assert_not_called()


def test_anexo_local_preview_y_cad(entorno,tmp_path):
    p=tmp_path/'plano.pdf'; p.write_bytes(pdf(('ANEXO LOCAL',(300,500))))
    cad=tmp_path/'plano.dwg'; cad.write_bytes(b'AC1027 plano')
    out=tmp_path/'preview.pdf'
    anexos.generar_con_anexos_obra_civil(out,[p,cad],'',lambda f:f.write_bytes(pdf(('BASE',(612,792)))))
    assert len(PdfReader(out).pages)==2


def test_fallo_render_conserva_pdf(entorno,tmp_path):
    out=tmp_path/'preview.pdf'; out.write_bytes(b'original')
    with pytest.raises(EvidenciaNoDisponible): anexos.generar_con_anexos_obra_civil(out,[],FOLIO,lambda f:False)
    assert out.read_bytes()==b'original'


def test_no_url_externa(entorno,tmp_path,monkeypatch):
    fetch=Mock(); monkeypatch.setattr(historico,'descargar_archivo_historico',fetch)
    with pytest.raises(EvidenciaNoDisponible): anexos.generar_con_anexos_obra_civil(tmp_path/'out.pdf',['https://externo.example/anexo.pdf'],FOLIO,Mock())
    fetch.assert_not_called()


def test_motor_real_consulta_y_preview(entorno,monkeypatch,tmp_path):
    monkeypatch.setitem(sys.modules,'customtkinter',types.ModuleType('customtkinter'))
    monkeypatch.setitem(sys.modules,'services.movimientos_service',types.SimpleNamespace(registrar_movimiento_seguro=lambda **kw:None))
    from views import formato_helpers
    from services.obras_civiles_universal import generar_pdf_obra_civil_desde_registro
    raw=pdf(('ANEXO REAL 1',(300,500)),('ANEXO REAL 2',(500,300)))
    meta=registro(raw)
    fetch=Mock(return_value=raw); monkeypatch.setattr(historico,'descargar_archivo_historico',fetch)
    fotografia=io.BytesIO(); Image.new('RGB',(117,83),'blue').save(fotografia,'PNG')
    photo=dict(bucket=historico.BUCKET,storage_path=f'obras-civiles/SOLICITUD-{uuid4()}/{uuid4()}_archivo.png',nombre='foto.png',url='')
    monkeypatch.setattr(historico,'descargar_foto_historica',Mock(return_value=fotografia.getvalue()))
    obra=dict(obc_folio=FOLIO,obc_cliente='Prueba ficticia',obc_nombre_proyecto='Prueba de anexos',obc_evidencias_json=[photo],obc_archivos_adjuntos_json=[meta])
    out=tmp_path/'consulta.pdf'
    assert generar_pdf_obra_civil_desde_registro(obra,ruta_salida=out,abrir=False)==str(out)
    paginas=PdfReader(out).pages
    assert 'ANEXO REAL 1' in paginas[-2].extract_text() and 'ANEXO REAL 2' in paginas[-1].extract_text()
    assert 'Obra Civil' in paginas[0].extract_text()
    local=tmp_path/'local.pdf'; local.write_bytes(raw)
    pre=tmp_path/'preview.pdf'
    assert formato_helpers.generar_pdf_preview('Obra Civil',{'Folio OBC':FOLIO,'Cliente':'Prueba','__archivos_adjuntos_obc':[str(local)]},ruta_salida=pre,abrir=False)==str(pre)
    assert 'ANEXO REAL 2' in PdfReader(pre).pages[-1].extract_text()
    assert fetch.call_count==1
    monkeypatch.setattr(formato_helpers,'ruta_documentos_axia',lambda subcarpeta:tmp_path)
    guardado=formato_helpers.generar_pdf_archivo('Obra Civil',{'Folio OBC':FOLIO,'Cliente':'Prueba','__archivos_adjuntos_obc':[str(local)]},nombre_archivo='guardado',subcarpeta='obras_civiles')
    assert 'ANEXO REAL 2' in PdfReader(guardado).pages[-1].extract_text()


def test_aplana_anotaciones_visibles(entorno,tmp_path):
    import fitz
    local=tmp_path/'anotado.pdf'
    with fitz.open() as doc:
        pagina=doc.new_page(width=300,height=500)
        pagina.insert_text((40,40),'ANEXO CON ANOTACION')
        anotacion=pagina.add_freetext_annot(fitz.Rect(40,100,250,150),'TEXTO VISIBLE')
        anotacion.update()
        doc.save(local)
    destino=tmp_path/'resultado.pdf'
    anexos.generar_con_anexos_obra_civil(destino,[local],FOLIO,lambda f:f.write_bytes(pdf(('BASE',(612,792)))))
    pagina=PdfReader(destino).pages[-1]
    assert not pagina.get('/Annots')
    with fitz.open(destino) as doc:
        assert 'TEXTO VISIBLE' in doc[-1].get_text()
