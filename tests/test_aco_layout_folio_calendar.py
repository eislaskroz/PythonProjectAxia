from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_aco_form_uses_full_area_fixed_actions_and_click_only_calendar():
    source = (ROOT / 'views' / 'inicio_aco_view.py').read_text(encoding='utf-8')
    assert 'form.pack(fill="both", expand=True' in source
    assert 'barra_acciones.pack(fill="x"' in source
    assert 'asociar_selector_fecha(entry, form, variable, abrir_con_foco=False)' in source
    # El alta ACO ya no debe disparar el calendario al recibir foco.
    segment = source[source.index('def mostrar_formulario_crear_aco'):source.index('def mostrar_solicitud_aco')]
    assert '<FocusIn>' not in segment


def test_aco_number_is_generated_by_supabase_trigger():
    view = (ROOT / 'views' / 'inicio_aco_view.py').read_text(encoding='utf-8')
    service = (ROOT / 'services' / 'acos_service.py').read_text(encoding='utf-8')
    migration = (ROOT / 'migrations' / '20260813_folio_aco_automatico.sql').read_text(encoding='utf-8')

    segment = view[view.index('def mostrar_formulario_crear_aco'):view.index('def mostrar_solicitud_aco')]
    assert 'aco_numero NO se envía' in segment
    assert 'datos_aco.pop("aco_numero", None)' in service
    assert 'CREATE OR REPLACE FUNCTION public.generar_folio_aco()' in migration
    assert "'ACO-' || v_mes || '-' || TO_CHAR(v_fecha, 'YYYY') || '-'" in migration
    assert "LPAD(v_siguiente::text, 3, '0')" in migration
    assert 'pg_advisory_xact_lock' in migration
