"""Fase 1: Catálogo AXIA en LEV, sin tocar inventario."""
from pathlib import Path
from services.levantamiento_catalogo_axia import (
    referencia_axia, categoria_canalizacion_axia, unidad_levantamiento_axia,
    CatalogoAxiaLevantamientos,
)

ROOT = Path(__file__).resolve().parents[2]


def test_referencia_conserva_identidad_pero_no_costo_proveedor():
    producto = {'codigo_axia':'TUB-CAN-00019','producto':'TUBO EMT 3/4',
                'categoria_axia':'Canalización','familia_axia':'Tubo',
                'unidad_inventario':'Pieza(s)','p_costo':300,'proveedor':'INTERNO',
                'saldo_actual':80}
    data = referencia_axia(producto)
    assert data['codigo_axia'] == 'TUB-CAN-00019'
    assert data['producto_axia'] == 'TUBO EMT 3/4'
    assert not {'p_costo','proveedor','saldo_actual'} & data.keys()


def test_categoria_y_unidad_mantienen_conversion_historica():
    assert categoria_canalizacion_axia({'producto':'Tubo EMT 3/4'}) == 'Tubo'
    assert categoria_canalizacion_axia({'producto':'Canaleta blanca 20x12'}) == 'Canaleta'
    assert categoria_canalizacion_axia({'producto':'Patch cord 2 m'}) == 'Patch cord'
    assert unidad_levantamiento_axia({'unidad_inventario':'rollo'}) == 'Rollo(s)'
    assert unidad_levantamiento_axia({'unidad_inventario':''}) == 'Pieza(s)'


def test_solo_acciones_de_lectura_en_cliente(monkeypatch):
    servicio = CatalogoAxiaLevantamientos.__new__(CatalogoAxiaLevantamientos)
    servicio.token = None
    servicio._usuario_id = None
    llamadas = []
    monkeypatch.setattr(servicio, '_peticion', lambda accion, datos=None, **kw: llamadas.append((accion,datos,kw)) or (
        {'id_usuario':'24','token':'TOKEN'} if accion == 'login_levantamientos' else []))
    servicio.iniciar_lectura('tecnico','pwd',24)
    servicio.buscar('tubo')
    assert [x[0] for x in llamadas] == ['login_levantamientos','catalogo_levantamientos']
    assert llamadas[1][1]['buscar'] == 'tubo'


def test_no_permiso_escritura_en_sesion_lectura():
    edge = (ROOT/'supabase/functions/axia-almacen/index.ts').read_text(encoding='utf-8')
    assert "session.alcance === 'levantamientos_lectura' && accion !== 'catalogo_levantamientos'" in edge
    assert "const roles = alcance === 'levantamientos_lectura' ? [1,2,3,4,5,6] : [1,8]" in edge
    assert "select('codigo_axia,producto,categoria_axia,familia_axia,departamento_origen,unidad_inventario,saldo_actual')" in edge
    assert edge.index("session.alcance === 'levantamientos_lectura'") < edge.index("if (accion === 'catalogo')")


def test_tres_catalogos_guardan_codigo_y_siguen_teniendo_captura_manual():
    view = (ROOT/'views/levantamiento_view.py').read_text(encoding='utf-8')
    assert 'Buscar producto AXIA' in view
    assert 'Buscar equipo AXIA' in view
    assert 'Buscar material AXIA' in view
    assert view.count('**item.get("referencia_axia", {})') >= 3
    assert 'agregar_material_miscelaneo(None)' in view
    assert 'agregar_equipo_catalogo' in view
    assert '"canalizacion_materiales"' in view


def test_no_se_invoca_registrar_movimientos_desde_levantamientos():
    selector = (ROOT/'ui/selector_catalogo_axia.py').read_text(encoding='utf-8')
    assert 'registrar_salida_ot(' not in selector
    assert 'registrar(' not in selector
