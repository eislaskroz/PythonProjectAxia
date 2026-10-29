"""Cobertura de selector universal de Levantamientos 2.05.06."""
from pathlib import Path
from ui.catalogo_axia_inline import etiquetas_catalogo, etiqueta_producto, detalle_producto, normalizar
from services.levantamiento_catalogo_axia import referencia_axia, especificacion_catalogo_axia

ROOT=Path(__file__).resolve().parents[2]


def test_catalogo_completo_con_duplicados_no_pierde_referencias():
    filas=[{'codigo_axia':f'AXI-CAN-{i:05d}', 'producto':'Abrazadera' if i < 4 else f'Producto {i}',
            'categoria_axia':'Canalización', 'familia_axia':'Abrazaderas'} for i in range(1886)]
    etiquetas=etiquetas_catalogo(filas)
    assert len(etiquetas)==len(set(etiquetas))==1886
    assert all('AXI-CAN-' not in x for x in etiquetas)
    assert 'registro 4/4' in etiquetas[3]


def test_descripcion_es_lo_visible_pero_folio_interno_se_conserva():
    p={'codigo_axia':'TUB-CAN-00001','producto':'Tubo EMT 1/2"', 'categoria_axia':'Canalización',
       'familia_axia':'Tubería', 'departamento_origen':'ELECTRICO', 'unidad_inventario':'Pieza(s)',
       'saldo_actual':15, 'p_costo':35,'proveedor':'PRIVADO'}
    assert etiqueta_producto(p)=='Tubo EMT 1/2"'
    assert all(x in detalle_producto(p) for x in ('Canalización','Tubería','ELECTRICO','Pieza(s)','15'))
    assert 'PRIVADO' not in detalle_producto(p) and '35' not in detalle_producto(p)
    assert referencia_axia(p)['codigo_axia']=='TUB-CAN-00001'
    assert especificacion_catalogo_axia(p)=='1/2"'
    assert especificacion_catalogo_axia({'producto':'Caja de registro sin medida'})==''


def test_selector_permite_todos_y_no_filtra_ciento_veinte():
    fuente=(ROOT/'ui/catalogo_axia_inline.py').read_text(encoding='utf-8')
    view=(ROOT/'views/levantamiento_view.py').read_text(encoding='utf-8')
    assert 'encontrados[:120]' not in fuente
    assert 'self._combo.configure(values=encontrados)' in fuente
    assert 'entrada_especificacion_axia' in view
    assert 'columnspan=2' in view
    assert 'codigo_axia' in fuente  # Sólo búsqueda e identidad interna.
    assert 'No se realizó ningún movimiento de Almacén.' in view
    assert 'No se realizó ningún movimiento de Almacén.' not in fuente
