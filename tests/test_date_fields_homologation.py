from pathlib import Path


def test_fecha_requerida_uses_date_type():
    text = Path("views/levantamientos/form_definitions.py").read_text(encoding="utf-8")
    assert '("fecha_requerida", "date", "Fecha requerida de entrega", "YYYY-MM-DD", "")' in text


def test_extra_forms_bind_date_picker():
    text = Path("views/levantamiento_view.py").read_text(encoding="utf-8")
    assert 'if "fecha" in texto.lower()' in text
    assert 'asociar_selector_fecha(entry, parent_frame, variable)' in text


def test_conversion_forms_use_shared_date_picker():
    for filename in ("views/orden_servicio_conversion_view.py", "views/orden_trabajo_conversion_view.py"):
        text = Path(filename).read_text(encoding="utf-8")
        assert "from ui.date_picker import asociar_selector_fecha" in text
        assert '"fecha" in label.lower()' in text
