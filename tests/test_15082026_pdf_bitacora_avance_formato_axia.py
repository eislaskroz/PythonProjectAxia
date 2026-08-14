from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bitacora_pdf_usa_renderer_especializado():
    txt = (ROOT / "views" / "formato_helpers.py").read_text(encoding="utf-8")
    assert "def _generar_pdf_bitacora_avance_axia" in txt
    assert "DESCRIPCIÓN DEL SERVICIO" in txt
    assert "Porcentaje de Avance" in txt


def test_bitacora_datos_pdf_incluyen_flujo_vinculado():
    txt = (ROOT / "views" / "bitacora_avance_view.py").read_text(encoding="utf-8")
    assert '"Levantamiento": contexto_ot.get("ot_folio_levantamiento")' in txt
    assert '"OT": contexto_ot.get("ot_folio")' in txt
    assert '"Dirección de Servicio": var_direccion.get()' in txt
    assert '"Técnico(s)": var_tecnico.get()' in txt


def test_contexto_bitacora_recupera_folio_levantamiento():
    txt = (ROOT / "services" / "bitacoras_service.py").read_text(encoding="utf-8")
    assert "ot_folio_levantamiento" in txt


def test_titulo_bitacora_se_dibuja_en_cabecera_corporativa():
    txt = (ROOT / "core" / "pdf" / "base_pdf.py").read_text(encoding="utf-8")
    assert 'visible_title = "BITÁCORA DE AVANCE"' in txt
