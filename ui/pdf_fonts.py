"""Fuentes obligatorias e incrustadas para todos los PDF generados por AXIA."""
from __future__ import annotations
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from ui.font_runtime import ensure_poppins

FONT_PDF_REGULAR = "Poppins"
FONT_PDF_MEDIUM = "Poppins-Medium"
FONT_PDF_BOLD = "Poppins-Bold"
FONT_PDF_SEMIBOLD = "Poppins-SemiBold"


def registrar_poppins():
    folder = ensure_poppins()
    names = {
        "Poppins": "Poppins-Regular.ttf",
        "Poppins-Medium": "Poppins-Medium.ttf",
        "Poppins-SemiBold": "Poppins-SemiBold.ttf",
        "Poppins-Bold": "Poppins-Bold.ttf",
        "Poppins-Italic": "Poppins-Italic.ttf",
        "Poppins-BoldItalic": "Poppins-BoldItalic.ttf",
    }
    for name, filename in names.items():
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(folder / filename)))
    pdfmetrics.registerFontFamily(
        "Poppins", normal="Poppins", bold="Poppins-Bold",
        italic="Poppins-Italic", boldItalic="Poppins-BoldItalic",
    )
    return True

registrar_poppins()
