"""Regresiones del formulario de cotización y del PDF entregable al cliente."""
from pathlib import Path

from services.cotizacion_partidas import es_lote_servicio, importes_servicio
from services.cotizacion_pdf import generar_pdf_cotizacion


def test_identificacion_de_servicio_solo_ultimo_lote():
    item = {"unidad_tipo": "Servicio", "concepto": "Servicio de Control de Accesos"}
    assert es_lote_servicio(item, 5, 6)
    assert not es_lote_servicio(item, 4, 6)
    assert not es_lote_servicio({"unidad_tipo":"Pieza(s)","concepto":"Canaleta"}, 5, 6)


def test_importe_manual_no_depende_de_utilidad():
    importe, precio = importes_servicio({"importe": "$6,500.00", "cantidad": "1", "utilidad_pct": "30"})
    assert importe == 6500
    assert precio == 6500


def test_pdf_de_cliente_sin_datos_internos(tmp_path):
    from pypdf import PdfReader
    data = {
        "cot_folio": "COT-PRUEBA",
        "cot_fecha": "20/10/2026", "cot_cliente": "Cliente de prueba",
        "cot_partidas_json": [
            {"lote":"1", "unidad_tipo":"Pieza(s)", "cantidad":"2", "proveedor":"HOME DEPOT PROVEEDOR INTERNO",
             "modelo":"Modelo", "sku":"SKU123", "marca":"Marca", "concepto":"Equipo de prueba",
             "precio_lista":99991, "costo":99992, "utilidad_pct":739,
             "precio_venta":99993, "precio_unitario":1500, "importe":3000,
             "observaciones":"Instalación"},
            {"lote":"2", "unidad_tipo":"Servicio", "cantidad":"1", "proveedor":"AXIA",
             "modelo":"", "sku":"SVC-01", "marca":"AXIA", "concepto":"Servicio de instalación",
             "precio_lista":99991, "costo":99992, "utilidad_pct":739,
             "precio_venta":99993, "precio_unitario":6500, "importe":6500,
             "observaciones":"Mano de obra"},
        ],
        "cot_subtotal":9500, "cot_descuento_pct":0, "cot_subtotal_descuento":9500,
        "cot_iva_pct":16, "cot_iva":1520, "cot_total":11020,
    }
    ruta = generar_pdf_cotizacion(data, tmp_path / 'cot_cliente.pdf', abrir=False)
    assert ruta.exists() and ruta.stat().st_size > 0
    text = '\n'.join(p.extract_text() or '' for p in PdfReader(str(ruta)).pages)
    for campo in ('P. LISTA', 'COSTO', 'UTILIDAD', 'P. VENTA', 'PROVEEDOR'):
        assert campo not in text
    for campo in ('P. UNIT.', 'IMPORTE', 'Servicio de instalación', '$6,500.00'):
        assert campo in text
    for dato_interno in ('99991', '99992', '99993', '739%', 'HOME DEPOT PROVEEDOR INTERNO'):
        assert dato_interno not in text


def test_tres_bandejas_y_resumen_compacto():
    vista = (Path(__file__).resolve().parents[2] / 'views' / 'cotizaciones_view.py').read_text(encoding='utf-8')
    assert 'obtener_cotizaciones_en_compra' in vista
    assert 'Cotizaciones Autorizadas' in vista
    assert 'Cotizaciones Realizadas' in vista
    assert 'Levantamientos Preautorizados' in vista
    assert 'es_lote_servicio(item, i, len(partidas))' in vista


def test_guardar_lote_servicio_directo_sin_margen(monkeypatch):
    import importlib
    import sys
    import types
    # La prueba no debe conectarse a Supabase ni necesitar credenciales reales.
    def modulo(nombre, **atributos):
        m = types.ModuleType(nombre)
        for clave, valor in atributos.items():
            setattr(m, clave, valor)
        monkeypatch.setitem(sys.modules, nombre, m)
    modulo('supabase_config', supabase=None)
    modulo('services.movimientos_service', registrar_movimiento_seguro=lambda **kw: None)
    modulo('services.folios_service', solicitar_folio_cotizacion=lambda: 'COT-TEST')
    modulo('services.sucursales_service', obtener_sucursal_por_id=lambda _id: {})
    modulo('services.usuarios_service', obtener_usuario_por_id=lambda _id: {})
    sys.modules.pop('services.cotizaciones_service', None)
    svc = importlib.import_module('services.cotizaciones_service')

    class Respuesta:
        def __init__(self, data): self.data = data

    class Tabla:
        def insert(self, payload):
            self.payload = payload
            return self
        def execute(self):
            return Respuesta([self.payload])

    class BD:
        def table(self, nombre):
            assert nombre == svc.TABLA_COTIZACIONES
            return Tabla()

    monkeypatch.setattr(svc, 'supabase', BD())
    monkeypatch.setattr(svc, 'solicitar_folio_cotizacion', lambda: 'COT-TEST')
    monkeypatch.setattr(svc, 'registrar_movimiento_seguro', lambda **kwargs: None)
    datos = {
        'id_levantamiento': 1, 'lev_folio': 'LEV-TEST', 'cot_cliente': 'Cliente',
        'cot_contacto': 'Contacto', 'cot_sucursal': 'Sucursal', 'cot_asunto': 'Asunto',
        'cot_esi': 'Vendedora', 'cot_esi_correo': 'ventas@ejemplo.com',
        'cot_esi_telefono': '1234567890', 'cot_jefe_operaciones': 'Operaciones',
        'cot_supervisor': 'Supervisor', 'cot_dias': '1', 'cot_personas': '2',
        'cot_plan_pagos': 'PUE', 'cot_vigencia': '15', 'cot_descuento_pct': '0',
        'cot_iva_pct': '16',
    }
    partes = [
        {'unidad_tipo':'Pieza(s)', 'cantidad':'2', 'proveedor':'SYSCOM', 'modelo':'M',
         'sku':'SKU', 'marca':'Marca', 'concepto':'Equipo', 'precio_lista':'1500',
         'utilidad_pct':'30', 'importe':'3900'},
        {'unidad_tipo':'Servicio', 'cantidad':'1', 'proveedor':'', 'modelo':'',
         'sku':'SVC-1', 'marca':'', 'concepto':'Servicio de instalación',
         'precio_lista':'5000', 'utilidad_pct':'30', 'importe':'6500',
         'observaciones':'Mano de obra'},
    ]
    guardada = svc.guardar_cotizacion_comercial(datos, partes, 'Ventas')
    p1, p2 = guardada['cot_partidas_json']
    assert p1['costo'] == 450 and p1['importe'] == 3900
    assert p2['importe'] == 6500 and p2['precio_unitario'] == 6500
    assert p2['costo'] == 0 and p2['utilidad_pct'] == 0
    assert guardada['cot_subtotal'] == 10400
    assert guardada['cot_total'] == 12064
