from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_levantamiento_tiene_pregunta_y_validacion_evidencia():
    text=(ROOT/'views'/'levantamiento_view.py').read_text(encoding='utf-8')
    assert '¿Deseas agregar evidencia fotográfica?' in text
    assert 'var_desea_evidencias.get() == "Sí" and not evidencias_levantamiento' in text
    assert '__evidencias_locales' in text
    assert 'subir_evidencias_levantamiento' in text

def test_schema_incluye_evidencias():
    text=(ROOT/'services'/'levantamientos_schema.py').read_text(encoding='utf-8')
    assert '"lev_evidencias_json"' in text

def test_pdf_maestro_renderiza_evidencias():
    text=(ROOT/'services'/'levantamiento_seguridad_pdf.py').read_text(encoding='utf-8')
    assert 'def _append_evidencias_fotograficas' in text
    assert '_append_evidencias_fotograficas(story, registro, width, header)' in text

def test_obra_civil_evidencias_son_condicionales_y_storage():
    text=(ROOT/'views'/'obra_civil_view.py').read_text(encoding='utf-8')
    assert '¿Deseas agregar evidencia fotográfica?' in text
    assert 'subir_evidencias_obra_civil' in text
    assert '__evidencias_fotograficas' in text
