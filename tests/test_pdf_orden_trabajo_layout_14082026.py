from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPERS = (ROOT / 'views' / 'formato_helpers.py').read_text(encoding='utf-8')


def test_ot_usa_renderer_especializado():
    assert 'def _generar_pdf_orden_trabajo_axia' in HELPERS
    assert 'casefold() == "orden de trabajo"' in HELPERS


def test_ot_contiene_datos_del_formato_referencia():
    for label in (
        'NO. ACO', 'JEFE DE OPERACIONES', 'NÚMERO DE DÍAS',
        'NÚMERO DE PERSONAS', 'SERVICIO', 'PARTIDA', 'UNIDAD',
        'CANTIDAD', 'MODELO', 'MARCA', 'CONCEPTO',
    ):
        assert label in HELPERS


def test_ot_tabla_es_dinamica_y_repite_encabezado():
    assert 'LongTable(' in HELPERS
    assert 'repeatRows=1' in HELPERS
    assert 'splitByRow=1' in HELPERS
