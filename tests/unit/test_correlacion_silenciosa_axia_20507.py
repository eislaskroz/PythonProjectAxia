"""Preservar el formulario original y relacionar artículos sin modificar inventario."""
from pathlib import Path
from services.correlacion_levantamientos_almacen import CorrelacionadorAxia

ROOT=Path(__file__).resolve().parents[2]

PRODUCTOS=[
 {'codigo_axia':'TUB-CAN-00063', 'producto':'TUBO PARED DELGADA DE 13MM',
  'categoria_axia':'Canalización','familia_axia':'Tubería y conduit'},
 {'codigo_axia':'ABR-CAN-00020', 'producto':'ABRAZADERA OMEGA 1/2'},
 {'codigo_axia':'TUB-CAN-00001','producto':'ABRAZADERA TIPO OMEGA PARA TUBO CONDUIT DE 13MM'},
 {'codigo_axia':'CAB-RED-00015','producto':'BOBINA 305M D/CABLE UTP CAT5E PE PARA EXTERIOR'},
 {'codigo_axia':'CAB-RED-00016','producto':'BOBINA 305M D/CABLE UTP CAT6 PE PARA EXTERIOR'},
 {'codigo_axia':'CAB-CAN-00100','producto':'PATCH CORD CAT6 2 METROS'},
 {'codigo_axia':'ABR-CAN-00001','producto':'ABRAZADERA DE CLIP 1'},
 {'codigo_axia':'CNL-CAN-00016','producto':'CANALETA 2X2 PLASTICA'},
 {'codigo_axia':'SWT-RED-00004','producto':'CISCO SYSTEMS SWITCH'},
 {'codigo_axia':'TUB-CAN-00087','producto':'TUBO PARED DELGADA DE 19MM'},
 {'codigo_axia':'TUB-CAN-00088','producto':'TUBO PARED GRUESA DE 19MM'},
]


def test_correlaciona_tubo_sin_pedir_codigo_al_tecnico():
    c=CorrelacionadorAxia(PRODUCTOS)
    r=c.canalizacion('Tubo','Pared delgada (EMT)','1/2" (13mm)')
    assert r['codigo_axia']=='TUB-CAN-00063'


def test_misma_categoria_pero_distinta_especificacion_no_da_falso_positivo():
    c=CorrelacionadorAxia(PRODUCTOS)
    assert not c.canalizacion('Tubo','Pared delgada (EMT)','2" (51mm)')
    assert not c.canalizacion('Cable','UTP Cat5e','14 AWG (Hasta 15A)')
    assert not c.canalizacion('Patch cord','Cat5e - 1 m','No aplica')


def test_reconoce_abrazadera_omega_y_no_se_confunde_con_tubo():
    c=CorrelacionadorAxia(PRODUCTOS)
    assert c.canalizacion('Abrazadera','Tipo Omega','1/2" (13mm)')['codigo_axia']=='ABR-CAN-00020'


def test_material_por_nombre_y_equipo_no_ambiguo():
    c=CorrelacionadorAxia(PRODUCTOS)
    assert c.material('ABRAZADERA DE CLIP 1')['codigo_axia']=='ABR-CAN-00001'
    assert c.equipo('Redes','CISCO SYSTEMS SWITCH')['codigo_axia']=='SWT-RED-00004'
    assert not c.equipo('Redes','SWITCH')  # Descripción genérica no basta.


def test_nombres_duplicados_no_tienen_match_inventado():
    datos=PRODUCTOS+[{'codigo_axia':'ABR-CAN-00200','producto':'ABRAZADERA DE CLIP 1'}]
    assert not CorrelacionadorAxia(datos).material('ABRAZADERA DE CLIP 1')


def test_interfaz_inicial_preservada_y_correlacion_sin_movimientos():
    view=(ROOT/'views/levantamiento_view.py').read_text(encoding='utf-8')
    assert '("Categoría", "Tipo", "Tamaño / calibre / especificación", "Cantidad", "Unidad", "Aproximado", "Acción")' in view
    assert '("Familia", "Subfamilia", "Cantidad", "Marca", "Modelo", "Características técnicas", "Acción")' in view
    assert '"➕ Agregar insumo del catálogo"' in view
    assert '"➕ Agregar otro material"' in view
    assert 'selector_producto_axia' not in view
    assert 'CorrelacionadorAxia()' in view
    assert 'form_body.after(300, cargar_referencias_almacen)' in view
    assert 'registrar_salida_ot(' not in view
