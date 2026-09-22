from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ui_exige_cotizacion_finalizada_y_permiso():
    texto = (ROOT / "views" / "orden_servicio_conversion_view.py").read_text(encoding="utf-8")
    assert "obtener_cotizacion_finalizada_de_levantamiento" in texto
    assert "cotizacion_finalizada and autorizado" in texto
    assert 'btn_convertir.configure(state="normal")' in texto
    assert "Solo Administrador o Jefe de Operaciones" in texto


def test_servicio_revalida_permiso_y_cotizacion():
    texto = (ROOT / "services" / "ordenes_trabajo_service.py").read_text(encoding="utf-8")
    bloque = texto[texto.index("def convertir_levantamiento_a_trabajo"):texto.index("def buscar_ordenes_trabajo_por_aco")]
    assert "puede_convertir_levantamiento_a_orden(usuario_activo)" in bloque
    assert "obtener_cotizacion_finalizada_de_levantamiento" in bloque
    assert "debe estar finalizada y enviada a Compras" in bloque


def test_consulta_identifica_estado_finalizado():
    texto = (ROOT / "services" / "cotizaciones_service.py").read_text(encoding="utf-8")
    bloque = texto[texto.index("def obtener_cotizacion_finalizada_de_levantamiento"):texto.index("def finalizar_cotizacion_para_compras")]
    assert '.eq("cot_estatus", ESTATUS_EN_COMPRA)' in bloque
    assert 'consulta.eq("id_levantamiento", id_levantamiento)' in bloque
    assert 'consulta.eq("lev_folio", folio)' in bloque
