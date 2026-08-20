from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / 'views' / 'cotizaciones_view.py').read_text(encoding='utf-8')
SERVICE = (ROOT / 'services' / 'cotizaciones_service.py').read_text(encoding='utf-8')


def test_bandeja_superior_muestra_cotizaciones_pendientes_y_levantamientos():
    assert 'Cotizaciones realizadas · Pendientes de Compras' in VIEW
    assert 'Levantamientos preautorizados' in VIEW
    assert 'tabla_cot = NativeTreeTable' in VIEW
    assert 'tabla = NativeTreeTable' in VIEW


def test_cotizaciones_pendientes_solo_consulta_borrador():
    assert 'def obtener_cotizaciones_pendientes_compras' in SERVICE
    assert '.eq("cot_estatus", ESTATUS_BORRADOR)' in SERVICE


def test_cotizacion_guardada_se_puede_reabrir_desde_su_levantamiento():
    assert 'def obtener_levantamiento_de_cotizacion' in SERVICE
    assert 'def cargar_cotizacion_seleccionada' in VIEW
    assert 'obtener_levantamiento_de_cotizacion(cot)' in VIEW
