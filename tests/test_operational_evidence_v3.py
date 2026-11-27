import hashlib
import io
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from services import desktop_operational_evidence as svc
from services import sesion_axia_compartida as session
from app_context import obtener_usuario_actual

FOLIO = 'OS-00005'
BASE = 'https://example.supabase.co'

@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setitem(sys.modules, 'supabase_config', SimpleNamespace(SUPABASE_URL=BASE, SUPABASE_KEY='public-test'))
    monkeypatch.setitem(obtener_usuario_actual(), 'id_usuario', 2)
    session.establecer_sesion('test-session', 2, int(time.time())+1000)
    monkeypatch.setenv('AXIA_DESKTOP_EVIDENCE_GRANT','a'*64)
    buf = io.BytesIO(); Image.new('RGB',(12,16),'blue').save(buf,'JPEG'); raw = buf.getvalue()
    photos=[]
    for photo in ['83d6159a-2362-470a-8abe-8fe3f3309b63','36b3807b-00d5-4d1f-b875-2dd8061e2404']:
        path=f'v3/20/OT-00009/ORDEN_SERVICIO/{svc.PILOTO[FOLIO][1]}/{photo}'
        photos.append(dict(photoId=photo,storagePath=path,sha256=hashlib.sha256(raw).hexdigest(),mimeType='image/jpeg',sizeBytes=len(raw),signedUrl=BASE+'/storage/v1/object/sign/axia-operational-evidence/'+path+'?token=test'))
    post=Mock(return_value=SimpleNamespace(status_code=200,json=lambda:{'ok':True,'folio':FOLIO,'photos':photos}))
    resp=Mock();resp.status_code=200;resp.iter_content.return_value=[raw]
    ctx=Mock();ctx.__enter__=Mock(return_value=resp);ctx.__exit__=Mock(return_value=False)
    get=Mock(return_value=ctx)
    monkeypatch.setattr(svc.requests,'post',post);monkeypatch.setattr(svc.requests,'get',get)
    yield photos,post,get,raw
    session.cerrar_sesion()

def test_success(setup):
    photos,post,get,raw=setup
    result=svc.descargar_fotos_operativas(FOLIO)
    assert len(result)==2 and all(x.contenido==raw for x in result)
    assert post.call_args.kwargs['headers']['Authorization']=='Bearer test-session'
    assert post.call_args.kwargs['headers']['X-AXIA-Desktop-Grant']=='a'*64
    assert get.call_count==2
    assert all('headers' not in c.kwargs and c.kwargs['allow_redirects'] is False for c in get.call_args_list)

def test_no_session(setup):
    _,post,get,_=setup;session.cerrar_sesion()
    with pytest.raises(svc.EvidenciaNoDisponible):svc.descargar_fotos_operativas(FOLIO)
    post.assert_not_called();get.assert_not_called()

def test_no_grant(setup,monkeypatch):
    _,post,get,_=setup;monkeypatch.delenv('AXIA_DESKTOP_EVIDENCE_GRANT')
    with pytest.raises(svc.EvidenciaNoDisponible):svc.descargar_fotos_operativas(FOLIO)
    post.assert_not_called();get.assert_not_called()

@pytest.mark.parametrize('status',[401,403,404,409,503])
def test_http_failure(setup,status):
    _,post,get,_=setup;post.return_value=SimpleNamespace(status_code=status)
    with pytest.raises(svc.EvidenciaNoDisponible):svc.descargar_fotos_operativas(FOLIO)
    get.assert_not_called()

@pytest.mark.parametrize('field,value',[('signedUrl','https://external.example/photo'),('storagePath','wrong'),('sha256','0'*64),('sizeBytes',1),('mimeType','image/png')])
def test_invalid_photo(setup,field,value):
    photos,post,get,_=setup;photos[0][field]=value
    with pytest.raises(svc.EvidenciaNoDisponible):svc.descargar_fotos_operativas(FOLIO)
    if field in ('signedUrl','storagePath'):get.assert_not_called()

def test_incomplete_manifest(setup):
    photos,post,get,_=setup;photos.pop()
    with pytest.raises(svc.EvidenciaNoDisponible):svc.descargar_fotos_operativas(FOLIO)
    get.assert_not_called()

def test_no_legacy_call(setup):
    _,post,get,_=setup
    with pytest.raises(svc.EvidenciaNoDisponible):svc.descargar_fotos_operativas('OS-00003')
    post.assert_not_called();get.assert_not_called()
