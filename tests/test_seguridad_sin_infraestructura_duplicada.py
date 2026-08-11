from pathlib import Path


def test_seguridad_no_renderiza_bloque_legacy_infraestructura_requerida():
    source = (Path(__file__).resolve().parents[1] / "views" / "levantamiento_view.py").read_text(encoding="utf-8")
    assert 'registrar_seccion("infraestructura_requerida"' not in source
    assert 'secciones_dinamicas["infraestructura_requerida"]' not in source
    assert '"infraestructura_requerida": {' not in source
    assert 'detalle["canalizacion_materiales"] = obtener_canalizacion_materiales_json()' in source
