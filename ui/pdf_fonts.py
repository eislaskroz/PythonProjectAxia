"""Registro central de tipografía Poppins en los PDF de AXIA.

Se utiliza la fuente instalada en Windows. Si no está presente, ReportLab
conserva un tipo de letra de respaldo para evitar fallos de generación.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PDF_REGULAR = "Helvetica"
FONT_PDF_BOLD = "Helvetica-Bold"
FONT_PDF_SEMIBOLD = "Helvetica-Bold"


def _directories():
    app_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    return (app_root / "assets/fonts", local / "Microsoft/Windows/Fonts", windir / "Fonts")


def registrar_poppins():
    global FONT_PDF_REGULAR, FONT_PDF_BOLD, FONT_PDF_SEMIBOLD
    nombres = {"Poppins": "Poppins-Regular.ttf", "Poppins-Bold": "Poppins-Bold.ttf",
               "Poppins-SemiBold": "Poppins-SemiBold.ttf"}
    fuentes = {}
    for alias, archivo in nombres.items():
        ruta = next((folder / archivo for folder in _directories() if (folder / archivo).is_file()), None)
        if ruta is not None:
            fuentes[alias] = ruta
    if not {"Poppins", "Poppins-Bold"}.issubset(fuentes):
        return False
    try:
        for alias, ruta in fuentes.items():
            if alias not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(alias, str(ruta)))
        pdfmetrics.registerFontFamily("Poppins", normal="Poppins", bold="Poppins-Bold",
                                       italic="Poppins", boldItalic="Poppins-Bold")
        FONT_PDF_REGULAR = "Poppins"
        FONT_PDF_BOLD = "Poppins-Bold"
        FONT_PDF_SEMIBOLD = "Poppins-SemiBold" if "Poppins-SemiBold" in fuentes else "Poppins-Bold"
        return True
    except Exception:
        return False


registrar_poppins()
