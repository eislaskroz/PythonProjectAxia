import io
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from app_context import obtener_usuario_actual
from services import desktop_historical_evidence as svc
from services import sesion_axia_compartida as session

BASE = 'https://example.supabase.co'
FOLIO = 'BIT-00001'
PATH = 'bitacoras/BIT-00001/0123456789abcdef0123456789abcdef_foto.png'
PUBLIC = BASE + '/storage/v1/object/public/bitacoras-evidencias/' + PATH
SIGNED = BASE + '/storage/v1/object/sign/bitacoras-evidencias/' + PATH + '?token=test'


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setitem(sys.modules, 'supabase_config', SimpleNamespace(SUPABASE_URL=BASE, SUPABASE_KEY='public-test'))
    monkeypatch.setitem(obtener_usuario_actual(), 'id_usuario', 2)
    session.establecer_sesion('test-session', 2, int(time.time()) + 1000)
    monkeypatch.setenv('AXIA_DESKTOP_EVIDENCE_GRANT', 'a' * 64)
    buf = io.BytesIO()
    Image.new('RGB', (12, 16), 'blue').save(buf, 'PNG')
    raw = buf.getvalue()
    data = {'ok': True, 'bucket': svc.BUCKET, 'storagePath': PATH, 'expiresIn': 120, 'signedUrl': SIGNED}
    post = Mock(return_value=SimpleNamespace(status_code=200, json=lambda: data))
    response = Mock(status_code=200)
    response.iter_content.return_value = [raw]
    ctx = Mock()
    ctx.__enter__ = Mock(return_value=response)
    ctx.__exit__ = Mock(return_value=False)
    get = Mock(return_value=ctx)
    monkeypatch.setattr(svc.requests, 'post', post)
    monkeypatch.setattr(svc.requests, 'get', get)
    yield data, post, get, raw
    session.cerrar_sesion()


@pytest.mark.parametrize('item', [PATH, PUBLIC, {'storage_path': PATH}, {'url': PUBLIC, 'storage_path': PATH}, {'public_url': PUBLIC}])
def test_reference(item):
    assert svc.ruta_historica(item, FOLIO, BASE) == PATH


@pytest.mark.parametrize('item', [PUBLIC.replace('example.supabase.co', 'other.example'), {'storage_path': PATH, 'url': PUBLIC.replace('BIT-00001', 'BIT-00002')}, {'bucket': 'other', 'storage_path': PATH}, {'storage_path': PATH.replace('BIT-00001', 'BIT-00002')}])
def test_reject_reference(item):
    with pytest.raises(svc.EvidenciaNoDisponible):
        svc.ruta_historica(item, FOLIO, BASE)


def test_local():
    assert svc.ruta_historica('C:/temp/foto.png', FOLIO, BASE) is None


def test_success(setup):
    _, post, get, raw = setup
    result = svc.preparar_fotos_historicas({'Fotos': [{'url': PUBLIC}, {'storage_path': PATH}, 'C:/temp/local.png']}, FOLIO)['Evidencia Fotográfica']
    assert result[0].contenido == result[1].contenido == raw
    assert result[2] == 'C:/temp/local.png'
    assert post.call_count == get.call_count == 1
    assert post.call_args.kwargs['headers']['X-AXIA-Desktop-Grant'] == 'a'*64
    assert get.call_args.args[0] == SIGNED
    assert 'headers' not in get.call_args.kwargs
    assert not get.call_args.kwargs['allow_redirects']


@pytest.mark.parametrize('status', [401, 403, 404, 503])
def test_http_failure(setup, status):
    _, post, get, _ = setup
    post.return_value = SimpleNamespace(status_code=status)
    with pytest.raises(svc.EvidenciaNoDisponible):
        svc.descargar_foto_historica(PATH, FOLIO)
    get.assert_not_called()


@pytest.mark.parametrize('field,value', [('signedUrl', PUBLIC), ('signedUrl', SIGNED.replace('example.supabase.co', 'other.example')), ('storagePath', 'wrong'), ('expiresIn', 999), ('bucket', 'other')])
def test_invalid_reply(setup, field, value):
    data, _, get, _ = setup
    data[field] = value
    with pytest.raises(svc.EvidenciaNoDisponible):
        svc.descargar_foto_historica(PATH, FOLIO)
    get.assert_not_called()


def test_no_session(setup):
    _, post, get, _ = setup
    session.cerrar_sesion()
    with pytest.raises(svc.EvidenciaNoDisponible):
        svc.descargar_foto_historica(PATH, FOLIO)
    post.assert_not_called()
    get.assert_not_called()


def test_no_grant(setup, monkeypatch):
    _, post, get, _ = setup
    monkeypatch.delenv('AXIA_DESKTOP_EVIDENCE_GRANT')
    with pytest.raises(svc.EvidenciaNoDisponible):
        svc.descargar_foto_historica(PATH, FOLIO)
    post.assert_not_called()
    get.assert_not_called()


def test_corrupt_image(setup):
    _, _, get, _ = setup
    get.return_value.__enter__.return_value.iter_content.return_value = [b'invalid']
    with pytest.raises(svc.EvidenciaNoDisponible):
        svc.descargar_foto_historica(PATH, FOLIO)
