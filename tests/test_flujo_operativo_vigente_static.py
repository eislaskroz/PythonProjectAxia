from pathlib import Path


def read(path):
    return Path(path).read_text(encoding='utf-8')


def test_menu_sigue_flujo_lev_aco_ot_bit_os():
    src = read('ui/app_sidebar.py')
    positions = [src.index(x) for x in (
        '📋 Levantamientos', '🏠 ACO', '🛠️ Órdenes de trabajo',
        '📊 Bitácoras operativas', '🧾 Órdenes de servicio'
    )]
    assert positions == sorted(positions)


def test_levantamiento_convierte_a_ot():
    src = read('views/orden_servicio_conversion_view.py')
    assert 'Convertir levantamiento en Orden de Trabajo' in src
    assert 'text="✓ Convertir a OT"' in src
    assert 'convertir_levantamiento_a_trabajo' in src


def test_ot_bit_os_acciones_vigentes():
    src = read('controllers/navigation_controller.py')
    assert '"accion_text": "✓ Convertir a OS"' in src
    assert '"accion_text": "✓ Asignar a OT"' in src
    assert '"accion_text": "✓ Finalizar OT"' in src


def test_relaciones_persistentes_estan_migradas():
    sql = read('migrations/20260813_flujo_lev_aco_ot_bit_os.sql')
    for col in ('ot_folio_levantamiento', 'bit_ot_folio', 'os_folio_ot', 'os_folio_bitacora'):
        assert col in sql
