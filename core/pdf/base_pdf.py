"""Motor corporativo PDF 2.0 para documentos AXIA.

Centraliza fondo, metadatos, márgenes, estilos y numeración de página.
"""
from __future__ import annotations

from core.logger import configurar_logger

logger = configurar_logger(__name__)

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas

from core.version import APP_VERSION


class BasePdfGenerator:
    """Configuración visual compartida por todos los documentos PDF de AXIA."""

    PRIMARY = colors.HexColor("#0B324A")
    SECONDARY = colors.HexColor("#00BCEB")
    BORDER = colors.HexColor("#B8C2CC")
    LIGHT = colors.HexColor("#F4F8FB")
    TEXT = colors.HexColor("#243447")

    ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
    BACKGROUND_PATH = ASSETS_DIR / "FormatoFondo.png"

    # Área útil calculada para no invadir encabezado ni pie de la plantilla.
    LEFT_MARGIN = 34
    RIGHT_MARGIN = 34
    TOP_MARGIN = 96
    BOTTOM_MARGIN = 78

    @classmethod
    def canvas_factory(cls, title: str):
        def _factory(filename, pagesize=None, **kwargs):
            canvas = Canvas(filename, pagesize=pagesize or letter, **kwargs)
            canvas.setTitle(f"AXIA - {title}")
            canvas.setAuthor("AXIA Comunicaciones S.A. de C.V.")
            canvas.setSubject(f"Documento corporativo AXIA: {title}")
            canvas.setCreator(f"Sistema AXIA {APP_VERSION}")
            return canvas
        return _factory

    @classmethod
    def draw_page(cls, canvas, document, *, title: str = "Documento AXIA") -> None:
        """Dibuja la plantilla antes del contenido en cada página."""
        canvas.saveState()
        width, height = document.pagesize

        if cls.BACKGROUND_PATH.exists():
            try:
                canvas.drawImage(
                    str(cls.BACKGROUND_PATH),
                    0,
                    0,
                    width=width,
                    height=height,
                    preserveAspectRatio=False,
                    mask="auto",
                )
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

        # Número de página sobre la franja inferior, sin duplicar datos del fondo.
        canvas.setFillColor(cls.TEXT)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawRightString(width - cls.RIGHT_MARGIN, 72, f"Página {document.page}")
        canvas.restoreState()

    @classmethod
    def styles(cls):
        base = getSampleStyleSheet()
        return {
            "normal": ParagraphStyle(
                "AxiaPdfNormal",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=7.4,
                leading=9.2,
                textColor=cls.TEXT,
            ),
            "title": ParagraphStyle(
                "AxiaPdfTitle",
                parent=base["Title"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=16,
                alignment=1,
                textColor=cls.PRIMARY,
                spaceAfter=2,
            ),
            "subtitle": ParagraphStyle(
                "AxiaPdfSubtitle",
                parent=base["Normal"],
                fontSize=7.2,
                leading=9,
                alignment=1,
                textColor=cls.TEXT,
            ),
            "section": ParagraphStyle(
                "AxiaPdfSection",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=8.7,
                leading=10.5,
                textColor=cls.PRIMARY,
            ),
            "table_header": ParagraphStyle(
                "AxiaPdfTableHeader",
                parent=base["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.0,
                leading=8.4,
                textColor=colors.white,
            ),
        }
