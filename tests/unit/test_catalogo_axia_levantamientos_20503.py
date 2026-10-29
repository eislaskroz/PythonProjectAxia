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


def test_lev_cat_maestro_directo_tres_secciones_sin_botones_viejos():
    view = (ROOT/'views/levantamiento_view.py').read_text(encoding='utf-8')
    login = (ROOT/'login.py').read_text(encoding='utf-8')
    assert 'Buscar producto AXIA' not in view
    assert 'Buscar equipo AXIA' not in view
    assert 'Buscar material AXIA' not in view
    assert view.count('selector_producto_axia(') >= 4
    assert 'catalogo_axia_lectura.todos' in view
    assert 'establecer_sesion_catalogo(resultado.get("token_catalogo")' in login
    assert view.count('**item.get("referencia_axia", {})') >= 3
    assert '"canalizacion_materiales"' in view


def test_la_sesion_lev_se_establece_con_login_normal_y_consulta_paginada(monkeypatch):
    import services.levantamiento_catalogo_axia as modulo
    modulo.establecer_sesion_catalogo('token-lectura', 24)
    from services.almacen_service import AlmacenRemoto
    monkeypatch.setattr(AlmacenRemoto, '__init__', lambda self: setattr(self, 'token', None))
    servicio = modulo.CatalogoAxiaLevantamientos(24)
    assert servicio.token == 'token-lectura'
    llamadas = []
    def fake_peticion(accion, datos):
        llamadas.append((accion,datos))
        return [{'codigo_axia': str(i)} for i in range(500)] if len(llamadas)==1 else [{'codigo_axia':'FIN'}]
    monkeypatch.setattr(servicio, '_peticion', fake_peticion)
    datos = servicio.todos()
    assert len(datos) == 501
    assert [args['pagina'] for _,args in llamadas] == [1,2]
    assert all(accion == 'catalogo_levantamientos' for accion,_ in llamadas)
    assert modulo.CatalogoAxiaLevantamientos(99).token is None
    modulo.establecer_sesion_catalogo(None, None)


def test_consulta_tiene_paginas_y_sesion_extendida_solo_para_lectura():
    edge = (ROOT/'supabase/functions/axia-almacen/index.ts').read_text(encoding='utf-8')
    assert "alcance === 'levantamientos_lectura' ? 12 * 3600 : 900" in edge
    assert "accion !== 'catalogo_levantamientos'" in edge
    assert ".range((pagina-1)*limite, pagina*limite - 1)" in edge


def test_no_se_invoca_registrar_movimientos_desde_levantamientos():
    selector = (ROOT/'ui/selector_catalogo_axia.py').read_text(encoding='utf-8')
    assert 'registrar_salida_ot(' not in selector
    assert 'registrar(' not in selector
