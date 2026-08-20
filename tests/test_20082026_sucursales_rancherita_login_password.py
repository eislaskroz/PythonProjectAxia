from pathlib import Path


def test_sucursal_schema_and_form_fields_present():
    service = Path("services/sucursales_service.py").read_text(encoding="utf-8")
    view = Path("views/clientes_admin_view.py").read_text(encoding="utf-8")
    for field in ("suc_calle_numero", "suc_colonia", "suc_codigo_postal"):
        assert field in service
        assert field in view
    for label in ("Calle y Número", "Colonia", "Código Postal"):
        assert label in view


def test_rancherita_migration_contains_all_branches():
    sql = Path("migrations/20260820_sucursales_direccion_rancherita.sql").read_text(encoding="utf-8")
    for branch in ("ERMITA", "REYES", "GUSTAVO BAZ", "F-620", "D-406", "D-401", "C-309", "TEXCOCO", "A-45", "C-19", "CARPIO"):
        assert f"'{branch}'" in sql
    assert "ADD COLUMN IF NOT EXISTS suc_calle_numero" in sql
    assert "ADD COLUMN IF NOT EXISTS suc_colonia" in sql
    assert "ADD COLUMN IF NOT EXISTS suc_codigo_postal" in sql


def test_login_has_password_visibility_toggle():
    login = Path("login.py").read_text(encoding="utf-8")
    assert "def alternar_password" in login
    assert 'entry_password.configure(show="" if password_visible["valor"] else "*")' in login
