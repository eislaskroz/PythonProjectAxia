import importlib
import sys
import types


def _servicio(monkeypatch):
    def registrar_modulo(nombre, **atributos):
        modulo = types.ModuleType(nombre)
        for clave, valor in atributos.items():
            setattr(modulo, clave, valor)
        monkeypatch.setitem(sys.modules, nombre, modulo)

    registrar_modulo('supabase_config', supabase=None)
    registrar_modulo('services.movimientos_service', registrar_movimiento_seguro=lambda **kw: None)
    registrar_modulo('services.folios_service', solicitar_folio_cotizacion=lambda: 'COT-PRUEBA')
    registrar_modulo('services.sucursales_service', obtener_sucursal_por_id=lambda _id: {})
    registrar_modulo('services.usuarios_service', obtener_usuario_por_id=lambda _id: {})
    sys.modules.pop('services.cotizaciones_service', None)
    return importlib.import_module('services.cotizaciones_service')


def _registro_lev70():
    return {
        'lev_folio': 'LEV-00070',
        'lev_tipo': 9,
        'lev_detalle_tecnico_json': {
            'civil_misc_0_material': 'Boquilla sin arena marca juntacrest',
            'civil_misc_0_quantity': '15',
            'civil_misc_0_unit': 'Kilogramo(s)',
            'civil_misc_0_specification': 'blanca',
            'civil_misc_1_material': 'Silicón / sellador',
            'civil_misc_1_quantity': '4',
            'civil_misc_1_unit': 'Pieza(s)',
            'civil_misc_1_specification': 'poliuretano negro',
        },
    }


def test_lev70_materiales_legados_se_cotizan(monkeypatch):
    servicio = _servicio(monkeypatch)
    partidas = servicio.construir_partidas_comerciales(_registro_lev70())
    assert len(partidas) == 3
    assert partidas[0]['cantidad'] == '15'
    assert partidas[0]['unidad_tipo'] == 'Kilogramo(s)'
    assert 'Boquilla sin arena marca juntacrest' in partidas[0]['concepto']
    assert partidas[1]['cantidad'] == '4'
    assert partidas[1]['unidad_tipo'] == 'Pieza(s)'
    assert 'Silicón / sellador' in partidas[1]['concepto']


def test_cotizacion_guardada_no_pierde_precios(monkeypatch):
    servicio = _servicio(monkeypatch)
    guardada = [{'concepto': 'Boquilla cotizada', 'cantidad': '15', 'precio_lista': 900, 'unidad_tipo': 'Kilogramo(s)'}]
    partes = servicio.construir_partidas_comerciales(_registro_lev70(), {'cot_partidas_json': guardada})
    assert partes == guardada


def test_cotizacion_con_solo_servicio_recupera_materiales(monkeypatch):
    servicio = _servicio(monkeypatch)
    servicio_previo = {'concepto': 'Servicio de instalación', 'cantidad': '1', 'unidad_tipo': 'Servicio', 'importe': '250'}
    partes = servicio.construir_partidas_comerciales(_registro_lev70(), {'cot_partidas_json': [servicio_previo]})
    assert len(partes) == 3
    assert partes[-1] == servicio_previo
    assert partes[0]['cantidad'] == '15'


def test_registro_moderno_conserva_partidas(monkeypatch):
    servicio = _servicio(monkeypatch)
    reg = {'lev_folio':'LEV-00070','lev_detalle_tecnico_json':{'materiales_miscelaneos':[{'material':'Boquilla','cantidad':'15','unidad':'Kilogramo(s)','especificacion':'blanca'}]}}
    partes = servicio.partidas_cotizables(reg)
    assert len(partes) == 1
    assert partes[0]['cantidad'] == '15'
