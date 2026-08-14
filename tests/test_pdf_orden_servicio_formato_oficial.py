from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPERS = (ROOT / 'views' / 'formato_helpers.py').read_text(encoding='utf-8')
OPS = (ROOT / 'services' / 'operational_document_pdf.py').read_text(encoding='utf-8')

def test_os_tiene_renderer_especializado():
    assert 'def _generar_pdf_orden_servicio_axia' in HELPERS
    assert '"orden de servicio"' in HELPERS

def test_os_tiene_bloques_formato_oficial():
    for text in ('Descripción del Servicio y/o Instalación', 'Observaciones', 'Evaluación del Servicio', 'FIRMA CLIENTE / ENCARGADO'):
        assert text in HELPERS

def test_os_mapea_horas_y_evaluacion():
    for field in ('os_hora_llegada', 'os_hora_salida', 'os_eval_habilidades', 'os_eval_trato', 'os_eval_velocidad', 'os_eval_otro'):
        assert field in OPS
