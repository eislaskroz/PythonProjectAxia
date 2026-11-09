"""Evita que el PDF administrativo BIT regrese al render genérico."""
from pathlib import Path


def test_admin_bitacora_renderer_explicito():
    root = Path(__file__).resolve().parents[2]
    controller = (root / "controllers/navigation_controller.py").read_text(encoding="utf-8")
    view = (root / "views/admin_operational_editor_view.py").read_text(encoding="utf-8")
    pdf = (root / "services/pdf_registro_service.py").read_text(encoding="utf-8")
    assert '"pdf_renderer": "bitacora_avance"' in controller
    assert 'pdf_config.get("pdf_renderer") == "bitacora_avance"' in view
    assert 'generar_pdf_registro(record, pdf_config, abrir=True)' in view
    assert '(configuracion or {}).get("pdf_renderer") == "bitacora_avance"' in pdf
    assert '"Bitácora de Avance", datos_bit' in pdf
