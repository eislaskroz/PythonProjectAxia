from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fix26_migracion_conserva_historial_y_agrega_auditoria_finalizacion():
    sql = (ROOT / "migrations" / "20260820_fix26_cotizacion_en_compra.sql").read_text(encoding="utf-8")
    assert "add column if not exists cot_finalizado_por" in sql.lower()
    assert "add column if not exists cot_fecha_finalizacion" in sql.lower()
    assert "en compra x cotización" in sql.lower()
    assert (ROOT / "migrations" / "20260820_cotizaciones_formales.sql").exists()


def test_fix26_view_incorpora_modificar_y_finalizar_sin_generar_ot():
    src = (ROOT / "views" / "cotizaciones_view.py").read_text(encoding="utf-8")
    assert "Modificar cotización" in src
    assert "Finalizar cotización" in src
    assert "finalizar_cotizacion_para_compras" in src
    assert "NO genera una Orden de Trabajo" in src
    assert "render(reg, forzar_edicion=True)" in src


def test_fix26_servicio_deja_bandeja_para_compras_y_no_invoca_ot():
    src = (ROOT / "services" / "cotizaciones_service.py").read_text(encoding="utf-8")
    assert 'ESTATUS_EN_COMPRA = "EN COMPRA X COTIZACIÓN"' in src
    assert "def obtener_cotizaciones_en_compra" in src
    assert "def finalizar_cotizacion_para_compras" in src
    bloque = src.split("def finalizar_cotizacion_para_compras", 1)[1].split("# Compatibilidad temporal", 1)[0]
    assert "orden_trabajo" not in bloque.lower()
    assert '"cot_estatus": ESTATUS_EN_COMPRA' in bloque


def test_fix26_schema_expone_auditoria_de_handoff():
    src = (ROOT / "services" / "cotizaciones_schema.py").read_text(encoding="utf-8")
    assert '"cot_finalizado_por"' in src
    assert '"cot_fecha_finalizacion"' in src
