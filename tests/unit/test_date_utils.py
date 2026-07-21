from core.date_utils import normalizar_fecha_supabase

def test_normaliza_fecha_mexicana():
    assert normalizar_fecha_supabase("22/07/2026") == "2026-07-22"

def test_conserva_fecha_iso():
    assert normalizar_fecha_supabase("2026-07-22") == "2026-07-22"
