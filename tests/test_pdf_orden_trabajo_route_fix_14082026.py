from pathlib import Path
from services.ordenes_trabajo_schema import partidas_desde_detalle_levantamiento

ROOT = Path(__file__).resolve().parents[1]
PDF_SERVICE = (ROOT / 'services' / 'pdf_registro_service.py').read_text(encoding='utf-8')
HELPERS = (ROOT / 'views' / 'formato_helpers.py').read_text(encoding='utf-8')


def test_admin_ot_bypasses_generic_pdf_engine():
    assert '_clasificar_registro(registro, configuracion) == "orden_trabajo"' in PDF_SERVICE
    assert 'contrato_orden_trabajo' in PDF_SERVICE
    assert '"Orden de Trabajo", datos_ot' in PDF_SERVICE


def test_legacy_pdf_api_ot_uses_operational_renderer():
    assert 'casefold() == "orden de trabajo"' in HELPERS
    assert 'return _generar_pdf_orden_trabajo_axia(' in HELPERS


def test_partidas_extraidas_de_detalle_no_incluyen_resumen_narrativo():
    detail = {
        'canalizacion_materiales': [
            {'categoria': 'Tubo', 'tipo': 'PVC', 'tamano': '1/2', 'cantidad': '20', 'unidad': 'Metro(s)'},
        ],
        'equipos_principales': [
            {'familia': 'Switch', 'subfamilia': 'Administrable', 'cantidad': '1', 'marca': 'Ubiquiti', 'modelo': 'USW', 'caracteristicas': '24 puertos'},
        ],
        'materiales_miscelaneos': [
            {'material': 'Taquetes', 'cantidad': '100', 'unidad': 'Pieza(s)', 'especificacion': '1/4'},
        ],
        'texto_libre': 'ESTE TEXTO NO DEBE CONVERTIRSE EN UNA PARTIDA',
    }
    rows = partidas_desde_detalle_levantamiento(detail)
    assert len(rows) == 3
    concepts = ' | '.join(r['concepto'] for r in rows)
    assert 'PVC' in concepts
    assert 'Switch' in concepts
    assert 'Taquetes' in concepts
    assert 'ESTE TEXTO' not in concepts
