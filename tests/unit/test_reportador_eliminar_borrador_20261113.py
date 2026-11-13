"""Comprobaciones estructurales del borrado individual de autoguardados."""
from pathlib import Path
import ast

VIEW = Path(__file__).resolve().parents[2] / 'views' / 'reportador_fotografico_view.py'
SERVICE = Path(__file__).resolve().parents[2] / 'services' / 'reportador_fotografico_service.py'


def test_vista_y_servicio_compilan():
    ast.parse(VIEW.read_text(encoding='utf-8'))
    ast.parse(SERVICE.read_text(encoding='utf-8'))


def test_eliminar_usa_clave_confirmacion_y_api_existente():
    tree = ast.parse(VIEW.read_text(encoding='utf-8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ReportadorFotografico')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'eliminar_borrador')
    source = ast.get_source_segment(VIEW.read_text(encoding='utf-8'), method)
    assert 'askyesno' in source
    assert "draft.get('clave')" in source
    assert 'rf.borrar_autoguardado(clave)' in source
    assert 'self.panel()' in source
    assert 'self._error' in source
    assert 'rf.guardar_reporte' not in source


def test_cada_boton_eliminar_captura_su_borrador():
    source = VIEW.read_text(encoding='utf-8')
    assert "lambda d=draft: self.eliminar_borrador(d)" in source
    assert "'Eliminar'" in source
    assert "_accion('borrar_autoguardado', clave=clave)" in SERVICE.read_text(encoding='utf-8')
