"""La reimpresión histórica no ejecuta operaciones de inventario."""
from pathlib import Path
import fitz
import pytest

from services.almacen_reimpresion import generar_comprobante_historico
from services.almacen_service import AlmacenSimulador, AlmacenRemoto

ADMIN = {'id_usuario':1, 'usu_tipo':1, 'usuario':'almacen'}
PRODUCTOS = [{'codigo':'ABR-CAN-00001', 'producto':'Abrazadera galvanizada', 'activo':True},
             {'codigo':'CAB-RED-00001', 'producto':'Cable CAT6 azul', 'activo':True}]


def test_entrada_historia_imprime_etiqueta_sin_mutar(tmp_path):
    svc=AlmacenSimulador(PRODUCTOS)
    mov=svc.registrar(codigo='ABR-CAN-00001',tipo='ENTRADA',cantidad='8.5',
        motivo='Compra',referencia='FAC-42',destinatario='Proveedor',usuario=ADMIN)
    antes=svc.catalogo()
    detalle=svc.comprobante_kardex(mov['id'])
    doc=fitz.open(generar_comprobante_historico(detalle,ruta=tmp_path/'etiqueta.pdf'))
    assert len(doc)==1
    texto=doc[0].get_text()
    assert 'ABR-CAN-00001' in texto and '8.5' in texto and 'FAC-42' in texto
    assert len(doc[0].get_drawings())>20
    assert svc.catalogo()==antes and len(svc.kardex())==1


def test_salida_individual_regenera_ticket_sin_cambiar_kardex(tmp_path):
    svc=AlmacenSimulador(PRODUCTOS)
    svc.registrar(codigo='ABR-CAN-00001',tipo='ENTRADA',cantidad='12',
        motivo='Compra',referencia='',destinatario='Proveedor',usuario=ADMIN)
    mov=svc.registrar(codigo='ABR-CAN-00001',tipo='SALIDA',cantidad='2',
        motivo='Instalación',referencia='OT-00015',destinatario='Técnico',usuario=ADMIN)
    saldo=svc.catalogo()[0]['saldo']
    doc=fitz.open(generar_comprobante_historico(svc.comprobante_kardex(mov['id']),
                                                 ruta=tmp_path/'ticket.pdf'))
    texto=' '.join(p.get_text() for p in doc)
    for v in ('ABR-CAN-00001','OT-00015','Técnico','Cantidad entregada: 2'):
        assert v in texto
    assert not any(s in texto for s in ('P. costo','Utilidad','P. lista'))
    assert svc.catalogo()[0]['saldo']==saldo
    assert len(svc.kardex())==2


def test_dos_entregas_misma_ot_no_se_mezclan(tmp_path):
    svc=AlmacenSimulador(PRODUCTOS)
    for p in PRODUCTOS:
        svc.registrar(codigo=p['codigo'],tipo='ENTRADA',cantidad='10',motivo='Compra',
                     referencia='',destinatario='Proveedor',usuario=ADMIN)
    first=svc.registrar_salida_ot(folio='OT-00001',partidas=[
      {'codigo':'ABR-CAN-00001','cantidad':2}, {'codigo':'CAB-RED-00001','cantidad':3}],
      destinatario='Técnico A',motivo='Primera entrega',usuario=ADMIN)
    second=svc.registrar_salida_ot(folio='OT-00001',partidas=[
      {'codigo':'ABR-CAN-00001','cantidad':1}],
      destinatario='Técnico B',motivo='Segunda entrega',usuario=ADMIN)
    detalle=svc.comprobante_kardex(first['movimientos'][0]['id'])
    assert len(detalle['movimientos'])==2
    assert detalle['destinatario']=='Técnico A'
    doc=fitz.open(generar_comprobante_historico(detalle,ruta=tmp_path/'ot.pdf'))
    texto=' '.join(p.get_text() for p in doc)
    assert 'ARTICULOS: 2' in texto and 'Técnico A' in texto
    assert 'Técnico B' not in texto
    otro=svc.comprobante_kardex(second['movimientos'][0]['id'])
    assert len(otro['movimientos'])==1 and otro['destinatario']=='Técnico B'


def test_se_rechaza_detalle_incompleto_y_entrada_con_varias_partidas():
    with pytest.raises(ValueError): generar_comprobante_historico({'tipo':'SALIDA','movimientos':[]})
    with pytest.raises(ValueError): generar_comprobante_historico({'tipo':'ENTRADA','movimientos':[
       {'codigo':'X','cantidad':1},{'codigo':'Y','cantidad':1}]})


def test_reimpresion_remota_es_solo_lectura(monkeypatch):
    import sys, types
    fake=types.ModuleType('supabase_config')
    fake.SUPABASE_URL='https://demo.supabase.co'
    fake.SUPABASE_KEY='anon-demo'
    monkeypatch.setitem(sys.modules,'supabase_config',fake)
    svc=AlmacenRemoto()
    sent=[]
    svc._peticion=lambda accion,data=None: sent.append((accion,data)) or {'tipo':'ENTRADA'}
    uid='a5a4d454-8899-4532-acad-e4ca2ed5b4ed'
    assert svc.comprobante_kardex(uid)['tipo']=='ENTRADA'
    assert sent==[('comprobante_kardex',{'movimiento_id':uid})]
    with pytest.raises(ValueError):svc.comprobante_kardex('NO-UUID')


def test_edge_reconstruye_ot_por_ids_no_por_folio():
    root=Path(__file__).resolve().parents[2]
    edge=(root/'supabase/functions/axia-almacen/index.ts').read_text(encoding='utf-8')
    block=edge.split("if (accion === 'comprobante_kardex')",1)[1].split("if (accion === 'consultar_ot')",1)[0]
    assert ".contains('resultado',{movimientos:[{id:mov.id}]})" in block
    assert ".in('id',ids)" in block
    assert not any(pattern in block for pattern in (".insert(",".update(",".delete(","db.rpc("))
    assert "movimientos:movimientos.map" in block
