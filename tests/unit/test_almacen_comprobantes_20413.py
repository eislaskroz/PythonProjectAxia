"""Pruebas de etiquetas y tickets posteriores al guardado de Almacén."""
from decimal import Decimal
import fitz
import pytest
from services.almacen_comprobantes import generar_etiqueta_entrada, generar_ticket_salida


def test_etiqueta_code128_y_datos(tmp_path):
    pdf = generar_etiqueta_entrada(
        codigo='ABR-CAN-00001', producto='Abrazadera galvanizada 1/2',
        cantidad=Decimal('12.500'), referencia='FAC-24',
        fecha='2026-10-29T18:14:16Z', ruta=tmp_path/'etiqueta.pdf')
    doc = fitz.open(pdf)
    assert len(doc) == 1
    assert 99 < doc[0].rect.width / 2.834645669 < 101
    assert 59 < doc[0].rect.height / 2.834645669 < 61
    texto = doc[0].get_text()
    assert 'ABR-CAN-00001' in texto
    assert '12.5' in texto
    assert '29/10/2026 12:14:16' in texto
    assert len(doc[0].get_drawings()) > 20  # barras de Code128 reales


def test_etiqueta_rechaza_codigo_no_imprimible(tmp_path):
    with pytest.raises(ValueError):
        generar_etiqueta_entrada(codigo='ABC\nDEF', producto='Producto', cantidad=1, ruta=tmp_path/'malo.pdf')


def test_ticket_salida_sin_precios(tmp_path):
    pdf = generar_ticket_salida(
        partidas=[{'codigo':'TUB-CAN-00001','producto':'Tubo galvanizado','cantidad':'2'},
                  {'codigo':'RTR-RED-00002','producto':'Router empresarial','cantidad':'1'}],
        destinatario='Encargado de red', motivo='Instalación',
        referencia='OT-00024', responsable='Almacenista',
        identificador='f7042e02-e9bb-44ea-b102-64b904',
        fecha='2026-10-29T18:14:16Z', ruta=tmp_path/'ticket.pdf')
    doc = fitz.open(pdf)
    assert len(doc) == 1
    assert 79 < doc[0].rect.width / 2.834645669 < 81
    assert doc[0].rect.height < 650  # ticket sin márgenes enormes
    contenido = ''.join(p.get_text() for p in doc)
    for x in ('TUB-CAN-00001', 'RTR-RED-00002', 'OT-00024', 'Encargado de red',
              '29/10/2026 12:14:16', 'Cantidad entregada: 2', 'No es comprobante fiscal'):
        assert x in contenido
    assert not any(x in contenido for x in ('Precio costo','Utilidad', 'P. Lista'))


def test_ticket_ot_largo_se_completo(tmp_path):
    partidas = [{'codigo':f'CAB-RED-{i:05d}',
                 'producto':f'Cable estructurado CAT6 - lote {i} ' + 'material ' * 5,
                 'cantidad':'1.250'} for i in range(40)]
    pdf = generar_ticket_salida(partidas=partidas, destinatario='Area técnica',
                                motivo='Entrega por OT', referencia='OT-00100',
                                ruta=tmp_path/'largo.pdf')
    doc = fitz.open(pdf)
    contenido = ''.join(p.get_text() for p in doc)
    assert 'CAB-RED-00000' in contenido
    assert 'CAB-RED-00039' in contenido
    assert 'ARTICULOS: 40' in contenido
    assert len(doc) >= 1  # El rollo puede paginarse con entregas extensas


def test_no_se_incluye_acceso_a_supabase():
    import inspect
    import services.almacen_comprobantes as componente
    fuente = inspect.getsource(componente)
    assert 'supabase.table(' not in fuente
    assert 'registrar_salida(' not in fuente
    assert 'registrar_entrada(' not in fuente
