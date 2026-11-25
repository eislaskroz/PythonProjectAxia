from __future__ import annotations

from ui.pdf_fonts import FONT_PDF_REGULAR, FONT_PDF_BOLD

from core.logger import configurar_logger

logger = configurar_logger(__name__)

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas

from core.version import APP_VERSION


class BasePdfGenerator:

    PRIMARY = colors.HexColor("#0B324A")
    SECONDARY = colors.HexColor("#00BCEB")
    BORDER = colors.HexColor("#B8C2CC")
    LIGHT = colors.HexColor("#F4F8FB")
    TEXT = colors.HexColor("#243447")

    ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
    BACKGROUND_PATH = ASSETS_DIR / "FormatoFondo.png"
    BACKGROUND_LANDSCAPE_PATH = ASSETS_DIR / "FormatoFondoHorizontal.png"

    LEFT_MARGIN = 34
    RIGHT_MARGIN = 34
    TOP_MARGIN = 96
    BOTTOM_MARGIN = 78

    LANDSCAPE_SIDE_MARGIN = 28
    LANDSCAPE_TOP_MARGIN = 146
    LANDSCAPE_BOTTOM_MARGIN = 62
    FRAME_PADDING = 6

    @classmethod
    def landscape_body_width(cls, page_width=792):
        return page_width - 2 * cls.LANDSCAPE_SIDE_MARGIN - 2 * cls.FRAME_PADDING

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
        canvas.saveState()
        width, height = document.pagesize

        background_path = cls.BACKGROUND_LANDSCAPE_PATH if width > height else cls.BACKGROUND_PATH
        if background_path.exists():
            try:
                canvas.drawImage(
                    str(background_path),
                    0,
                    0,
                    width=width,
                    height=height,
                    preserveAspectRatio=False,
                    mask="auto",
                )
            except Exception:
                logger.debug("Excepción recuperable controlada.", exc_info=True)

        title_key = str(title or "").strip().casefold()
        visible_title = None
        if title_key.startswith("levantamiento"):
            visible_title = "LEVANTAMIENTOS"
        elif title_key in {"orden de trabajo", "órden de trabajo", "ordenes de trabajo", "órdenes de trabajo"}:
            visible_title = "ÓRDENES DE TRABAJO"
        elif title_key in {"bitácora de avance", "bitacora de avance", "bitácoras de avance", "bitacoras de avance"}:
            visible_title = "BITÁCORA DE AVANCE"
        elif title_key in {"cotización", "cotizacion", "cotizaciones"}:
            visible_title = "COTIZACIÓN"

        if visible_title:
            canvas.setFillColor(cls.PRIMARY)
            canvas.setFont(FONT_PDF_BOLD, 13)
            canvas.drawCentredString(width / 2, height - 88, visible_title)

        canvas.setFillColor(cls.TEXT)
        canvas.setFont(FONT_PDF_REGULAR, 6.5)
        if width > height:
            canvas.setFillColor(colors.white)
            canvas.setFont(FONT_PDF_BOLD, 6.2)
            canvas.drawString(33, 18, "55-49-89-34-64")
            canvas.drawString(150, 18, "www.axiacomunicaciones.com")
            canvas.drawString(345, 18, "Álvaro Obregón Manzana 2, Lote 3 - 55630 San Juan de Guadalupe, Méx.")
            canvas.setFillColor(cls.TEXT)
            canvas.setFont(FONT_PDF_REGULAR, 6.5)
            canvas.drawRightString(width - cls.RIGHT_MARGIN, 62, f"Página {document.page}")
        else:
            canvas.drawRightString(width - cls.RIGHT_MARGIN, 72, f"Página {document.page}")
        canvas.restoreState()

    @classmethod
    def styles(cls):
        base = getSampleStyleSheet()
        return {
            "normal": ParagraphStyle(
                "AxiaPdfNormal",
                parent=base["Normal"],
                fontName=FONT_PDF_REGULAR,
                fontSize=7.4,
                leading=9.2,
                textColor=cls.TEXT,
            ),
            "title": ParagraphStyle(
                "AxiaPdfTitle",
                parent=base["Title"],
                fontName=FONT_PDF_BOLD,
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
                fontName=FONT_PDF_BOLD,
                fontSize=8.7,
                leading=10.5,
                textColor=cls.PRIMARY,
            ),
            "table_header": ParagraphStyle(
                "AxiaPdfTableHeader",
                parent=base["Normal"],
                fontName=FONT_PDF_BOLD,
                fontSize=7.0,
                leading=8.4,
                textColor=colors.white,
            ),
        }