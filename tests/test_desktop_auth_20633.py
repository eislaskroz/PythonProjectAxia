import time
import types
import sys
import pytest
from services import auth_service as auth


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setitem(sys.modules, "supabase_config", types.SimpleNamespace(SUPABASE_URL="https://example.supabase.co", SUPABASE_KEY="anon"))
    def setup(status=200, data=None, error=None):
        body = {"ok": status == 200, "data": data}
        calls = []
        def post(url, **kwargs):
            calls.append((url, kwargs))
            if error:
                raise error
            return types.SimpleNamespace(status_code=status, json=lambda: body)
        monkeypatch.setattr(auth.requests, "post", post)
        return calls
    return setup


def valid(**changes):
    return {"id_usuario": 2, "usu_tipo": 1, "usu_nickname": "admin", "usu_nombre": "Test", "usu_apellido": "User", "accessToken": "a.b.c", "expiresAtEpochSeconds": int(time.time()) + 3600, **changes}


def test_login_servidor(api):
    calls = api(data=valid(usu_password="no debe regresar al cliente"))
    user, token, expiry = auth.validar_login("admin", "ficticia", {"nombre_equipo": "PC", "ubicacion": {}})
    assert user["id_usuario"] == 2 and "usu_password" not in user
    assert token == "a.b.c" and expiry > time.time()
    assert len(calls) == 1 and calls[0][0].endswith("/desktop-auth")
    assert calls[0][1]["allow_redirects"] is False


@pytest.mark.parametrize("status", [400, 403, 404, 429, 500])
def test_error_no_autentica(api, status):
    api(status=status)
    with pytest.raises(auth.ErrorAutenticacion):
        auth.validar_login("admin", "ficticia")


def test_credenciales_rechazadas(api):
    api(status=401)
    assert auth.validar_login("admin", "ficticia") is None


@pytest.mark.parametrize("changes", [{"id_usuario": 0}, {"usu_tipo": 11}, {"usu_nickname": "otro"}, {"accessToken": ""}, {"expiresAtEpochSeconds": 0}])
def test_sesion_invalida(api, changes):
    api(data=valid(**changes))
    with pytest.raises(auth.ErrorAutenticacion):
        auth.validar_login("admin", "ficticia")


def test_sin_red(api):
    api(error=auth.requests.ConnectionError())
    with pytest.raises(auth.ErrorAutenticacion):
        auth.validar_login("admin", "ficticia")
