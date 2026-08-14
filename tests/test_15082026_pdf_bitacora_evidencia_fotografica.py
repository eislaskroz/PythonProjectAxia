from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_renderer_incluye_evidencia_fotografica_real():
    src = (ROOT / 'views' / 'formato_helpers.py').read_text(encoding='utf-8')
    assert 'EVIDENCIA FOTOGRÁFICA' in src
    assert 'ImageOps.exif_transpose' in src
    assert 'requests.get(origen, timeout=12)' in src
    assert 'bitacoras-evidencias' in src


def test_formulario_pasa_fotos_preview_y_pdf_definitivo():
    src = (ROOT / 'views' / 'bitacora_avance_view.py').read_text(encoding='utf-8')
    assert 'def datos_pdf(evidencias=None):' in src
    assert '"Evidencia Fotográfica": fotos_pdf' in src
    assert 'datos_pdf(evidencias_pdf)' in src


def test_admin_pasa_bit_fotos_al_renderer_maestro():
    src = (ROOT / 'services' / 'pdf_registro_service.py').read_text(encoding='utf-8')
    assert '"Evidencia Fotográfica": registro.get("bit_fotos") or []' in src
