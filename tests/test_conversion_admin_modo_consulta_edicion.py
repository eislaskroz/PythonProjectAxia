from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'views' / 'orden_servicio_conversion_view.py'


def test_conversion_admin_carga_en_modo_consulta_y_edicion_explicita():
    src = SOURCE.read_text(encoding='utf-8')
    assert 'def _set_modo_edicion(habilitado):' in src
    assert '_set_modo_edicion(False)' in src
    assert 'text="✎ Editar"' in src
    assert 'text="💾 Guardar"' in src
    assert 'text="✓ Convertir a OS"' in src
    assert 'text="📥 Cargar seleccionado"' in src
    assert 'text="👁 PDF Levantamiento"' in src
    assert 'actualizar_levantamiento' in src
    assert 'Guarda o finaliza la edición antes de convertir' in src
