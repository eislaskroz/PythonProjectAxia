import json
import sys
import time
import types

import pytest
import requests
from cryptography.fernet import Fernet

from services import desktop_audit_write as audit
from services import sesion_axia_compartida as session
from services import movimientos_service as movimientos
from security import data_encryption as encryption


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    monkeypatch.setattr(audit, 'user_data_dir', lambda: tmp_path)
    key = Fernet.generate_key()
    monkeypatch.setattr(encryption, '_obtener_fernet', lambda: Fernet(key))
    monkeypatch.setitem(sys.modules, 'supabase_config', types.SimpleNamespace(SUPABASE_URL='https://example.supabase.co', SUPABASE_KEY='anon'))
    session.establecer_sesion('jwt.test.value', 53, int(time.time()) + 600)
    calls = []
    def setup(status=200, error=None, mismatch=False):
        def post(url, **kwargs):
            calls.append((url, kwargs))
            if error:
                raise error
            return types.SimpleNamespace(status_code=status, json=lambda: {'ok': status == 200, 'data': {'evento_id': 'otro' if mismatch else kwargs['json']['evento_id'], 'id_movimiento': 42, 'recuperado': False}})
        monkeypatch.setattr(audit.requests, 'post', post)
        return calls
    yield setup, tmp_path
    session.cerrar_sesion()


def datos():
    return {'modulo':'NAVEGACION','accion':'ABRIR_VISTA','descripcion':'Prueba local','registro_afectado':'PRUEBA','id_usuario':2,'usuario':'admin','fecha_hora':'1900-01-01'}


def pendientes(tmp_path, actor=53):
    return list((tmp_path / 'audit_pending_v2' / str(actor)).glob('*.enc'))


def test_envia_solo_campos_cliente(entorno):
    setup, tmp = entorno
    calls = setup()
    assert audit.registrar_evento(53, datos())
    url, kw = calls[0]
    assert url.endswith('/desktop-audit-write') and not kw['allow_redirects']
    assert kw['headers']['Authorization'] == 'Bearer jwt.test.value'
    assert set(kw['json']) == {'evento_id','evento'}
    assert not {'id_usuario','usuario','fecha_hora'} & set(kw['json']['evento'])
    assert not pendientes(tmp)


def test_reintento_mismo_uuid_y_contenido(entorno):
    setup, tmp = entorno
    calls = setup(error=requests.ConnectionError())
    assert not audit.registrar_evento(53, datos())
    archivos = pendientes(tmp)
    assert len(archivos) == 1 and archivos[0].read_text().startswith('enc::')
    assert 'Prueba local' not in archivos[0].read_text()
    original = calls[0][1]['json']
    setup()
    assert audit.reintentar_uno(53)
    assert calls[-1][1]['json'] == original
    assert not pendientes(tmp)


def test_no_reenvia_entre_usuarios(entorno):
    setup, tmp = entorno
    calls = setup(error=requests.ConnectionError())
    assert not audit.registrar_evento(53, datos())
    session.establecer_sesion('otro', 2, int(time.time()) + 600)
    setup()
    assert not audit.reintentar_uno(2)
    assert len(calls) == 1 and len(pendientes(tmp)) == 1


@pytest.mark.parametrize('status', [400,403,409,413])
def test_rechazo_conservado_sin_reenvio(entorno,status):
    setup,tmp = entorno
    calls=setup(status=status)
    assert not audit.registrar_evento(53,datos())
    assert not pendientes(tmp)
    assert len(list((tmp/'audit_pending_v2'/'53'/'rechazados').glob('*.enc'))) == 1
    assert not audit.reintentar_uno(53) and len(calls)==1


@pytest.mark.parametrize('status',[401,429,500])
def test_fallo_reintentable(entorno,status):
    setup,tmp=entorno
    setup(status=status)
    assert not audit.registrar_evento(53,datos()) and len(pendientes(tmp))==1


def test_respuesta_no_correspondiente(entorno):
    setup,tmp=entorno
    setup(mismatch=True)
    assert not audit.registrar_evento(53,datos()) and len(pendientes(tmp))==1


def test_sin_sesion(entorno):
    setup,tmp=entorno
    calls=setup()
    session.cerrar_sesion()
    assert not audit.registrar_evento(53,datos()) and not calls and len(pendientes(tmp))==1


def test_movimientos_rechaza_identidad_distinta(monkeypatch):
    monkeypatch.setattr(movimientos,'obtener_usuario_actual',lambda:{'id_usuario':53})
    monkeypatch.setattr(movimientos,'registrar_evento',lambda *a:pytest.fail('No enviar'))
    assert not movimientos.registrar_movimiento(id_usuario=2)


def test_no_guarda_en_claro(entorno,monkeypatch):
    setup,tmp=entorno
    setup(error=requests.ConnectionError())
    monkeypatch.setattr(encryption,'_obtener_fernet',lambda:None)
    assert not audit.registrar_evento(53,datos()) and not pendientes(tmp)


def test_reintenta_pendiente_tras_envio_correcto(entorno):
    setup,tmp=entorno
    calls=setup(error=requests.ConnectionError())
    assert not audit.registrar_evento(53,datos())
    first=calls[0][1]['json']
    setup()
    assert audit.registrar_evento(53,datos())
    assert calls[-1][1]['json']==first and not pendientes(tmp)
