"""Regresión: las tablas deben respetar los anchos y el scroll horizontal."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from ui.table_columns import read_preferences, valid_width, write_preferences, TableColumnManager


def test_anchos_guardan_solo_preferencias_visual():
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'AXIA'/'preferencias_tablas.json'
        assert write_preferences('almacen_catalogo', {'codigo': 210, 'producto': 410},path)
        assert write_preferences('usuarios_catalogo', {'nombre': 260},path)
        assert read_preferences(path) == {
            'almacen_catalogo': {'codigo': 210, 'producto': 410},
            'usuarios_catalogo': {'nombre': 260},
        }
        assert 'nombre' not in read_preferences(path)['almacen_catalogo']


def test_archivo_malformado_no_bloquea_lectura():
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'prefs.json'
        path.write_text('{no-es-json',encoding='utf-8')
        assert read_preferences(path)=={}
        path.write_text('{"almacen":{"a":40,"b":130,"c":99999}}',encoding='utf-8')
        assert read_preferences(path)=={'almacen':{'b':130}}


def test_redimensionar_y_recargar_no_restablece_anchos():
    # Mocks de Treeview: comprueba el contrato sin pantalla ni CustomTkinter.
    class MockTree:
        def __init__(self):
            self._cols=('codigo','producto')
            self.widths={c:200 for c in self._cols}
            self.opts={}
        def __getitem__(self,item): return self._cols
        def configure(self,**kw): self._cols=tuple(kw['columns'])
        def heading(self, key, **kw): pass
        def column(self,key,option=None,**kw):
            if option=='width':return self.widths[key]
            if kw.get('width') is not None:self.widths[key]=kw['width']
            self.opts[key]=kw
        def bind(self,*a,**kw): pass
        def winfo_exists(self):return True
        def after_idle(self,func):func()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'prefs.json'
        with patch('ui.table_columns.preferences_path',return_value=path):
            tree=MockTree()
            mgr=TableColumnManager(tree,'almacen_catalogo')
            cols=(('codigo','Código AXIA',160),('producto','Producto',320))
            mgr.configure_columns(cols)
            assert tree.widths=={'codigo':160,'producto':320}
            assert tree.opts['producto']['stretch'] is False
            tree.widths['producto']=480
            mgr.capture_changed_widths()
            mgr.configure_columns(cols)
            assert tree.widths['producto']==480
            other=MockTree()
            TableColumnManager(other,'almacen_catalogo').configure_columns(cols)
            assert other.widths['producto']==480
            mgr.reset_widths()
            assert tree.widths['producto']==320
            restored=MockTree()
            TableColumnManager(restored,'almacen_catalogo').configure_columns(cols)
            assert restored.widths['producto']==320


def test_columna_nueva_no_pierde_preferencias_anteriores():
    class MockTree:
        def __init__(self):self.cols=(); self.widths={}
        def __getitem__(self,_):return self.cols
        def configure(self,**kw):self.cols=tuple(kw['columns']);self.widths.update({k:200 for k in self.cols if k not in self.widths})
        def heading(self,*a,**kw):pass
        def column(self,k,opt=None,**kw):
            if opt=='width':return self.widths[k]
            self.widths[k]=kw['width']
        def bind(self,*a,**kw):pass
    with tempfile.TemporaryDirectory() as tmp:
        with patch('ui.table_columns.preferences_path',return_value=Path(tmp)/'settings.json'):
            tree=MockTree()
            mgr=TableColumnManager(tree,'auditoria_eventos')
            mgr.configure_columns((('usuario','Usuario',150),('fecha','Fecha',125)))
            tree.widths['usuario']=300
            mgr.configure_columns((('usuario','Usuario',150),('accion','Acción',200)))
            mgr.configure_columns((('usuario','Usuario',150),('fecha','Fecha',125)))
            assert tree.widths['usuario']==300
            assert tree.widths['fecha']==125
