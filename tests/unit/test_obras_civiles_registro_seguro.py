"""Contrato de guardado nuevo: Edge Function, seguridad e idempotencia."""
import ast
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
REQUEST = '997f4fd9-3bee-4562-bc1d-b46ce17b3cba'
REG = {'obc_id': 7, 'obc_folio': 'OBC-0002', 'obc_request_id': REQUEST}


def _service(monkeypatch, resultados):
    ruta = ROOT / 'services' / 'obras_civiles_service.py'
    tree = ast.parse(ruta.read_text(encoding='utf-8'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='crear_obra_civil']
    gateway = ModuleType('services.obra_civil_gateway')
    gateway.SesionObraCivilInvalida = type('SesionObraCivilInvalida', (PermissionError,), {})
    gateway.peticion_obra_civil = Mock(side_effect=list(resultados))
    monkeypatch.setitem(sys.modules, 'services.obra_civil_gateway', gateway)
    ns = {
        'normalizar_campos_fecha': lambda x: x,
        'logger': Mock(), 'register_error': Mock(),
        'registrar_movimiento_seguro': Mock(),
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]),str(ruta),'exec'),ns)
    return ns['crear_obra_civil'], gateway.peticion_obra_civil, gateway.SesionObraCivilInvalida


def test_guardado_nuevo_no_envia_folio_ni_identidad_falsificables(monkeypatch):
    guardar, api, _ = _service(monkeypatch, [None, REG])
    assert guardar({'obc_request_id':REQUEST,'obc_folio':'OBC-0001',
                   'creado_por':'OTRO','obc_estatus':999,'obc_cliente':'Prueba'},usuario_id=3)==[REG]
    assert api.call_count==2
    assert api.call_args_list[0].args[:2]==('consultar',REQUEST)
    assert api.call_args_list[1].args[:2]==('guardar',REQUEST)
    assert api.call_args_list[1].kwargs['usuario_id']==3
    assert api.call_args_list[1].kwargs['datos']=={'obc_cliente':'Prueba'}


def test_reintento_recupera_mismo_folio_sin_guardar(monkeypatch):
    guardar, api, _ = _service(monkeypatch,[REG])
    assert guardar({'obc_request_id':REQUEST},usuario_id=3)==[REG]
    assert api.call_count==1
    assert api.call_args.args[0]=='consultar'


def test_corte_de_red_consulta_uuid_y_no_repite_insert(monkeypatch):
    guardar, api, _ = _service(monkeypatch,[None,ConnectionError('corte'),REG])
    assert guardar({'obc_request_id':REQUEST},usuario_id=3)==[REG]
    assert [x.args[0] for x in api.call_args_list]==['consultar','guardar','consultar']


def test_sin_confirmacion_cierra_sin_crear_nuevo(monkeypatch):
    guardar, api, _ = _service(monkeypatch,[None,ConnectionError('corte'),None])
    assert guardar({'obc_request_id':REQUEST},usuario_id=3) is None
    assert [x.args[0] for x in api.call_args_list]==['consultar','guardar','consultar']


def test_si_no_hay_sesion_no_hace_insert(monkeypatch):
    guardar, api, ErrorSesion = _service(monkeypatch,[])
    api.side_effect=ErrorSesion('Sin autorización')
    with pytest.raises(ErrorSesion):
        guardar({'obc_request_id':REQUEST},usuario_id=3)
    assert api.call_count==1
    assert api.call_args.args[0]=='consultar'


def test_no_existe_insert_directo_ni_rpc_publica():
    codigo=(ROOT/'services/obras_civiles_service.py').read_text(encoding='utf-8')
    segmento=codigo.split('def crear_obra_civil',1)[1].split('def obtener_obras_civiles',1)[0]
    assert '.insert(' not in segmento
    assert 'supabase.rpc(' not in segmento
    assert "peticion_obra_civil('guardar'" in segmento


def test_function_validates_signature_and_owner():
    codigo=(ROOT/'supabase/functions/axia-obras-civiles/index.ts').read_text(encoding='utf-8')
    assert "crypto.subtle.verify('HMAC'" in codigo
    assert "claims!.alcance !== 'levantamientos_lectura'" in codigo
    assert 'SOLICITUD_AJENA' in codigo
    assert "error.code==='23505'" in codigo
    assert "const registro={...raw,obc_request_id:solicitud,creado_por:user.nickname,obc_estatus:1}" in codigo
