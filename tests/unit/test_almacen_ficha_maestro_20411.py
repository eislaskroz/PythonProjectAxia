"""Regresiones de catálogo real. No se requieren conexión ni servicios externos."""
from pathlib import Path
from uuid import UUID
import sys
import types
import pytest
from services.almacen_service import validar_producto_maestro, AlmacenRemoto

ROOT=Path(__file__).resolve().parents[2]


def producto():
    return dict(producto='Tubo EMT 3/4', categoria_axia='Canalización',
                familia_axia='Tubería y conduit', departamento='CANALIZACIÓN',
                proveedor='Proveedor de prueba', codigo_proveedor='ABC-123',
                costo='45.550000', venta='60.50', p_mayoreo='52.30',
                minimo='2', maximo='30', unidad_inventario='Pieza',
                seguimiento_sugerido='Consumible', estado_clasificacion='Validado',
                posible_equivalencia='')


def test_acepta_campos_originales_y_no_requiere_codigo():
    v=validar_producto_maestro(producto())
    assert 'codigo' not in v
    assert v['p_mayoreo']=='52.300000'
    assert v['codigo_proveedor']=='ABC-123'
    assert v['categoria_axia']=='Canalización'


def test_impide_codigo_modificado_y_saldo_en_modificacion():
    datos=producto()
    datos['codigo']='TUB-CAN-00001'
    assert validar_producto_maestro(datos,codigo='TUB-CAN-00001')['codigo']=='TUB-CAN-00001'
    with pytest.raises(ValueError,match='no puede modificarse'):
        validar_producto_maestro(datos,codigo='TUB-CAN-99999')
    datos['saldo']='10000'
    assert 'saldo' not in validar_producto_maestro(datos)


def test_valida_precio_y_categoria():
    for key,value in [('costo','-1'),('p_mayoreo','NaN'),('maximo','1.0000001'),
                      ('categoria_axia',''),('familia_axia','')]:
        d=producto();d[key]=value
        with pytest.raises(ValueError):
            validar_producto_maestro(d)


def test_remoto_no_envia_codigo_e_id_reintento(monkeypatch):
    fake=types.ModuleType('supabase_config')
    fake.SUPABASE_URL='https://demo.supabase.co';fake.SUPABASE_KEY='anon-test'
    monkeypatch.setitem(sys.modules,'supabase_config',fake)
    svc=AlmacenRemoto();svc._usuario_id='10';svc.token='token'
    calls=[];svc._peticion=lambda name,payload=None,**k:calls.append((name,payload)) or {'codigo':'TUB-CAN-00051'}
    user={'id_usuario':10}
    data=producto();data['solicitud_id']='d516b214-e93e-48bf-bf95-b312b43fb983'
    assert svc.crear_producto(datos=data,usuario=user)['codigo']=='TUB-CAN-00051'
    assert calls[0][0]=='crear_producto'
    assert 'codigo' not in calls[0][1]['producto']
    assert calls[0][1]['producto']['solicitud_id']==data['solicitud_id']
    svc.editar_producto(codigo='TUB-CAN-00051',datos=data,usuario=user)
    assert calls[1][1]['producto']['codigo']=='TUB-CAN-00051'


def test_sql_y_edge_generan_folio_servidor_y_protegen_consecutivo():
    sql=(ROOT/'supabase/migrations/20261029_axia_almacen_alta_automatica_20411.sql').read_text()
    edge=(ROOT/'supabase/functions/axia-almacen/index.ts').read_text()
    view=(ROOT/'views/almacen_view.py').read_text()
    assert 'pg_advisory_xact_lock' in sql
    assert 'alta_solicitud_id' in sql
    assert 'GRANT EXECUTE ON FUNCTION public.axia_almacen_maestro_crear_producto(jsonb,uuid)' in sql
    assert "db.rpc('axia_almacen_maestro_crear_producto'" in edge
    assert "'Código AXIA'" in view
    assert 'Se asignará automáticamente al guardar' in view
    assert 'CTkScrollableFrame' in view
