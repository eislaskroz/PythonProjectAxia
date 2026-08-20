from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mostrar_cotizaciones_usa_dos_argumentos_en_verificar_permiso():
    src = (ROOT / "controllers" / "navigation_controller.py").read_text(encoding="utf-8")
    bloque = src[src.index("def mostrar_cotizaciones"):src.index("def mostrar_compras")]
    assert "puede_cotizar_levantamientos," in bloque
    assert "puede_ver_compras," not in bloque


def test_fix28_consolida_columnas_compras_y_roles():
    sql = (ROOT / "migrations" / "20260820_fix28_correcciones_compras.sql").read_text(encoding="utf-8").lower()
    assert "cot_finalizado_por" in sql
    assert "cot_fecha_finalizacion" in sql
    assert "usu_tipo between 1 and 8" in sql
