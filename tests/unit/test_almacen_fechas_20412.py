"""Regresiones: horas correctas al consultar el Kárdex de Supabase."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.almacen_fechas import fecha_kardex_mexico


def test_supabase_utc_a_hora_de_mexico():
    assert fecha_kardex_mexico('2026-10-29T18:14:16+00:00') == '29/10/2026 12:14:16'
    assert fecha_kardex_mexico('2026-10-29T18:14:16.123456Z') == '29/10/2026 12:14:16'


def test_timestamp_con_zona_y_cruce_de_dia():
    assert fecha_kardex_mexico('2026-10-30T02:10:00+00:00') == '29/10/2026 20:10:00'
    assert fecha_kardex_mexico('2026-10-29T12:14:16-06:00') == '29/10/2026 12:14:16'
    assert fecha_kardex_mexico(datetime(2026, 10, 29, 18, 14, 16, tzinfo=timezone.utc)) == '29/10/2026 12:14:16'


def test_timestamp_sin_zona_y_datos_incompletos():
    assert fecha_kardex_mexico('2026-10-29 18:14:16') == '29/10/2026 12:14:16'
    assert fecha_kardex_mexico('') == ''
    assert fecha_kardex_mexico(None) == ''
    assert fecha_kardex_mexico('valor no reconocido') == 'valor no reconocido'


def test_vista_kardex_usa_conversion_sin_reformatear_sql():
    fuente = (Path(__file__).resolve().parents[2] / 'views' / 'almacen_view.py').read_text(encoding='utf-8')
    assert "'fecha': fecha_kardex_mexico(m.get('fecha'))" in fuente
    assert "str(m.get('fecha') or '')[:19]" not in fuente
