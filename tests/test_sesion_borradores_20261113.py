from __future__ import annotations
import time

from services import sesion_axia_compartida as sesion


def test_token_no_se_expone_a_otra_cuenta():
    sesion.establecer_sesion('test.only.token', 10, int(time.time()) + 500)
    assert sesion.obtener_sesion(10) == 'test.only.token'
    assert sesion.obtener_sesion(11) is None
    sesion.cerrar_sesion()
    assert sesion.obtener_sesion(10) is None


def test_sesion_vencida_no_se_utiliza():
    sesion.establecer_sesion('expired', 10, int(time.time()) - 10)
    assert sesion.obtener_sesion(10) is None
    sesion.cerrar_sesion()


def test_sesion_movil_con_id_distinto_rechazada(monkeypatch):
    class MockResp:
        def raise_for_status(self): pass
        def json(self):
            return {'ok': True, 'data': {'id_usuario': 55, 'accessToken': 'X', 'expiresAtEpochSeconds': int(time.time()) + 1000}}
    import sys
    import types
    fake = types.SimpleNamespace(SUPABASE_URL='https://example.supabase.co', SUPABASE_KEY='anon')
    monkeypatch.setitem(sys.modules, 'supabase_config', fake)
    monkeypatch.setattr(sesion.requests, 'post', lambda *args, **kwargs: MockResp())
    try:
        sesion.solicitar_sesion('user', 'pass', 99)
    except PermissionError:
        pass
    else:
        assert False, 'Debe rechazar el usuario distinto'
