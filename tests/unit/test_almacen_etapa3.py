"""La ejecución normal conecta siempre al Catálogo Maestro AXIA protegido."""
import sys
import types
from pathlib import Path
from services.almacen_service import AlmacenRemoto, crear_almacen

ROOT = Path(__file__).resolve().parents[2]


def _config(monkeypatch):
    mod = types.ModuleType('supabase_config')
    mod.SUPABASE_URL='https://demo.supabase.co'
    mod.SUPABASE_KEY='anon-demo'
    monkeypatch.setitem(sys.modules,'supabase_config',mod)


def test_default_remoto_sin_variables_de_entorno(monkeypatch):
    _config(monkeypatch)
    monkeypatch.delenv('AXIA_ALMACEN_MODO', raising=False)
    remoto=crear_almacen()
    assert isinstance(remoto,AlmacenRemoto) and remoto.remoto and not remoto.laboratorio
    assert remoto.endpoint.endswith('/functions/v1/axia-almacen')
    assert not hasattr(remoto,'service_role_key')


def test_entorno_ignora_solicitudes_de_modo_pruebas(monkeypatch):
    _config(monkeypatch)
    monkeypatch.setenv('AXIA_ALMACEN_MODO','remoto_pruebas')
    remoto=crear_almacen()
    assert remoto._sufijo==''
    assert remoto.laboratorio is False


def test_acciones_apuntan_al_catalogo_unico(monkeypatch):
    _config(monkeypatch)
    svc=crear_almacen()
    svc._usuario_id='8'; svc.token='token-simulado'
    calls=[]
    svc._peticion=lambda a,d=None,**kw: calls.append((a,d)) or []
    svc.catalogo();svc.kardex('TUB-CAN-00001')
    svc.registrar(codigo='TUB-CAN-00001',tipo='ENTRADA',cantidad='5',
      motivo='Ingreso',referencia='FAC-1',destinatario='',usuario={'id_usuario':8},
      idempotencia='11111111-1111-4111-8111-111111111111')
    assert [x[0] for x in calls]==['catalogo','kardex','registrar']
    assert calls[-1][1]['cantidad']=='5'


def test_no_introduce_credenciales_servidor_en_python():
    fuente=(ROOT/'services/almacen_service.py').read_text(encoding='utf-8')
    assert "return AlmacenRemoto(laboratorio=False)" in fuente
    assert "SUPABASE_SERVICE_ROLE_KEY" not in fuente
    assert "AXIA_ALMACEN_MODO', 'simulador'" not in fuente
