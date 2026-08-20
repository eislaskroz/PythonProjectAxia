from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def text(rel): return (ROOT/rel).read_text(encoding='utf-8')


def test_migracion_crea_tabla_y_folio_cot():
    s=text('migrations/20260820_cotizaciones_formales.sql')
    assert 'create table if not exists public.db_cotizaciones' in s.lower()
    assert 'generar_folio_cotizacion' in s
    assert "'COT-'" in s


def test_servicio_persiste_tabla_nueva_y_campos_comerciales():
    s=text('services/cotizaciones_service.py')
    assert 'TABLA_COTIZACIONES' in s
    for campo in ['proveedor','sku','precio_lista','costo','utilidad_pct','precio_venta','precio_unitario','importe','observaciones']:
        assert f'"{campo}"' in s


def test_ui_captura_condiciones_y_pdf():
    s=text('views/cotizaciones_view.py')
    for texto in ['Plan de Pagos','Vigencia de Cotización','Descuento %','IVA %','PDF Cotización','Guardar cotización']:
        assert texto in s


def test_pdf_es_horizontal_y_conserva_estructura():
    s=text('services/cotizacion_pdf.py')
    assert 'landscape, letter' in s
    for texto in ['No. Cotización','No. Levantamiento','Plan de Pagos','Vigencia de Cotización','Proveedor','P. Lista','Utilidad','P. Venta','P. Unitario','Observaciones']:
        assert texto in s
