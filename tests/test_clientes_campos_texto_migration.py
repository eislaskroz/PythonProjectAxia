from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "migrations" / "20260813_clientes_campos_texto_cifrado.sql").read_text(encoding="utf-8")


def test_migracion_amplia_campos_cliente_a_text():
    for campo in (
        "cli_razonsocial", "cli_rfc", "cli_contacto", "cli_telefono",
        "cli_correo", "cli_calle", "cli_numero", "cli_colonia",
        "cli_municipio", "cli_estado", "cli_cp", "cli_notas",
    ):
        assert f"ALTER COLUMN {campo}" in SQL
    assert "TYPE text" in SQL
    assert "BEGIN;" in SQL and "COMMIT;" in SQL
