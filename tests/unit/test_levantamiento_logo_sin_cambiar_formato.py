from pathlib import Path

import fitz

from core.pdf.base_pdf import BasePdfGenerator
from services import levantamiento_seguridad_pdf as generator


def _registro_largo():
    partidas = [
        {
            "material": ("CABLE FIBRA OPTICA PARA INTERIOR Y EXTERIOR ") * (5 + i % 2),
            "cantidad": str(i + 1),
            "unidad": "Pieza(s)",
            "especificacion": f"PARTIDA {i + 1}",
        }
        for i in range(26)
    ]
    return {
        "lev_folio": "LEV-PRUEBA",
        "lev_descripcion": "Instalación y adecuación de servicios",
        "lev_cliente": "CLIENTE DE PRUEBA",
        "lev_detalle_tecnico_json": {
            "tipo_levantamiento": "General",
            "materiales_miscelaneos": partidas,
        },
    }


def test_logo_original_y_mismo_texto_en_multipagina(tmp_path, monkeypatch):
    reg = _registro_largo()
    original = tmp_path / "sin_proteccion.pdf"
    corregido = tmp_path / "protegido.pdf"

    with monkeypatch.context() as m:
        m.setattr(generator, "_proteger_logo_pdf_levantamiento", lambda _: None)
        generator.generar_pdf_levantamiento_maestro(reg, ruta_salida=original)
    generator.generar_pdf_levantamiento_maestro(reg, ruta_salida=corregido)

    base = fitz.open(original)
    nuevo = fitz.open(corregido)
    assert len(base) == len(nuevo) >= 2
    for anterior, actual in zip(base, nuevo):
        assert [w[4] for w in anterior.get_text("words")] == [w[4] for w in actual.get_text("words")]
    assert BasePdfGenerator.BACKGROUND_PATH.name == "FormatoFondo.png"


def test_sin_plantilla_corporativa_exclusiva():
    root = Path(__file__).resolve().parents[2]
    source = (root / "core/pdf/base_pdf.py").read_text(encoding="utf8")
    assert "BACKGROUND_LEVANTAMIENTOS_PATH" not in source
