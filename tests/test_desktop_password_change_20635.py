import sys
import time
import types

import pytest

from app_context import obtener_usuario_actual
from services import desktop_password_change as secure
from services import sesion_axia_compartida as session


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setitem(sys.modules, "supabase_config", types.SimpleNamespace(SUPABASE_URL="https://example.supabase.co", SUPABASE_KEY="anon"))
    monkeypatch.setitem(obtener_usuario_actual(), "id_usuario", 31)
    session.establecer_sesion("jwt.test.value", 31, int(time.time()) + 600)
    calls = []

    def setup(status=200, body=None, error=None):
        def post(url, **kwargs):
            calls.append((url, kwargs))
            if error:
                raise error
            data = body if body is not None else {"ok": True, "data": {"cambiado": True}}
            return types.SimpleNamespace(status_code=status, json=lambda: data)
        monkeypatch.setattr(secure.requests, "post", post)
        return calls

    yield setup
    session.cerrar_sesion()


def test_authenticated_change(api):
    calls = api()
    ok, _ = secure.cambiar_password("Anterior!123", "Nueva!12345", "Nueva!12345")
    assert ok
    assert calls[0][0].endswith("/desktop-password-change")
    assert calls[0][1]["headers"]["Authorization"] == "Bearer jwt.test.value"
    assert calls[0][1]["json"] == {"passwordActual": "Anterior!123", "passwordNuevo": "Nueva!12345"}
    assert calls[0][1]["allow_redirects"] is False


@pytest.mark.parametrize("status", [301, 400, 401, 403, 409, 429, 500])
def test_failure(api, status):
    calls = api(status=status, body={"ok": False, "error": "NO MOSTRAR", "requestId": "dea8cdfe-aef1-4afe-ab1c-c501d550bed3"})
    ok, message = secure.cambiar_password("Anterior!123", "Nueva!12345", "Nueva!12345")
    assert not ok and "NO MOSTRAR" not in message and "dea8cdfe" in message
    assert len(calls) == 1


@pytest.mark.parametrize("actual,nuevo,confirmacion", [("", "Nueva!12345", "Nueva!12345"), ("Anterior!123", "Nueva!12345", "otra"), ("Anterior!123", "abc", "abc"), ("Anterior!123", "Anterior!123", "Anterior!123"), ("Anterior!123", "Nueva!12345" + "é"*40, "Nueva!12345" + "é"*40), ("a"*73, "Nueva!12345", "Nueva!12345")])
def test_invalid_local(api, actual, nuevo, confirmacion):
    calls = api()
    assert not secure.cambiar_password(actual, nuevo, confirmacion)[0]
    assert not calls


def test_session_mismatch(api, monkeypatch):
    calls = api()
    monkeypatch.setitem(obtener_usuario_actual(), "id_usuario", 2)
    assert not secure.cambiar_password("Anterior!123", "Nueva!12345", "Nueva!12345")[0]
    assert not calls


def test_invalid_response(api):
    api(body={"ok": True, "data": {"cambiado": False}})
    assert not secure.cambiar_password("Anterior!123", "Nueva!12345", "Nueva!12345")[0]


def test_network_failure(api):
    api(error=secure.requests.ConnectionError("private detail"))
    ok, message = secure.cambiar_password("Anterior!123", "Nueva!12345", "Nueva!12345")
    assert not ok and "private detail" not in message
