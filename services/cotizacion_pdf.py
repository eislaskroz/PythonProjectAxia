"""PDF comercial de cotización con identidad visual del AXIA PDF Engine.

La cotización mantiene la misma jerarquía, paleta, retícula, fondo corporativo
y comportamiento multipágina de Levantamientos, OT, OS y Bitácoras, usando
Letter horizontal únicamente por la cantidad de columnas comerciales.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from html import escape as html_escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.logger import configurar_logger
from core.pdf.base_pdf import BasePdfGenerator

logger = configurar_logger(__name__)

# Etiquetas históricas del formato comercial conservadas por compatibilidad:
# No. Cotización | No. Levantamiento | Plan de Pagos | Vigencia de Cotización
# Proveedor | P. Lista | Utilidad | P. Venta | P. Unitario | Observaciones

BLUE = colors.HexColor("#1F4E79")
LIGHT_BLUE = colors.HexColor("#EAF1F7")
BORDER = colors.HexColor("#8FA3B5")
TEXT = colors.HexColor("#243447")
WHITE = colors.white


def _txt(value: Any, fallback: str = "-") -> str:
    value = str(value or "").strip()
    return value or fallback


def _money(value: Any) -> str:
    try:
        return f"${float(value or 0):,.2f}"
    except Exception:
        return "$0.00"


def _open(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif os.uname().sysname == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        logger.exception("No fue posible abrir el PDF de cotización.")


def generar_pdf_cotizacion(cotizacion: dict, ruta_salida: str | Path | None = None, abrir: bool = True) -> Path:
    """Genera una cotización corporativa AXIA en Letter horizontal."""
    cotizacion = dict(cotizacion or {})
    folio = _txt(cotizacion.get("cot_folio"), "COT-BORRADOR")
    if ruta_salida:
        destino = Path(ruta_salida)
    else:
        carpeta = Path(tempfile.gettempdir()) / "AXIA" / "cotizaciones"
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / f"AXIA_{folio}.pdf"
    destino.parent.mkdir(parents=True, exist_ok=True)

    styles = BasePdfGenerator.styles()
    normal = ParagraphStyle(
        "AxiaCotNormal", parent=styles["normal"], fontName="Helvetica",
        fontSize=6.6, leading=8.0, textColor=TEXT,
    )
    label = ParagraphStyle(
        "AxiaCotLabel", parent=normal, fontName="Helvetica-Bold",
        fontSize=6.5, leading=7.8,
    )
    header = ParagraphStyle(
        "AxiaCotHeader", parent=normal, fontName="Helvetica-Bold",
        fontSize=5.8, leading=6.6, textColor=WHITE, alignment=1,
    )
    row_style = ParagraphStyle(
        "AxiaCotRow", parent=normal, fontSize=5.05, leading=5.8,
    )
    row_center = ParagraphStyle(
        "AxiaCotRowCenter", parent=row_style, alignment=1,
    )

    def p(value: Any, style=normal, fallback: str = "-") -> Paragraph:
        return Paragraph(html_escape(_txt(value, fallback)), style)

    def section_title(title: str, width: float) -> Table:
        t = Table([[Paragraph(html_escape(title.upper()), styles["table_header"])]], colWidths=[width], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BLUE),
            ("BOX", (0, 0), (-1, -1), 0.5, BLUE),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    page_w, _page_h = landscape(letter)
    usable_width = page_w - 56  # 28 pt por lado
    story = []

    # El título documental lo dibuja BasePdfGenerator. No repetimos folio, fecha
    # ni levantamiento debajo del título; esos datos viven en la retícula formal
    # de la cotización, igual que en el formato comercial de referencia.
    story.append(section_title("Datos generales de cotización", usable_width - 82))
    story.append(Spacer(1, 2))

    # Dos retículas paralelas conservan la estructura del formato proporcionado,
    # pero usando el lenguaje visual AXIA de celdas azules y fondo claro.
    left_rows = [
        [p("NOMBRE", label, ""), p("AXIA COMUNICACIONES SA DE CV", normal, "")],
        [p("RFC", label, ""), p("ACO1402056N2", normal, "")],
        [p("DIRECCIÓN", label, ""), p("ÁLVARO OBREGÓN MZ 2 LT 3, SAN JUAN DE GUADALUPE, ZUMPANGO, ESTADO DE MÉXICO C.P. 55630", normal, "")],
        [p("ESI / EJECUTIVA DE VENTAS", label, ""), p(cotizacion.get("cot_esi"), normal, "")],
        [p("CORREO ESI", label, ""), p(cotizacion.get("cot_esi_correo"), normal, "")],
        [p("TELÉFONO ESI", label, ""), p(cotizacion.get("cot_esi_telefono"), normal, "")],
    ]
    right_rows = [
        [p("JEFE DE OPERACIONES", label, ""), p(cotizacion.get("cot_jefe_operaciones"), normal, "")],
        [p("SUPERVISOR", label, ""), p(cotizacion.get("cot_supervisor"), normal, "")],
        [p("DÍAS", label, ""), p(cotizacion.get("cot_dias"), normal, "")],
        [p("PERSONAS", label, ""), p(cotizacion.get("cot_personas"), normal, "")],
    ]

    def info_table(rows, widths):
        t = Table(rows, colWidths=widths)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
            ("BACKGROUND", (1, 0), (1, -1), WHITE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        return t

    left = info_table(left_rows, [1.45*inch, 3.95*inch])
    right = info_table(right_rows, [1.45*inch, 1.75*inch])
    # El bloque superior reserva físicamente la esquina derecha para el logo
    # corporativo del fondo horizontal; ningún dato puede quedar debajo de él.
    top_grid = Table([[left, right]], colWidths=[5.55*inch, 3.25*inch], hAlign="LEFT")
    top_grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.extend([top_grid, Spacer(1, 3)])

    # Segunda retícula: fecha, folios y datos del cliente a la izquierda;
    # condiciones comerciales a la derecha. Esta disposición replica el flujo
    # visual del formato proporcionado sin duplicar el folio en el encabezado.
    quote_rows = [
        [p("FECHA DE COTIZACIÓN", label, ""), p(cotizacion.get("cot_fecha"), normal, "")],
        [p("NO. COTIZACIÓN", label, ""), p(folio, normal, "")],
        [p("NO. LEVANTAMIENTO", label, ""), p(cotizacion.get("lev_folio"), normal, "")],
        [p("CLIENTE", label, ""), p(cotizacion.get("cot_cliente"), normal, "")],
        [p("CONTACTO", label, ""), p(cotizacion.get("cot_contacto"), normal, "")],
        [p("SUCURSAL", label, ""), p(cotizacion.get("cot_sucursal"), normal, "")],
        [p("ASUNTO", label, ""), p(cotizacion.get("cot_asunto"), normal, "")],
    ]
    quote = info_table(quote_rows, [1.45*inch, 3.95*inch])

    terms_rows = [
        [p("PLAN DE PAGOS", label, ""), p(cotizacion.get("cot_plan_pagos"), normal, "")],
        [p("VIGENCIA DE COTIZACIÓN", label, ""), p(cotizacion.get("cot_vigencia"), normal, "")],
    ]
    terms = info_table(terms_rows, [1.55*inch, 2.65*inch])
    quote_grid = Table([[quote, terms]], colWidths=[5.55*inch, 4.65*inch], hAlign="LEFT")
    quote_grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.extend([quote_grid, Spacer(1, 4), section_title("Partidas de cotización", usable_width), Spacer(1, 2)])

    partidas = cotizacion.get("cot_partidas_json") or []
    if isinstance(partidas, str):
        try:
            partidas = json.loads(partidas)
        except Exception:
            partidas = []
    partidas = partidas if isinstance(partidas, list) else []

    headers = ["LOTE", "UNIDAD / TIPO", "CANT.", "PROVEEDOR", "MODELO", "SKU", "MARCA", "CONCEPTO", "P. LISTA", "COSTO", "UTILIDAD", "P. VENTA", "P. UNIT.", "IMPORTE", "OBSERVACIONES"]
    table_data = [[Paragraph(h, header) for h in headers]]
    for item in partidas:
        table_data.append([
            p(item.get("lote"), row_center, ""),
            p(item.get("unidad_tipo"), row_center, ""),
            p(item.get("cantidad"), row_center, ""),
            p(item.get("proveedor"), row_style, ""),
            p(item.get("modelo"), row_style, ""),
            p(item.get("sku"), row_style, ""),
            p(item.get("marca"), row_style, ""),
            p(item.get("concepto"), row_style, ""),
            p(_money(item.get("precio_lista")), row_center, ""),
            p(_money(item.get("costo")), row_center, ""),
            p(f"{item.get('utilidad_pct', 0)}%", row_center, ""),
            p(_money(item.get("precio_venta")), row_center, ""),
            p(_money(item.get("precio_unitario")), row_center, ""),
            p(_money(item.get("importe")), row_center, ""),
            p(item.get("observaciones"), row_style, ""),
        ])
    if len(table_data) == 1:
        table_data.append([p("", row_style, "")] * len(headers))

    widths = [0.33, 0.68, 0.42, 0.68, 0.62, 0.42, 0.48, 1.38, 0.57, 0.57, 0.50, 0.58, 0.58, 0.62, 0.87]
    widths = [x*inch for x in widths]
    commercial = LongTable(table_data, colWidths=widths, repeatRows=1, splitByRow=1)
    commercial.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (2, -1), "CENTER"),
        ("ALIGN", (8, 1), (13, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
    ]))
    story.extend([commercial, Spacer(1, 4)])

    totals = Table([
        [p("SUBTOTAL", label, ""), p(_money(cotizacion.get("cot_subtotal")), normal, "")],
        [p("DESCUENTO", label, ""), p(f"{cotizacion.get('cot_descuento_pct', 0)}%", normal, "")],
        [p("SUBTOTAL CON DESCUENTO", label, ""), p(_money(cotizacion.get("cot_subtotal_descuento")), normal, "")],
        [p("IVA", label, ""), p(f"{cotizacion.get('cot_iva_pct', 16)}% / {_money(cotizacion.get('cot_iva'))}", normal, "")],
        [p("TOTAL", label, ""), p(_money(cotizacion.get("cot_total")), label, "")],
    ], colWidths=[1.55*inch, 1.45*inch], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
        ("BACKGROUND", (1, -1), (1, -1), colors.HexColor("#EAF7FB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(totals)

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=landscape(letter),
        rightMargin=28,
        leftMargin=28,
        topMargin=90,
        bottomMargin=62,
        title=f"AXIA - Cotización {folio}",
        author="AXIA Comunicaciones S.A. de C.V.",
        subject="Cotización Comercial",
        creator="Sistema AXIA",
    )

    def _on_page(canvas, document):
        BasePdfGenerator.draw_page(canvas, document, title="Cotización")

    try:
        doc.build(
            story,
            onFirstPage=_on_page,
            onLaterPages=_on_page,
            canvasmaker=BasePdfGenerator.canvas_factory("Cotización"),
        )
    except Exception:
        logger.exception("Error generando PDF corporativo de cotización.")
        raise

    if abrir:
        _open(destino)
    return destino
