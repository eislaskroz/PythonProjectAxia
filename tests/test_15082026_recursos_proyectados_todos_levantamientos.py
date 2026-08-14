from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_levantamiento_tiene_seccion_comun_recursos_y_columnas_supabase():
    view = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
    schema = (ROOT / 'services' / 'levantamientos_schema.py').read_text(encoding='utf-8')
    assert 'Recursos proyectados' in view
    assert 'var_dias_trabajo_general' in view
    assert 'var_personas_considerar_general' in view
    assert '"lev_dias_trabajo"' in schema
    assert '"lev_personas_considerar"' in schema
    assert '"lev_dias_trabajo": int(var_dias_trabajo_general.get().strip())' in view
    assert '"lev_personas_considerar": int(var_personas_considerar_general.get().strip())' in view


def test_formularios_especializados_no_renderizan_campos_recursos_duplicados():
    view = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
    assert 'campo[0] not in {"dias_trabajo", "personas_trabajo", "personas_considerar"}' in view
    assert 'entry_aa(seccion_aa_riesgos, "Días de trabajo proyectados"' not in view
    assert 'entry_rvd(seccion_rvd_pruebas, "Días de trabajo proyectados"' not in view
    assert 'entry_ele(seccion_ele_pruebas, "Días de trabajo proyectados"' not in view


def test_obra_civil_tambien_guarda_recursos_proyectados():
    view = (ROOT / 'views' / 'obra_civil_view.py').read_text(encoding='utf-8')
    service = (ROOT / 'services' / 'obras_civiles_service.py').read_text(encoding='utf-8')
    assert 'seccion("Recursos proyectados"' in view
    assert '"obc_dias_trabajo": int(var_dias_trabajo.get().strip())' in view
    assert '"obc_personas_considerar": int(var_personas_considerar.get().strip())' in view
    assert 'obc_dias_trabajo' in service
    assert 'obc_personas_considerar' in service


def test_migracion_incluye_ambas_tablas():
    sql = (ROOT / 'migrations' / '20260815_recursos_proyectados_todos_levantamientos.sql').read_text(encoding='utf-8')
    assert 'ALTER TABLE public.db_levantamientos' in sql
    assert 'lev_dias_trabajo integer' in sql
    assert 'lev_personas_considerar integer' in sql
    assert 'ALTER TABLE public.db_obras_civiles' in sql
    assert 'obc_dias_trabajo integer' in sql
    assert 'obc_personas_considerar integer' in sql
