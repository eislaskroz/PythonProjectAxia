from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def read(rel): return (ROOT / rel).read_text(encoding='utf-8')

def test_fecha_hoy_y_aco_selector():
    src=read('views/bitacora_avance_view.py')
    assert 'datetime.now().strftime("%d-%m-%Y")' in src
    assert 'obtener_contextos_aco_disponibles_bitacora' in src
    assert 'NativeComboBox' in src

def test_tecnicos_234_y_porcentaje():
    src=read('views/bitacora_avance_view.py')
    assert 'obtener_nombres_usuarios_por_tipos([2, 3, 4])' in src
    assert 'Porcentaje de avance' in src
    assert 'bit_porcentaje_avance' in src

def test_fotos_reemplazan_observaciones():
    src=read('views/bitacora_avance_view.py')
    assert 'Evidencias fotográficas' in src
    assert 'subir_evidencias_bitacora' in src
    assert 'texto_largo("Observaciones"' not in src

def test_migracion_fotos():
    src=read('migrations/20260814_bitacoras_evidencias_y_avance.sql')
    assert 'bit_fotos jsonb' in src
    assert "'bitacoras-evidencias'" in src
