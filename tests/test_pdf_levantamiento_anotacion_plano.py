from pathlib import Path

from services import levantamiento_seguridad_pdf as pdf
from services.axia_pdf_artifacts import PDF_RENDERER_VERSION


def test_renderer_version_includes_plano_change():
    assert PDF_RENDERER_VERSION >= 18


def test_master_renderer_reads_persisted_plano_json():
    source = Path(pdf.__file__).read_text(encoding='utf-8')
    assert 'lev_anotacion_plano_json' in source
    assert 'ANOTACIONES TIPO PLANO' in source.upper()
    assert '_append_anotacion_plano(story, registro, width, header)' in source
