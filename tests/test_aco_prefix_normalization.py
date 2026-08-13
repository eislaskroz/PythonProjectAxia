from services.acos_service import normalizar_numero_aco


def test_normaliza_prefijo_aco_repetido():
    assert normalizar_numero_aco("ACO-ACO-AGO-2026-001") == "ACO-AGO-2026-001"
    assert normalizar_numero_aco("aco-aco-aco-sep-2026-002") == "ACO-SEP-2026-002"
    assert normalizar_numero_aco("ACO-AGO-2026-003") == "ACO-AGO-2026-003"


def test_migracion_blinda_prefijo_repetido():
    from pathlib import Path
    migration = Path(__file__).resolve().parents[1] / "migrations" / "20260813_folio_aco_automatico.sql"
    sql = migration.read_text(encoding="utf-8")
    assert "regexp_replace(upper(btrim(NEW.aco_numero)), '^(ACO-)+', 'ACO-')" in sql
    assert "WHERE aco_numero ~* '^(ACO-){2,}'" in sql
