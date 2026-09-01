import json
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from services.levantamiento_seguridad_pdf import generar_pdf_levantamiento_maestro


def test_pdf_clasifica_y_renderiza_complementos_field(tmp_path):
    annotation = tmp_path / "annotation.png"
    Image.new("RGB", (800, 500), "white").save(annotation)
    photo = tmp_path / "photo.jpg"
    Image.new("RGB", (640, 480), "blue").save(photo)
    attached = tmp_path / "plans.pdf"
    pdf = canvas.Canvas(str(attached))
    pdf.drawString(72, 720, "PLANO FIELD PAGINA 1")
    pdf.showPage()
    pdf.drawString(72, 720, "PLANO FIELD PAGINA 2")
    pdf.save()

    evidence = [
        {"path": str(annotation), "mime": "image/png", "relacion_clave": "plan_annotation", "nombre": annotation.name},
        {"path": str(photo), "mime": "image/jpeg", "relacion_clave": "", "nombre": photo.name},
        {"path": str(attached), "mime": "application/pdf", "relacion_clave": "attached_plans", "nombre": attached.name},
    ]
    record = {
        "lev_folio": "LEV-TEST-FIELD",
        "lev_tipo": 2,
        "lev_tipo_levantamiento": "Redes Voz y Datos",
        "lev_modalidad_operativa": "Instalación",
        "lev_cliente": "CLIENTE PRUEBA",
        "lev_descripcion": "Prueba de complementos FIELD",
        "lev_detalle_tecnico_json": {"tipo_levantamiento": "Redes Voz y Datos"},
        "lev_evidencias_json": json.dumps(evidence),
    }
    output = tmp_path / "master.pdf"
    generar_pdf_levantamiento_maestro(record, ruta_salida=output, abrir=False)

    reader = PdfReader(output)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "ANOTACIONES TIPO PLANO" in text.upper()
    assert "EVIDENCIA FOTOGRÁFICA" in text.upper()
    assert "ARCHIVOS PDF / PLANOS ADJUNTOS" in text.upper()
    assert "Wants attachments" not in text
    assert "PLANO FIELD PAGINA 1" in text
    assert "PLANO FIELD PAGINA 2" in text
    assert len(reader.pages) >= 4
