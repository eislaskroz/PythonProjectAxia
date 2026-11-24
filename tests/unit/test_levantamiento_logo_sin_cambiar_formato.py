from pathlib import Path

import fitz

from core.pdf.base_pdf import BasePdfGenerator
from services.levantamiento_seguridad_pdf import generar_pdf_levantamiento_maestro


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


def test_todas_las_tablas_principales_alineadas_y_logo_despejado(tmp_path):
    destino = tmp_path / "levantamiento.pdf"
    generar_pdf_levantamiento_maestro(_registro_largo(), ruta_salida=destino)
    with fitz.open(destino) as pdf:
        assert len(pdf) >= 2
        for pagina in pdf:
            # Los bloques tabulares anchos comparten x inicial y x final, incluso tras el salto de página.
            cuadros = [d["rect"] for d in pagina.get_drawings()
                       if d["rect"].width > 350 and 115 <= d["rect"].y0 <= 450]
            assert cuadros
            bordes = {(round(r.x0, 1), round(r.x1, 1)) for r in cuadros}
            assert bordes == {(40.0, 522.4)}
            assert "LEVANTAMIENTOS" in pagina.get_text()
    assert BasePdfGenerator.BACKGROUND_PATH.name == "FormatoFondo.png"


def test_sin_parches_visuales_ni_fondos_alternativos():
    root = Path(__file__).resolve().parents[2]
    source = (root / "services/levantamiento_seguridad_pdf.py").read_text(encoding="utf8")
    assert "_proteger_logo_pdf_levantamiento" not in source
    assert "hAlign=\"LEFT\"" in source
    background = (root / "core/pdf/base_pdf.py").read_text(encoding="utf8")
    assert "BACKGROUND_LEVANTAMIENTOS_PATH" not in background
