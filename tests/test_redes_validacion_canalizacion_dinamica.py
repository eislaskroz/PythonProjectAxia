from pathlib import Path


def test_redes_no_valida_campos_ocultos_de_materiales_legacy():
    source = Path('views/levantamiento_view.py').read_text(encoding='utf-8')
    start = source.index('        if tipo_levantamiento == "Redes Voz y Datos":', source.index('def formulario_preview_completo'))
    end = source.index('        if tipo_levantamiento == "Electricidad":', start)
    block = source[start:end]
    assert 'var_rvd_cantidad_patch_panel.get().strip()' not in block
    assert 'var_rvd_tipo_patch_panel.get().strip()' not in block
    assert 'canalizacion_materiales_completa()' in block
    assert 'var_rvd_necesidad.get().strip()' in block


def test_seguridad_canalizacion_solo_instalacion_y_mantenimiento_con_acceso():
    source = Path('views/levantamiento_view.py').read_text(encoding='utf-8')
    assert 'and var_modalidad_levantamiento.get().strip() != "Instalación"' in source
    assert 'if es_instalacion or es_mantenimiento:' in source
    assert 'detalle["acceso_alturas_riesgos"]' in source
