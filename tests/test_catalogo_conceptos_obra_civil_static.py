from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_migracion_catalogo_obra_incluye_tabla_y_102_registros():
    sql = (ROOT / 'migrations' / '20260814_catalogo_conceptos_obra_civil.sql').read_text(encoding='utf-8')
    assert 'db_obra_conceptos' in sql
    assert 'OBRA-0102' in sql
    assert sql.count("('OBRA-") == 102
    assert 'obra_precio_unitario' in sql


def test_formulario_obra_integra_catalogo_dinamico_y_pdf():
    src = (ROOT / 'views' / 'obra_civil_view.py').read_text(encoding='utf-8')
    assert 'Conceptos de obra requeridos' in src
    assert '+ Agregar concepto' in src
    assert 'obtener_conceptos_obra_seleccionados' in src
    assert '"_conceptos_obra"' in src
    assert '("Conceptos de obra", ["Tipo", "Partida", "Unidad", "Cantidad", "Concepto"]' in src


def test_servicio_catalogo_obra_lee_supabase():
    src = (ROOT / 'services' / 'obra_conceptos_service.py').read_text(encoding='utf-8')
    assert 'TABLA_OBRA_CONCEPTOS = "db_obra_conceptos"' in src
    assert 'obra_activo' in src
    assert 'order("obra_tipo")' in src
