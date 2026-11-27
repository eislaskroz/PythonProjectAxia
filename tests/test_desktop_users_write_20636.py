import sys
import time
import types

import pytest

from app_context import obtener_usuario_actual
from services import desktop_users_write as secure
from services import sesion_axia_compartida as session


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setitem(sys.modules, 'supabase_config', types.SimpleNamespace(SUPABASE_URL='https://example.supabase.co', SUPABASE_KEY='anon'))
    monkeypatch.setitem(obtener_usuario_actual(), 'id_usuario', 2)
    monkeypatch.setitem(obtener_usuario_actual(), 'usu_tipo', 1)
    session.establecer_sesion('jwt.test.value', 2, int(time.time()) + 600)
    calls = []
    def setup(status=200, body=None, error=None):
        def post(url, **kwargs):
            calls.append((url, kwargs))
            if error:
                raise error
            return types.SimpleNamespace(status_code=status, json=lambda: body if body is not None else {'ok': True, 'data': {'id_usuario': 45}})
        monkeypatch.setattr(secure.requests, 'post', post)
        return calls
    yield setup
    session.cerrar_sesion()


def alta():
    return {'usu_nickname': 'AXIA_TEST', 'usu_nombre': 'Prueba', 'usu_apellido': 'Ficticia', 'usu_tipo': '4', 'usu_password': 'Nueva!12345', 'confirmar_password': 'Nueva!12345', 'usu_rfc': 'NO_ENVIAR', 'usu_acceso_habilitado': True}


def cuenta(**extra):
    return {'id_usuario': 45, 'usu_nickname': 'AXIA_TEST', 'usu_nombre': 'Prueba', 'usu_apellido': 'Ficticia', 'usu_tipo': 4, 'usu_correo': None, 'usu_depto': None, 'usu_puesto': None, 'usu_activo': True, 'usu_acceso_habilitado': False, 'usu_fecha_baja': None, **extra}


def test_create(api):
    calls = api()
    assert secure.guardar_cuenta(alta(), 'Admin!12345')[0]
    url, kwargs = calls[0]
    assert url.endswith('/desktop-users-write') and kwargs['allow_redirects'] is False
    assert kwargs['headers']['Authorization'] == 'Bearer jwt.test.value'
    body = kwargs['json']
    assert body['accion'] == 'crear' and body['id_usuario'] is None and body['esperado'] == {}
    assert body['datos'] == {'usu_nickname': 'AXIA_TEST', 'usu_nombre': 'Prueba', 'usu_apellido': 'Ficticia', 'usu_tipo': 4}
    assert body['activar'] is False


def test_patch_preserves_fields(api):
    calls = api()
    assert secure.guardar_cuenta({'usu_nombre': 'Prueba', 'usu_puesto': 'Técnico', 'usu_rfc': 'NO_ENVIAR'}, 'Admin!12345', cuenta())[0]
    body = calls[0][1]['json']
    assert body['datos'] == {'usu_puesto': 'Técnico'} and body['esperado']['usu_puesto'] is None
    assert body['passwordNuevo'] is None and body['activar'] is False


@pytest.mark.parametrize('activar', [False, True])
def test_explicit_activation(api, activar):
    calls = api()
    assert secure.guardar_cuenta({'usu_password': 'Nueva!12345', 'confirmar_password': 'Nueva!12345'}, 'Admin!12345', cuenta(), activar)[0]
    assert calls[0][1]['json']['activar'] is activar


@pytest.mark.parametrize('target', [cuenta(id_usuario=2), cuenta(usu_tipo=1), cuenta(usu_activo=False), cuenta(usu_fecha_baja='2026-11-27')])
def test_protected_target(api, target):
    calls = api()
    assert not secure.guardar_cuenta({'usu_puesto': 'Nuevo'}, 'Admin!12345', target)[0]
    assert not calls


def test_role_two(api, monkeypatch):
    calls = api()
    monkeypatch.setitem(obtener_usuario_actual(), 'usu_tipo', 2)
    assert not secure.guardar_cuenta(alta(), 'Admin!12345')[0] and not calls


@pytest.mark.parametrize('changes', [{'usu_tipo':'1'}, {'usu_password':'bad'}, {'confirmar_password':'distinta'}, {'usu_nickname':'abc%'}])
def test_invalid_create(api, changes):
    calls = api()
    assert not secure.guardar_cuenta({**alta(), **changes}, 'Admin!12345')[0] and not calls


@pytest.mark.parametrize('status', [400, 401, 403, 409, 429, 500])
def test_errors(api, status):
    calls = api(status=status, body={'ok': False, 'error': 'PRIVATE', 'requestId': 'dea8cdfe-aef1-4afe-ab1c-c501d550bed3'})
    ok, msg, _ = secure.guardar_cuenta(alta(), 'Admin!12345')
    assert not ok and 'PRIVATE' not in msg and len(calls) == 1


def test_response_wrong_id(api):
    api(body={'ok': True, 'data': {'id_usuario': 46}})
    assert not secure.guardar_cuenta({'usu_puesto': 'Nuevo'}, 'Admin!12345', cuenta())[0]


def test_response_hash(api):
    api(body={'ok': True, 'data': {'id_usuario': 45, 'usu_password': 'HASH'}})
    assert not secure.guardar_cuenta(alta(), 'Admin!12345')[0]


def test_network_no_retry(api):
    calls = api(error=secure.requests.ConnectionError('private'))
    ok, msg, _ = secure.guardar_cuenta(alta(), 'Admin!12345')
    assert not ok and len(calls) == 1 and 'private' not in msg
