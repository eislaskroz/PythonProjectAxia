"""Pruebas de movimientos locales efímeros; no requieren Supabase."""
import uuid
from decimal import Decimal
import pytest
from services.almacen_service import AlmacenSimulador, cantidad_valida

CAT = [{'codigo':'TEST-01','producto':'Conector CAT6','existencia':'999',
        'departamento':'REDES','costo':'2.00'}]
ADMIN = {'id_usuario':1,'usuario':'admin','usu_tipo':1}
ALMACEN = {'id_usuario':8,'usuario':'almacen','usu_tipo':8}
OTRO = {'id_usuario':4,'usuario':'operador','usu_tipo':4}


def mov(service, tipo='ENTRADA', qty='2', *, who=ALMACEN, idem=None, **kw):
    return service.registrar(codigo='TEST-01',tipo=tipo,cantidad=qty,
                            motivo=kw.get('motivo','Recepción de prueba'),
                            referencia=kw.get('referencia','OT-100'),
                            destinatario=kw.get('destinatario','Técnico A'),
                            usuario=who,idempotencia=idem)


def test_saldos_no_son_existencias_eleventa():
    demo=AlmacenSimulador(CAT)
    assert demo.catalogo()[0]['saldo']=='0'
    assert demo.catalogo()[0]['saldo_exportado']=='999'


def test_entrada_salida_y_kardex():
    demo=AlmacenSimulador(CAT)
    entrada=mov(demo,qty='7.500')
    salida=mov(demo,'SALIDA','2.125')
    assert entrada['saldo_anterior']=='0'
    assert salida['saldo_nuevo']=='5.375'
    assert len(demo.kardex('TEST-01'))==2
    assert demo.catalogo()[0]['saldo']=='5.375'
    assert CAT[0]['existencia']=='999'


def test_salida_negativa_es_rechazada():
    demo=AlmacenSimulador(CAT)
    with pytest.raises(ValueError, match='insuficiente'):
        mov(demo,'SALIDA','1')
    assert len(demo.kardex())==0


def test_idempotencia_evita_doble_entrada():
    demo=AlmacenSimulador(CAT)
    ident=str(uuid.uuid4())
    primero=mov(demo,idem=ident)
    segundo=mov(demo,idem=ident)
    assert primero['id']==segundo['id']
    assert demo.catalogo()[0]['saldo']=='2'
    with pytest.raises(ValueError,match='distintos'):
        mov(demo,qty='3',idem=ident)


def test_permisos_y_validaciones():
    demo=AlmacenSimulador(CAT)
    with pytest.raises(PermissionError):mov(demo,who=OTRO)
    with pytest.raises(ValueError):mov(demo,qty='-2')
    with pytest.raises(ValueError):mov(demo,qty='0')
    with pytest.raises(ValueError):mov(demo,qty='1.2345')
    with pytest.raises(ValueError):mov(demo,'SALIDA','1',destinatario='')
    assert mov(demo,who=ADMIN)['responsable_id']=='1'
    assert cantidad_valida('2.125')==Decimal('2.125')


def test_catalogo_codigos_unicos():
    with pytest.raises(ValueError,match='duplicados'):
        AlmacenSimulador(CAT + CAT)
