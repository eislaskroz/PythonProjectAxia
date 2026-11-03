"""Pruebas offline de altas y bajas RH: nunca usar registros reales."""
from __future__ import annotations

from pathlib import Path
from test_rrhh_integracion_20604 import _load_service

ROOT = Path(__file__).resolve().parents[2]


def test_alta_rrhh_no_envia_rol_ni_password(monkeypatch):
    modulo, envios = _load_service(monkeypatch)
    datos = {'usu_nickname':'alta.prueba', 'usu_nombre':'ALTA', 'usu_apellido':'SIMULADA',
             'usu_tipo':'1','usu_password':'CLAVE_NO_ENVIAR','usu_correo':'PERSONA@EJEMPLO.COM'}
    ok, _, _ = modulo.alta_usuario_rrhh(datos,'clave-ficticia','Alta laboral simulada')
    assert ok
    payload=envios[0][1]['json']
    assert payload['accion']=='alta'
    assert payload['nickname']=='alta.prueba'
    assert payload['datos']['usu_nombre']=='ALTA'
    assert payload['datos']['usu_correo']=='persona@ejemplo.com'
    assert set(payload['datos']).isdisjoint({'usu_tipo','usu_password','usu_activo','id_usuario'})


def test_alta_invalida_sin_envio(monkeypatch):
    modulo, envios = _load_service(monkeypatch)
    ok, _, _ = modulo.alta_usuario_rrhh({'usu_nickname':'a','usu_nombre':'A','usu_apellido':'B'},'clave','Motivo suficiente')
    assert not ok
    assert not envios


def test_baja_unicamente_activos_no_protegidos(monkeypatch):
    modulo, envios = _load_service(monkeypatch)
    ok, _, _ = modulo.baja_usuario_rrhh(
       {'id_usuario':123,'usu_tipo':4,'usu_activo':True},'clave','Finalización de contrato')
    assert ok
    payload=envios[0][1]['json']
    assert payload['accion']=='baja' and payload['activo_esperado'] is True
    assert payload['id_usuario']==123
    assert 'usu_password' not in payload
    assert 'usu_tipo' not in payload


def test_no_baja_administrador_ni_rrhh(monkeypatch):
    modulo, envios=_load_service(monkeypatch)
    for tipo in (1,10):
        ok,_,_=modulo.baja_usuario_rrhh({'id_usuario':34,'usu_tipo':tipo,'usu_activo':True},'clave','Cambio de contrato')
        assert not ok
    assert not envios


def test_no_baja_si_ya_inactivo(monkeypatch):
    modulo, envios=_load_service(monkeypatch)
    ok,_,_=modulo.baja_usuario_rrhh({'id_usuario':34,'usu_tipo':4,'usu_activo':False},'clave','Baja laboral')
    assert not ok and not envios


def test_sql_conserva_historial_y_control_rol():
    sql=(ROOT/'migrations/20261103_rrhh_altas_bajas.sql').read_text(encoding='utf8')
    assert "current_user <> 'service_role'" in sql
    assert 'usu_activo=false' in sql
    assert 'usu_acceso_habilitado=false' in sql
    assert 'usu_password=p_hash_revocado' in sql
    assert 'axia_rrhh_historial' in sql
    assert "v_usuario.usu_tipo IN (1,10)" in sql
    assert 'usu_tipo,usu_activo,usu_acceso_habilitado' in sql
    assert 'DELETE FROM public.db_usuarios' not in sql


def test_edge_rechaza_cambio_de_roles_y_usa_hash_aleatorio():
    edge=(ROOT/'supabase/functions/axia-rrhh-usuarios/index.ts').read_text(encoding='utf8')
    assert "action==='alta'" in edge
    assert "action==='baja'" in edge
    assert 'Object.keys(datos).some(k=>!FIELDS.includes(k))' in edge
    assert "await bcrypt.hash(randomSecret(),12)" in edge
    assert 'actor?.usu_activo!==true' in edge


def test_login_desktop_rechaza_bajas_y_pendientes():
    login=(ROOT/'services/auth_service.py').read_text(encoding='utf8')
    assert "usuario.get('usu_activo') is not True" in login
    assert "usuario.get('usu_acceso_habilitado') is not True" in login
