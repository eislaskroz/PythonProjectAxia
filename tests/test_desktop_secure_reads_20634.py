import sys
import time
import types

import pytest

from app_context import obtener_usuario_actual
from services import desktop_secure_reads as secure
from services import sesion_axia_compartida as session


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setitem(sys.modules, "supabase_config", types.SimpleNamespace(SUPABASE_URL="https://example.supabase.co", SUPABASE_KEY="anon"))
    monkeypatch.setitem(obtener_usuario_actual(), "id_usuario", 31)
    session.establecer_sesion("jwt.test.value", 31, int(time.time()) + 600)
    calls = []

    def setup(status=200, data=None, error=None):
        def post(url, **kwargs):
            calls.append((url, kwargs))
            if error:
                raise error
            value = data(kwargs["json"]) if callable(data) else data
            return types.SimpleNamespace(status_code=status, json=lambda: {"ok": status == 200, "data": value, "requestId": "dea8cdfe-aef1-4afe-ab1c-c501d550bed3"})
        monkeypatch.setattr(secure.requests, "post", post)
        return calls

    yield setup
    session.cerrar_sesion()


def test_authenticated_request(api):
    calls = api(data=[{"id_usuario": 31}])
    assert secure.listar("desktop-users", "listar", 100) == [{"id_usuario": 31}]
    assert calls[0][0].endswith("/desktop-users")
    assert calls[0][1]["headers"]["Authorization"] == "Bearer jwt.test.value"
    assert calls[0][1]["allow_redirects"] is False


def test_pagination(api):
    calls = api(data=lambda b: [{"id": i} for i in range(b["offset"], b["offset"] + b["limit"])])
    rows = secure.listar("desktop-audit", "movimientos", 500)
    assert len(rows) == 500
    assert [(c[1]["json"]["offset"], c[1]["json"]["limit"]) for c in calls] == [(0, 200), (200, 200), (400, 100)]


@pytest.mark.parametrize("status", [301, 400, 401, 403, 404, 429, 500])
def test_fail_closed(api, status):
    calls = api(status=status)
    with pytest.raises(secure.ConsultaSeguraError):
        secure.consultar("desktop-audit", "mis_movimientos")
    assert len(calls) == 1


def test_user_session_mismatch(api, monkeypatch):
    calls = api(data=[])
    monkeypatch.setitem(obtener_usuario_actual(), "id_usuario", 2)
    with pytest.raises(secure.ConsultaSeguraError):
        secure.consultar("desktop-audit", "mis_movimientos")
    assert not calls


def test_reject_password(api):
    api(data=[{"usu_password": "ficticio"}])
    with pytest.raises(secure.ConsultaSeguraError):
        secure.listar("desktop-users", "listar", 10)


def test_own_profile(api):
    calls = api(data={"id_usuario": 31})
    assert secure.consultar("desktop-users", "mi_perfil")["id_usuario"] == 31
    assert calls[0][1]["json"] == {"accion": "mi_perfil"}


def test_no_writes(api):
    calls = api()
    with pytest.raises(secure.ConsultaSeguraError):
        secure.consultar("desktop-users", "actualizar")
    assert not calls


def test_network(api):
    api(error=secure.requests.ConnectionError())
    with pytest.raises(secure.ConsultaSeguraError):
        secure.consultar("desktop-audit", "accesos")
