from pathlib import Path
from services.ordenes_trabajo_schema import partidas_desde_detalle_levantamiento

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "views" / "levantamiento_view.py").read_text(encoding="utf-8")
PDF = (ROOT / "services" / "levantamiento_seguridad_pdf.py").read_text(encoding="utf-8")


def test_seguridad_rack_repite_modalidades_rvd():
    assert 'var_cctv_modalidad_rack' in VIEW
    assert 'Forma de suministro del rack' in VIEW
    for texto in ("Cantidad de kits de rack", "Organizadores (cantidad)", "Charolas (cantidad)", "PDU (cantidad)", "Panel de parcheo (cantidad)"):
        assert texto in VIEW


def test_seguridad_tierra_desglosa_materiales():
    for texto in ("Barra de cobre (pzas)", "Aisladores de cobre (pzas)", "Varilla de cobre (pzas)", "Abrazaderas de cobre (pzas)", "Cable de cobre (m)", "Químico (botes/juegos)", "Tubería (m)", "Bote / registro (pzas)"):
        assert texto in VIEW
    assert 'construir_materiales_rack_tierra_seguridad' in VIEW


def test_materiales_seguridad_llegan_a_cotizacion():
    detalle = {"materiales_rack_tierra": [
        {"material":"Rack","categoria":"Rack","cantidad":"1","unidad":"Pieza(s)","especificacion":"12U"},
        {"material":"PDU","categoria":"Rack","cantidad":"1","unidad":"Pieza(s)"},
        {"material":"Cable de cobre","categoria":"Tierra física","cantidad":"10","unidad":"Metro(s)"},
    ]}
    conceptos = {p["concepto"] for p in partidas_desde_detalle_levantamiento(detalle)}
    assert "Rack - 12U" in conceptos
    assert "PDU" in conceptos
    assert "Cable de cobre" in conceptos


def test_pdf_muestra_materiales_rack_tierra_seguridad():
    assert 'Materiales de rack y tierra física' in PDF
    assert 'materiales_rack_tierra' in PDF
