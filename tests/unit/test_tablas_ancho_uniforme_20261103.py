"""Regresión: columnas ocupan ancho disponible sin alterar altos/barras."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ui.table_columns import TableColumnManager, distribuir_anchos


def test_distribuye_sobrante_sin_comprimir_contenido():
    anchos = distribuir_anchos([120, 210, 70], 1100)
    assert sum(anchos) == 1100
    assert all(a >= b for a, b in zip(anchos, [120, 210, 70]))
    assert distribuir_anchos([120, 210, 70], 250) == [120, 210, 70]
    assert distribuir_anchos([], 1000) == []


class FakeTree:
    def __init__(self, width=1000):
        self.cols = ()
        self.widths = {}
        self.viewport = width
        self.handlers = {}

    def __getitem__(self, key):
        return self.cols

    def configure(self, **kwargs):
        self.cols = tuple(kwargs['columns'])
        self.widths.update((col, 100) for col in self.cols if col not in self.widths)

    def heading(self, *_args, **_kwargs):
        pass

    def column(self, key, option=None, **kwargs):
        if option == 'width':
            return self.widths[key]
        if 'width' in kwargs:
            self.widths[key] = kwargs['width']

    def bind(self, event, callback, **_kwargs):
        self.handlers[event] = callback

    def after_idle(self, callback):
        callback()

    def winfo_exists(self):
        return True

    def winfo_width(self):
        return self.viewport


def test_ajuste_automatico_no_se_guarda_como_preferencia():
    with TemporaryDirectory() as temp:
        config = Path(temp) / 'preferencias_tablas.json'
        with patch('ui.table_columns.preferences_path', return_value=config):
            tree = FakeTree(width=1000)
            manager = TableColumnManager(tree, 'vista_pruebas')
            manager.configure_columns([('usuario', 'Usuario', 120),
                                       ('nombre', 'Nombre completo', 210),
                                       ('tipo', 'Tipo', 70)])
            assert 990 <= sum(tree.widths.values()) <= 1000
            assert not config.exists()  # Autoajuste nunca se persiste.
            tree.viewport = 290
            tree.handlers['<Configure>']()
            assert sum(tree.widths.values()) >= 400  # Scroll horizontal disponible.
            assert not config.exists()


def test_contenido_amplia_columnas_sin_modificar_altura():
    with TemporaryDirectory() as temp:
        with patch('ui.table_columns.preferences_path', return_value=Path(temp)/'prefs.json'):
            tree = FakeTree(width=420)
            manager = TableColumnManager(tree, 'otra_tabla')
            manager.configure_columns([('folio', 'Folio', 90), ('cliente', 'Cliente', 150)])
            manager.set_content_widths({'cliente': 385})
            assert tree.widths['cliente'] >= 385
            assert sum(tree.widths.values()) > tree.viewport


def test_ancho_personalizado_sigue_persistiendo():
    with TemporaryDirectory() as temp:
        path = Path(temp) / 'prefs.json'
        with patch('ui.table_columns.preferences_path', return_value=path):
            tree = FakeTree(width=300)
            manager = TableColumnManager(tree, 'otra_tabla')
            manager.configure_columns([('folio', 'Folio', 90), ('cliente', 'Cliente', 150)])
            tree.widths['cliente'] = 320
            manager.capture_changed_widths()
            assert manager.saved['cliente'] == 320
            assert path.exists()
            manager.reset_widths()
            assert manager.saved.get('cliente') is None
