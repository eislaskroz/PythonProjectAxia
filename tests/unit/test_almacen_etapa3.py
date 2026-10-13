"""Laboratorio Etapa 3: pruebas locales y contratos de enrutamiento (sin acceso a Supabase)."""
import json
import sys
import types
from pathlib import Path

import pytest

from services.almacen_service import AlmacenSimulador, AlmacenRemoto, crear_almacen

ROOT = Path(__file__).resolve().parents[2]


def test_modo_simulador_de_forma_predeterminada(monkeypatch):
    monkeypatch.delenv('AXIA_ALMACEN_MODO', raising=False)
    assert isinstance(crear_almacen(), AlmacenSimulador)


def test_modo_laboratorio_explicito(monkeypatch):
    fake = types.ModuleType('supabase_config')
    fake.SUPABASE_URL = 'https://demo.supabase.co'
    fake.SUPABASE_KEY = 'anon-publica-demo'
    monkeypatch.setitem(sys.modules, 'supabase_config', fake)
    monkeypatch.setenv('AXIA_ALMACEN_MODO', 'remoto_pruebas')
    remoto = crear_almacen()
    assert remoto.remoto and remoto.laboratorio
    assert remoto.endpoint.endswith('/functions/v1/axia-almacen')
    assert not hasattr(remoto, 'service_role_key')
    assert remoto._sufijo == '_lab'


def test_endpoints_laboratorio_no_usen_produccion(monkeypatch):
    fake = types.ModuleType('supabase_config')
    fake.SUPABASE_URL = 'https://demo.supabase.co'
    fake.SUPABASE_KEY = 'anon-publica-demo'
    monkeypatch.setitem(sys.modules, 'supabase_config', fake)
    svc = AlmacenRemoto(laboratorio=True)
    svc._usuario_id = '8'
    svc.token = 'token-simulado'
    calls = []
    monkeypatch.setattr(svc, '_peticion', lambda accion, datos=None, **kw: calls.append((accion, datos)) or ([] if accion != 'registrar_lab' else {'saldo_nuevo':'5'}))
    svc.catalogo()
    svc.kardex('TEST-01')
    svc.registrar(codigo='TEST-01', tipo='ENTRADA', cantidad='5', motivo='Lab',
                 referencia='PRUEBA', destinatario='', usuario={'id_usuario':8})
    assert [c[0] for c in calls] == ['catalogo_lab', 'kardex_lab', 'registrar_lab']
    assert calls[-1][1]['cantidad'] == '5'


def test_identidad_distinta_bloqueada(monkeypatch):
    fake = types.ModuleType('supabase_config')
    fake.SUPABASE_URL = 'https://demo.supabase.co'
    fake.SUPABASE_KEY = 'anon-publica-demo'
    monkeypatch.setitem(sys.modules, 'supabase_config', fake)
    svc = AlmacenRemoto(laboratorio=True)
    svc._usuario_id = '8'
    with pytest.raises(PermissionError, match='cambiado de usuario'):
        svc.registrar(codigo='X', tipo='ENTRADA', cantidad=1, motivo='prueba',
                     referencia='', destinatario='', usuario={'id_usuario':1})


def test_catalogo_semilla_1886_codigos_unicos_y_saldos_no_migrados():
    catalogo = json.loads((ROOT/'assets'/'almacen_catalogo_eleventa.json').read_text(encoding='utf-8'))
    assert len(catalogo) == 1886
    assert len({p['codigo'] for p in catalogo}) == len(catalogo)
    seed = (ROOT/'supabase'/'seeds'/'20261013_axia_almacen_lab_catalogo.sql').read_text(encoding='utf-8')
    assert seed.count('ON CONFLICT (codigo) DO UPDATE') == 8
    assert 'saldo=EXCLUDED' not in seed
    assert 'saldo_exportado' in seed
    migration = (ROOT/'supabase'/'migrations'/'20261013_axia_almacen_etapa3_laboratorio.sql').read_text(encoding='utf-8')
    assert 'movimientos_habilitados boolean NOT NULL DEFAULT false' in migration
    assert 'ALMACEN_NO_HABILITADO' not in migration
    assert 'REVOKE ALL ON' in migration


def test_modo_invalido_no_recae_silenciosamente_a_simulador(monkeypatch):
    monkeypatch.setenv('AXIA_ALMACEN_MODO', 'cualquier_otro')
    with pytest.raises(ValueError, match='inválido'):
        crear_almacen()
