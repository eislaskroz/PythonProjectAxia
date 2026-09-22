from pathlib import Path


def test_descripcion_bitacora_sin_altura_fija():
    txt = Path("views/formato_helpers.py").read_text(encoding="utf-8")
    assert 'Spacer(1, 3.15*inch)' not in txt
    assert 'desc_body = LongTable(filas_descripcion' in txt
    assert 'splitByRow=1' in txt


def test_descripcion_bitacora_conserva_saltos_de_linea_en_reportlab():
    txt = Path("views/formato_helpers.py").read_text(encoding="utf-8")
    assert 'contenido = contenido.replace("\\r\\n", "\\n").replace("\\r", "\\n")' in txt
    assert 'contenido = contenido.replace("\\n", "<br/>")' in txt


def test_descripcion_bitacora_puede_continuar_en_otra_pagina():
    txt = Path("views/formato_helpers.py").read_text(encoding="utf-8")
    assert 'filas_descripcion = [' in txt
    assert '[p(linea)] if linea else [Spacer(1, normal.leading)]' in txt
    assert 'LongTable puede continuar en otra' in txt
