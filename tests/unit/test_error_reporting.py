from core.error_reporting import register_error, get_last_error, clear_last_error

def test_registra_error_con_codigo_y_detalle():
    clear_last_error()
    report=register_error(ValueError("columna inexistente"), "Registrar prueba")
    assert report.incident_id.startswith("AX-")
    assert report.exception_type == "ValueError"
    assert "columna inexistente" in report.technical_message
    assert get_last_error() == report

def test_oculta_secretos():
    report=register_error(RuntimeError("password=secreto token=abc123"), "Prueba")
    assert "secreto" not in report.technical_message
    assert "abc123" not in report.technical_message
