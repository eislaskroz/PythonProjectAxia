"""Regresiones de borrado individual de fotos del Reportador Fotográfico."""
from unittest.mock import MagicMock
from pathlib import Path
import ast

# Aislar la lógica sin cargar CustomTkinter (no disponible en CI sin UI).
SOURCE = Path(__file__).resolve().parents[2] / 'views' / 'reportador_fotografico_view.py'
module = ast.parse(SOURCE.read_text(encoding='utf-8'))
cls = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'ReportadorFotografico')
method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_eliminar_foto')
namespace = {'messagebox': MagicMock(), 'rf': MagicMock()}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)

class ReportadorFotografico:
    _eliminar_foto = namespace['_eliminar_foto']


def _editor():
    editor = object.__new__(ReportadorFotografico)
    editor.estado = 'BORRADOR'
    editor.report_id = 17
    editor.contenedor = MagicMock()
    editor._actualizar_fotos = MagicMock()
    editor._changed = MagicMock()
    editor._error = MagicMock()
    return editor


def test_eliminar_pendiente_no_toca_las_otras_fotos():
    editor = _editor()
    editor.report_id = None
    act = {'clave': 'a', 'pendientes': {1: 'uno.jpg', 2: 'dos.jpg', 3: 'tres.jpg'}, 'fotos': {}}
    namespace['messagebox'].askyesno.return_value = True
    namespace['rf'].quitar_imagen.reset_mock(side_effect=True)
    remote = namespace['rf'].quitar_imagen
    if True:
        editor._eliminar_foto(act, 2)
        assert act['pendientes'] == {1: 'uno.jpg', 3: 'tres.jpg'}
        remote.assert_not_called()
        editor._actualizar_fotos.assert_called_once_with(act)


def test_eliminar_guardada_solo_elimina_slot_elegido():
    editor = _editor()
    act = {'clave': 'a', 'pendientes': {}, 'fotos': {1: 'uno.jpg', 2: 'dos.jpg', 3: 'tres.jpg'}}
    namespace['messagebox'].askyesno.return_value = True
    namespace['rf'].quitar_imagen.reset_mock(side_effect=True)
    remote = namespace['rf'].quitar_imagen
    if True:
        editor._eliminar_foto(act, 2)
        remote.assert_called_once_with(17, 2, 'a')
        assert act['fotos'] == {1: 'uno.jpg', 3: 'tres.jpg'}


def test_error_de_servidor_mantiene_foto_en_pantalla():
    editor = _editor()
    act = {'clave': 'a', 'pendientes': {}, 'fotos': {1: 'uno.jpg'}}
    namespace['messagebox'].askyesno.return_value = True
    namespace['rf'].quitar_imagen.side_effect = RuntimeError('Servidor no disponible')
    if True:
        editor._eliminar_foto(act, 1)
        assert act['fotos'] == {1: 'uno.jpg'}
        editor._actualizar_fotos.assert_not_called()
        editor._error.assert_called_once()


def test_finalizado_no_elimina():
    editor = _editor()
    editor.estado = 'FINALIZADO'
    act = {'clave': 'a', 'pendientes': {1: 'uno.jpg'}, 'fotos': {}}
    confirm = namespace['messagebox'].askyesno
    confirm.reset_mock()
    if True:
        editor._eliminar_foto(act, 1)
        assert act['pendientes'] == {1: 'uno.jpg'}
        confirm.assert_not_called()
