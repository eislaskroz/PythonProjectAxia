from services.equipos_catalogo_service import MARCAS_COMUNES


def test_marcas_reales_ordenadas_alfabeticamente():
    assert MARCAS_COMUNES[0] == "Por definir"
    assert MARCAS_COMUNES[-1] == "Otra"
    reales = MARCAS_COMUNES[1:-1]
    assert reales == sorted(reales, key=str.casefold)
    assert len(reales) == len(set(reales))


def test_pdf_datos_generales_integra_dias_y_personas_en_misma_tabla():
    from pathlib import Path
    source = Path(__file__).parents[1] / "services" / "levantamiento_seguridad_pdf.py"
    text = source.read_text(encoding="utf-8")
    assert '"DÍAS DE TRABAJO", days or "No definido"' in text
    assert '"PERSONAS A CONSIDERAR", people or "No definido"' in text
    assert '[1.35*inch, 1.0*inch, 1.75*inch, 2.80*inch]' not in text
