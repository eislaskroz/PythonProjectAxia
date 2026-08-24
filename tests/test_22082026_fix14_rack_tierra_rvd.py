from pathlib import Path
from services.ordenes_trabajo_schema import partidas_desde_detalle_levantamiento

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "views" / "levantamiento_view.py").read_text(encoding="utf-8")
PDF = (ROOT / "services" / "levantamiento_seguridad_pdf.py").read_text(encoding="utf-8")


def test_rack_tiene_modalidades_y_accesorios():
    assert 'Forma de suministro del rack' in VIEW
    assert '["Kit completo", "Rack solo"]' in VIEW
    for texto in ("Organizadores (cantidad)", "Charolas (cantidad)", "PDU (cantidad)", "Panel de parcheo (cantidad)"):
        assert texto in VIEW


def test_tierra_fisica_desglosa_materiales():
    assert '¿Se requiere tierra física?' in VIEW
    for texto in (
        "Barra de cobre (pzas)", "Aisladores de cobre (pzas)", "Varilla de cobre (pzas)",
        "Abrazaderas de cobre (pzas)", "Cable de cobre (m)", "Químico (botes/juegos)",
        "Tubería (m)", "Bote / registro (pzas)",
    ):
        assert texto in VIEW


def test_materiales_rack_tierra_llegan_a_cotizacion():
    detalle = {
        "materiales_rack_tierra": [
            {"material": "Rack", "categoria": "Rack", "cantidad": "1", "unidad": "Pieza(s)", "especificacion": "24U"},
            {"material": "PDU", "categoria": "Rack", "cantidad": "1", "unidad": "Pieza(s)"},
            {"material": "Cable de cobre", "categoria": "Tierra física", "cantidad": "15", "unidad": "Metro(s)"},
        ]
    }
    partidas = partidas_desde_detalle_levantamiento(detalle)
    conceptos = {p["concepto"] for p in partidas}
    assert "Rack - 24U" in conceptos
    assert "PDU" in conceptos
    assert "Cable de cobre" in conceptos


def test_pdf_homologa_etiquetas_nuevas():
    for clave in ("modalidad_rack", "cantidad_kit_rack", "rack_pdu", "tierra_barra_cobre", "tierra_cable_cobre"):
        assert f'"{clave}"' in PDF
