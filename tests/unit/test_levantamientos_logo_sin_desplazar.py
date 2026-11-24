from pathlib import Path
from PIL import Image
from services.levantamiento_seguridad_pdf import generar_pdf_levantamiento_maestro
from core.pdf.base_pdf import BasePdfGenerator


def test_levantamientos_conservan_altura_original_y_fondo_propio(tmp_path):
    assert BasePdfGenerator.TOP_MARGIN == 96
    fondo = BasePdfGenerator.BACKGROUND_LEVANTAMIENTOS_PATH
    assert fondo.is_file()
    with Image.open(fondo) as imagen:
        assert imagen.size == Image.open(BasePdfGenerator.BACKGROUND_PATH).size
    ruta = tmp_path / "levantamiento.pdf"
    generar_pdf_levantamiento_maestro({"lev_folio": "LEV-LOGO-TEST", "lev_detalle_tecnico_json": {"tipo_levantamiento": "General", "resumen_servicio": "Prueba"}}, ruta_salida=ruta)
    assert ruta.is_file() and ruta.stat().st_size > 1000


def test_otros_formatos_conservan_sus_fondos():
    code = (Path(__file__).resolve().parents[2] / "core/pdf/base_pdf.py").read_text("utf8")
    assert 'elif title_key.startswith("levantamiento")' in code
    assert 'background_path = cls.BACKGROUND_PATH' in code
