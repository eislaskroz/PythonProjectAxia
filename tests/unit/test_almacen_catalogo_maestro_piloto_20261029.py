"""Catálogo Maestro AXIA: trazabilidad de todas las columnas y movimientos reales."""
from pathlib import Path
import pytest
from services.almacen_catalogo_maestro import CAMPOS_ORIGINALES,CAMPOS_ADICIONALES,ficha_producto_maestro
ROOT=Path(__file__).resolve().parents[2]

def test_conserva_las_once_columnas_orig_y_saldo_actual():
    assert len(CAMPOS_ORIGINALES)==11
    campos={k for k,_ in CAMPOS_ORIGINALES+CAMPOS_ADICIONALES}
    assert {'proveedor','codigo_proveedor','p_mayoreo','saldo_actual','activo','existencia_eleventa'} <= campos

def test_ficha_maestro_tiene_saldos_separados():
    ficha=ficha_producto_maestro({'codigo_axia':'TUB-CAN-00001','producto':'Tubo EMT',
      'saldo_actual':'8','existencia_eleventa':'10','proveedor':None})
    assert 'TUB-CAN-00001' in ficha and 'Saldo actual en Supabase: 8' in ficha
    assert 'Existencia (ELEVENTA): 10' in ficha
    assert '— (pendiente)' in ficha

def test_sql_reutiliza_tabla_1886_y_no_resetea_saldos():
    sql=(ROOT/'supabase/migrations/20261029_axia_almacen_catalogo_definitivo_20408.sql').read_text()
    assert 'RENAME TO axia_almacen_catalogo' in sql
    assert 'WHERE saldo_actual IS NULL' in sql
    assert 'axia_almacen_maestro_registrar_movimiento' in sql
    assert 'FOR UPDATE' in sql
    assert 'IDEMPOTENCIA_CON_DATOS_DISTINTOS' in sql
    assert 'axia_almacen_maestro_registrar_salida_ot' in sql
    assert 'REVOKE ALL ON FUNCTION' in sql
    assert 'TO service_role' in sql

def test_edge_no_usa_catalogos_paralelos_y_protege_credenciales():
    codigo=(ROOT/'supabase/functions/axia-almacen/index.ts').read_text()
    assert "const tabla = 'axia_almacen_catalogo'" in codigo
    assert 'catalogo_maestro_piloto' not in codigo
    assert 'axia_almacen_lab_productos' not in codigo
    assert 'axia_almacen_maestro_registrar_movimiento' in codigo
    assert 'axia_almacen_maestro_registrar_salida_ot' in codigo
    assert codigo.index('await verificarToken(')<codigo.index("if (accion === 'catalogo')")

def test_ui_usa_un_solo_catalogo_y_muestra_datos_completos():
    vista=(ROOT/'views/almacen_view.py').read_text()
    assert 'vista_maestro_habilitada = False' in vista
    assert 'CATÁLOGO ÚNICO AXIA' in vista
    assert "('saldo', 'Saldo actual'" in vista
    assert "('codigo_origen_eleventa', 'Código ELEVENTA'" in vista
