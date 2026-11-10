"""Regresiones de campos visibles y flujo comercial DG."""
from pathlib import Path
from pypdf import PdfReader
from services.cotizacion_pdf import generar_pdf_cotizacion



def test_pdf_campos_filtrados(tmp_path):
    data = {
        'cot_folio':'COT-TEST-01', 'cot_cliente':'CLIENTE MUESTRA',
        'cot_asunto':'TITULO ALIMENTACION ELECTRICA', 'cot_plan_pagos':'PPD',
        'cot_partidas_json':[{'lote':'1','unidad_tipo':'Servicio','cantidad':'1',
                              'concepto':'INSTALACION TEST', 'importe':600, 'precio_unitario':600}],
        'cot_subtotal':600,'cot_total':696,
    }
    ruta = generar_pdf_cotizacion(data, tmp_path/'filtrado.pdf', abrir=False,
                                  campos_visibles={'folio','asunto','plan_pagos','partidas','concepto','importe','totales','total'})
    texto = '\n'.join(p.extract_text() or '' for p in PdfReader(str(ruta)).pages)
    assert 'TITULO ALIMENTACION ELECTRICA' in texto
    assert 'PPD' in texto
    assert 'INSTALACION TEST' in texto
    assert 'CLIENTE MUESTRA' not in texto
    assert 'PROVEEDOR' not in texto
    assert 'COT-TEST-01' in texto


def test_pdf_sin_ningun_campo(tmp_path):
    ruta = generar_pdf_cotizacion({'cot_folio':'COT-TEST-02'},tmp_path/'vacio.pdf',abrir=False,campos_visibles=set())
    assert ruta.exists() and ruta.stat().st_size>100


def test_campos_pdf_granulares():
    codigo = (Path(__file__).resolve().parents[2]/'views/cotizacion_pdf_opciones.py').read_text('utf8')
    for key in ('precio_unitario','cliente','rfc','asunto','plan_pagos','total'):
        assert f'"{key}"' in codigo


def test_cotizaciones_separadas_por_autorizacion():
    root = Path(__file__).resolve().parents[2]
    service = (root/'services/cotizaciones_service.py').read_text('utf8')
    assert 'ESTATUS_PENDIENTE_DG = "PENDIENTE DG"' in service
    assert '"cot_estatus": ESTATUS_PENDIENTE_DG' in service
    assert '.eq("cot_estatus", ESTATUS_PENDIENTE_DG)' in service
    assert '"cot_estatus": ESTATUS_EN_COMPRA' in service
    assert '.eq("cot_estatus", ESTATUS_EN_COMPRA)' in service
