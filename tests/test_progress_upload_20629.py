import hashlib
import queue
import sys
import time
from types import SimpleNamespace
from uuid import UUID
from unittest.mock import Mock

import pytest
from PIL import Image
from app_context import obtener_usuario_actual
from services import desktop_historical_upload as upload
from services import sesion_axia_compartida as session
from services import desktop_historical_evidence as historical
from ui import pdf_progress as progress


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, 'supabase_config', SimpleNamespace(SUPABASE_URL='https://example.supabase.co', SUPABASE_KEY='public-test'))
    monkeypatch.setitem(obtener_usuario_actual(), 'id_usuario', 2)
    monkeypatch.setenv('AXIA_DESKTOP_EVIDENCE_GRANT', 'a'*64)
    session.establecer_sesion('test-session', 2, int(time.time()) + 1000)
    path = tmp_path / 'foto.png'
    Image.new('RGB', (20, 20), 'blue').save(path)
    def fake(url, *, headers, data, timeout, allow_redirects):
        assert url == 'https://example.supabase.co/functions/v1/desktop-historical-evidence-upload'
        assert not allow_redirects
        fid = UUID(headers['X-AXIA-File-Id'])
        assert fid.version == 4
        expected = f"{headers['X-AXIA-Module']}/{headers['X-AXIA-Folio']}/{fid.hex}_archivo.{headers['X-AXIA-Extension']}"
        assert hashlib.sha256(data).hexdigest() == headers['X-AXIA-SHA256']
        return SimpleNamespace(status_code=201, json=lambda: dict(ok=True,bucket=upload.BUCKET,storagePath=expected,mime=headers['Content-Type'],sha256=hashlib.sha256(data).hexdigest(),sizeBytes=len(data),alreadyUploaded=False))
    post = Mock(side_effect=fake)
    monkeypatch.setattr(upload.requests, 'post', post)
    yield path, post
    session.cerrar_sesion()


def test_upload_replays_same_path(entorno):
    path, post = entorno
    first = upload.cargar_archivo_historico('bitacoras','BIT-00001',path,'image/png')
    second = upload.cargar_archivo_historico('bitacoras','BIT-00001',path,'image/png')
    assert first == second and first['url'] == '' and first['bucket'] == upload.BUCKET
    assert post.call_count == 2
    assert historical.ruta_historica(first,'BIT-00001','https://example.supabase.co') == first['storage_path']


def test_denied(entorno):
    path, post = entorno
    post.side_effect = None
    post.return_value = SimpleNamespace(status_code=403)
    with pytest.raises(RuntimeError, match='403'):
        upload.cargar_archivo_historico('bitacoras','BIT-00001',path,'image/png')


def test_missing_grant(entorno, monkeypatch):
    path, post = entorno
    monkeypatch.delenv('AXIA_DESKTOP_EVIDENCE_GRANT')
    with pytest.raises(RuntimeError, match='autorización'):
        upload.cargar_archivo_historico('bitacoras','BIT-00001',path,'image/png')
    post.assert_not_called()


def test_wrong_module(entorno):
    path, post = entorno
    with pytest.raises(RuntimeError):
        upload.cargar_archivo_historico('obras-civiles','OBC-0001',path,'image/png')
    post.assert_not_called()


def test_wrong_response(entorno):
    path, post = entorno
    post.side_effect = None
    post.return_value = SimpleNamespace(status_code=201,json=lambda:{'ok':True,'storagePath':'other'})
    with pytest.raises(RuntimeError,match='integridad'):
        upload.cargar_archivo_historico('bitacoras','BIT-00001',path,'image/png')


def test_real_progress_events(entorno, monkeypatch):
    path, _ = entorno
    event_queue = queue.Queue()
    monkeypatch.setattr(progress._context, 'eventos', event_queue, raising=False)
    p1 = 'bitacoras/BIT-00001/'+'a'*32+'_a.png'
    p2 = 'bitacoras/BIT-00001/'+'b'*32+'_b.png'
    fetch = Mock(return_value=path.read_bytes())
    monkeypatch.setattr(historical,'descargar_foto_historica',fetch)
    result = historical.preparar_fotos_historicas({'Fotos':[{'storage_path':p1},{'storage_path':p2}]},'BIT-00001')
    assert len(result['Evidencia Fotográfica']) == 2 and fetch.call_count == 2
    events = [event_queue.get_nowait()[1][1:] for _ in range(3)]
    assert events == [(0,2),(1,2),(2,2)]


def test_nested_decorator_no_new_dialog(monkeypatch):
    monkeypatch.setattr(progress._context,'eventos',queue.Queue(),raising=False)
    @progress.con_progreso_pdf
    def nested(x):
        return x + 1
    assert nested(5) == 6
