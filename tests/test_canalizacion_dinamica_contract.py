from pathlib import Path

SOURCE = Path('views/levantamiento_view.py').read_text(encoding='utf-8')


def test_canalizacion_dinamica_se_persiste_en_json():
    assert '"canalizacion_materiales"' in SOURCE
    assert 'obtener_canalizacion_materiales_json()' in SOURCE


def test_formularios_con_canalizacion_comparten_repetidor():
    for nombre in (
        'Seguridad y Monitoreo',
        'Redes Voz y Datos',
        'Electricidad',
        'Control de Accesos',
        'Enlaces Inalámbricos',
    ):
        assert f'"{nombre}"' in SOURCE
    assert '➕ Agregar partida' in SOURCE


def test_tipo_tamano_y_cantidad_son_campos_separados():
    assert '"Categoría", "Tipo", "Tamaño / calibre / especificación", "Cantidad"' in SOURCE
    assert 'TAMANOS_TUBOS' in SOURCE
