from io import BytesIO

import fitz

from services.reportador_fotografico_pdf import CONTENT_LEFT, CONTENT_RIGHT, generar_pdf_bytes


def test_evidencias_automaticas_y_anexos_respetan_margen():
    from tests.unit.test_reportador_pdf_original_20261109 import modelo

    detalle, fetch = modelo(os_count=2)
    data = generar_pdf_bytes(detalle, fetch)
    with fitz.open(stream=BytesIO(data), filetype="pdf") as document:
        assert len(document) >= 3
        counted = 0
        for page in document:
            for image in page.get_images(full=True):
                for rect in page.get_image_rects(image[0]):
                    if rect.width > 590 and rect.height > 750:
                        continue  # Fondo corporativo de hoja completa
                    counted += 1
                    assert rect.x0 >= CONTENT_LEFT - 0.1
                    assert rect.x1 <= CONTENT_RIGHT + 0.1
        assert counted >= 7  # Cinco fotos y dos OS escaneadas


def test_imagenes_no_estiran_fotografias():
    from tests.unit.test_reportador_pdf_original_20261109 import modelo
    data = generar_pdf_bytes(*modelo(os_count=1))
    with fitz.open(stream=BytesIO(data), filetype="pdf") as document:
        for page in document:
            for image in page.get_images(full=True):
                iw, ih = image[2], image[3]
                for rect in page.get_image_rects(image[0]):
                    if rect.width > 590 and rect.height > 750:
                        continue
                    assert abs(rect.width / rect.height - iw / ih) < 0.02
