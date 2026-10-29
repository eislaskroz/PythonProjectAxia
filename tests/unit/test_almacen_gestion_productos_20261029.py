"""CRUD seguro del catálogo AXIA; pruebas sin Supabase/GUI."""
from decimal import Decimal
import sys
import types
from pathlib import Path
import pytest

from services.almacen_service import AlmacenSimulador, AlmacenRemoto, validar_producto

ADMIN = {'id_usuario': 1, 'usu_tipo': 1, 'usuario': 'admin'}
OPERADOR = {'id_usuario': 4, 'usu_tipo': 4, 'usuario': 'op'}
DEMO = {'codigo':'OLD1','producto':'Tubo EMT','departamento':'MATERIALES',
        'costo':'10','venta':'12','minimo':'1','maximo':'20'}


def nuevo(codigo='NEW1'):
    return {'codigo':codigo,'producto':'Conector','departamento':'REDES','costo':'2.30',
            'venta':'3.50','minimo':'1.500','maximo':'10'}


def test_crear_editar_y_conservar_saldo():
    svc = AlmacenSimulador([DEMO])
    svc.crear_producto(datos=nuevo(),usuario=ADMIN)
    assert {x['codigo'] for x in svc.catalogo()} == {'NEW1','OLD1'}
    edited = nuevo()
    edited['producto']='Conector CAT6'
    edited['costo']='5.22'
    assert svc.editar_producto(codigo='NEW1',datos=edited,usuario=ADMIN)['producto']=='Conector CAT6'
    assert next(p for p in svc.catalogo() if p['codigo']=='NEW1')['saldo']=='0'
    with pytest.raises(ValueError,match='ya existe'):
        svc.crear_producto(datos=nuevo(),usuario=ADMIN)
    with pytest.raises(ValueError,match='código no puede'):
        svc.editar_producto(codigo='NEW1',datos=nuevo('DIFERENTE'),usuario=ADMIN)


def test_borrado_logico_reactivar_y_proteccion_historico():
    svc = AlmacenSimulador([DEMO])
    svc.registrar(codigo='OLD1',tipo='ENTRADA',cantidad='3',motivo='Llegada',
                  referencia='',destinatario='',usuario=ADMIN)
    with pytest.raises(ValueError,match='existencia'):
        svc.desactivar_producto(codigo='OLD1',usuario=ADMIN)
    svc.registrar(codigo='OLD1',tipo='SALIDA',cantidad='3',motivo='Salida',
                  referencia='',destinatario='Técnico',usuario=ADMIN)
    assert svc.desactivar_producto(codigo='OLD1',usuario=ADMIN)['activo'] is False
    assert svc.catalogo()==[]
    assert svc.catalogo(incluir_inactivos=True)[0]['activo'] is False
    assert len(svc.kardex('OLD1'))==2
    with pytest.raises(ValueError,match='activo'):
        svc.registrar(codigo='OLD1',tipo='ENTRADA',cantidad='1',motivo='Prueba',
                  referencia='',destinatario='',usuario=ADMIN)
    svc.reactivar_producto(codigo='OLD1',usuario=ADMIN)
    assert svc.catalogo()[0]['codigo']=='OLD1'
    assert len(svc.kardex('OLD1'))==2


def test_validaciones_y_roles():
    svc = AlmacenSimulador([DEMO])
    with pytest.raises(PermissionError):
        svc.crear_producto(datos=nuevo(),usuario=OPERADOR)
    for field,value in [('costo','-1'),('venta','NaN'),('minimo','1.5555'),('maximo','abc')]:
        v=nuevo()
        v[field]=value
        with pytest.raises(ValueError):
            validar_producto(v)
    assert validar_producto(nuevo())['venta']=='3.50'


def test_remoto_envia_solo_acciones_autorizadas(monkeypatch):
    fake=types.ModuleType('supabase_config')
    fake.SUPABASE_URL='https://demo.supabase.co'
    fake.SUPABASE_KEY='anon-demo'
    monkeypatch.setitem(sys.modules,'supabase_config',fake)
    svc=AlmacenRemoto(laboratorio=True)
    svc._usuario_id='1'
    svc.token='token'
    calls=[]
    svc._peticion=lambda action, payload=None, **kw: calls.append((action,payload)) or {'ok':True}
    svc.catalogo(incluir_inactivos=True)
    svc.crear_producto(datos=nuevo(),usuario=ADMIN)
    svc.editar_producto(codigo='NEW1',datos=nuevo(),usuario=ADMIN)
    svc.desactivar_producto(codigo='NEW1',usuario=ADMIN)
    svc.reactivar_producto(codigo='NEW1',usuario=ADMIN)
    assert [x[0] for x in calls]==[
        'catalogo','crear_producto','editar_producto',
        'desactivar_producto','reactivar_producto'
    ]
    assert calls[0][1]['incluir_inactivos'] is True
    with pytest.raises(PermissionError):
        svc.crear_producto(datos=nuevo(),usuario=OPERADOR)


def test_sql_y_edge_protegen_historial():
    root=Path(__file__).resolve().parents[2]
    sql=(root/'supabase/migrations/20261029_axia_almacen_gestion_productos.sql').read_text('utf8')
    ts=(root/'supabase/functions/axia-almacen/index.ts').read_text('utf8')
    assert 'SALDO_NO_CERO' in sql
    assert 'BEFORE INSERT ON public.axia_almacen_lab_movimientos' in sql
    assert 'DELETE FROM public.axia_almacen' not in sql
    assert 'axia_almacen_maestro_desactivar_producto' in ts
    for act in ['crear_producto','editar_producto','desactivar_producto','reactivar_producto']:
        assert act in ts
