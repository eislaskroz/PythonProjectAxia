"""OT: lote atómico, reintentos y seguridad para Almacén (sin Supabase)."""
from decimal import Decimal
from pathlib import Path
import pytest

from services.almacen_service import AlmacenSimulador
from services.almacen_entregas_ot import validar_entrega_ot, preparar_sugerencias_ot

ROOT=Path(__file__).resolve().parents[2]
ADMIN={'id_usuario':1,'usu_tipo':1,'usuario':'almacen'}
PRODUCTOS=[{'codigo':'C-01','producto':'Conector','activo':True},
           {'codigo':'T-02','producto':'Tubo','activo':True},
           {'codigo':'X-03','producto':'Desactivado','activo':False}]


def movimientos(svc):
    return svc.kardex()


def test_ot_entrega_multiple_atomica_con_idempotencia():
    svc=AlmacenSimulador(PRODUCTOS)
    for codigo in ('C-01','T-02'):
        svc.registrar(codigo=codigo,tipo='ENTRADA',cantidad='10',motivo='Recepción',
                     referencia='',destinatario='',usuario=ADMIN)
    key='7b5bf299-a695-46bf-bf5b-a89d1f6ea228'
    partes=[{'codigo':'C-01','cantidad':'2.500'}, {'codigo':'T-02','cantidad':'3'}]
    a=svc.registrar_salida_ot(folio='OT-00010',partidas=partes,destinatario='Técnico',
                             motivo='Entrega de OT',usuario=ADMIN,idempotencia=key)
    assert a['cantidad_partidas']==2
    assert [p['saldo'] for p in svc.catalogo() if p['codigo'] in ('C-01','T-02')]==['7.5','7']
    b=svc.registrar_salida_ot(folio='OT-00010',partidas=partes,destinatario='Técnico',
                             motivo='Entrega de OT',usuario=ADMIN,idempotencia=key)
    assert b['repetido'] is True
    assert len(movimientos(svc))==4
    with pytest.raises(ValueError,match='diferentes'):
        svc.registrar_salida_ot(folio='OT-00010',partidas=[{'codigo':'T-02','cantidad':1}],
                                destinatario='Técnico',motivo='Entrega de OT',
                                usuario=ADMIN,idempotencia=key)


def test_ot_entrega_fallida_no_descontar_ni_un_articulo():
    svc=AlmacenSimulador(PRODUCTOS)
    svc.registrar(codigo='C-01',tipo='ENTRADA',cantidad='10',motivo='Entrada',
                 referencia='',destinatario='',usuario=ADMIN)
    with pytest.raises(ValueError,match='insuficiente'):
        svc.registrar_salida_ot(folio='OT-00010',partidas=[{'codigo':'C-01','cantidad':'2'},
             {'codigo':'T-02','cantidad':'1'}],destinatario='Almacén',
             motivo='Entrega',usuario=ADMIN)
    assert next(p for p in svc.catalogo() if p['codigo']=='C-01')['saldo']=='10'
    assert len(movimientos(svc))==1


def test_ot_consolida_misma_clave_y_bloquea_invalidos():
    req=validar_entrega_ot('ot-00001',[{'codigo':'C-01','cantidad':'1.3'},
                   {'codigo':'C-01','cantidad':'0.7'}],'Técnico','Entrega')
    assert req['folio']=='OT-00001'
    assert req['partidas']==[{'codigo':'C-01','cantidad':'2'}]
    with pytest.raises(ValueError):
        validar_entrega_ot('OT-1',[{'codigo':'C-01','cantidad':'-1'}],'T','M')
    with pytest.raises(ValueError):
        validar_entrega_ot('OT-1',[{'codigo':'C-01','cantidad':'1'}],'','M')


def test_sugerencias_exigen_sku_exacto_y_omiten_servicio():
    data={'partidas':[{'concepto':'Conector','cantidad':'2','sku':'C-01'},
         {'concepto':'Red UTP','cantidad':1,'sku':''},
         {'concepto':'Servicio','unidad':'Servicio','cantidad':1}]}
    ok, pendiente=preparar_sugerencias_ot(data,PRODUCTOS)
    assert len(ok)==1 and ok[0]['codigo']=='C-01'
    assert len(pendiente)==1 and pendiente[0]['concepto']=='Red UTP'


def test_rpc_ot_no_da_acceso_publico_y_respeta_produccion():
    sql=(ROOT/'supabase/migrations/20261029_axia_almacen_entregas_ot.sql').read_text()
    edge=(ROOT/'supabase/functions/axia-almacen/index.ts').read_text()
    assert 'FOR UPDATE' in sql
    assert 'ON CONFLICT (idempotencia) DO NOTHING' in sql
    assert 'REVOKE ALL ON FUNCTION' in sql
    assert 'TO service_role' in sql
    assert 'OT_NO_ENCONTRADA' in sql
    assert 'catalogo_autorizado = true AND movimientos_habilitados = true' in sql
    assert 'axia_almacen_lab_registrar_salida_ot' in sql
    assert 'salida_ot' in edge and 'consultar_ot' in edge
    vista=(ROOT/'views/almacen_view.py').read_text()
    assert "tabs.add('Altas/Bajas/Modificaciones')" in vista
    assert 'SIMULADOR LOCAL: saldos' not in vista
    assert "texto='AXIA ALMACÉN" not in vista
    assert 'AXIA  /  Panel  /  Vista actual' not in (ROOT/'app.py').read_text()


def test_kardex_paginado_y_filtrado_por_ot():
    svc=AlmacenSimulador(PRODUCTOS)
    for numero in range(3):
        svc.registrar(codigo='C-01',tipo='ENTRADA',cantidad='1',motivo='Entrada',
                     referencia=f'OT-{numero}',destinatario='',usuario=ADMIN)
    assert len(svc.kardex(pagina=1,limite=2))==2
    assert len(svc.kardex(pagina=2,limite=2))==1
    assert svc.kardex('OT-1')[0]['referencia']=='OT-1'


def test_remoto_envia_ot_a_edge_protegida(monkeypatch):
    import sys, types
    from services.almacen_service import AlmacenRemoto
    fake=types.ModuleType('supabase_config')
    fake.SUPABASE_URL='https://demo.supabase.co'
    fake.SUPABASE_KEY='anon-demo'
    monkeypatch.setitem(sys.modules,'supabase_config',fake)
    svc=AlmacenRemoto(laboratorio=True)
    svc._usuario_id='1'
    svc.token='demo'
    solicitudes=[]
    svc._peticion=lambda a,d=None,**kwargs: solicitudes.append((a,d)) or {'folio':'OT-1'}
    assert svc.consultar_ot('ot-1',ADMIN)['folio']=='OT-1'
    svc.registrar_salida_ot(folio='OT-1',partidas=[{'codigo':'C-01','cantidad':'1'}],
                           destinatario='Operador',motivo='Entrega',usuario=ADMIN)
    assert [x[0] for x in solicitudes]==['consultar_ot_lab','salida_ot_lab']
    assert solicitudes[-1][1]['partidas']==[{'codigo':'C-01','cantidad':'1'}]
