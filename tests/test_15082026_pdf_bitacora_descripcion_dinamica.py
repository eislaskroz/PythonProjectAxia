from pathlib import Path


def test_descripcion_bitacora_sin_altura_fija():
    txt = Path("views/formato_helpers.py").read_text(encoding="utf-8")
    assert 'Spacer(1, 3.15*inch)' not in txt
    assert 'desc_body = Table([[p(descripcion or "Sin descripción registrada.")]]' in txt
