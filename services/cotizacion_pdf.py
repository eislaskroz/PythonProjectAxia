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
# P. Unitario | Importe | Observaciones (datos externos)

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


def generar_pdf_cotizacion(cotizacion: dict, ruta_salida: str | Path | None = None, abrir: bool = True, campos_visibles=None) -> Path:
    """Genera una cotización corporativa AXIA en Letter horizontal."""
    cotizacion = dict(cotizacion or {})
    folio = _txt(cotizacion.get("cot_folio"), "COT-BORRADOR")
    visibles = None if campos_visibles is None else set(campos_visibles)
    def ver(clave):
        return visibles is None or clave in visibles
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
    # El encabezado de sección se mantiene solo si existen campos generales.
    if visibles is None or any(ver(k) for k in ("empresa", "rfc", "domicilio_axia", "esi", "correo_esi", "telefono_esi", "jefe", "supervisor", "dias", "personas")):
        story.append(section_title("Datos generales de cotización", usable_width - 82))
        story.append(Spacer(1, 2))

    # Dos retículas paralelas conservan la estructura del formato proporcionado,
    # pero usando el lenguaje visual AXIA de celdas azules y fondo claro.
    left_defs = [
        ("empresa", "NOMBRE", "AXIA COMUNICACIONES SA DE CV"),
        ("rfc", "RFC", "ACO1402056N2"),
        ("domicilio_axia", "DIRECCIÓN", "ÁLVARO OBREGÓN MZ 2 LT 3, SAN JUAN DE GUADALUPE, ZUMPANGO, ESTADO DE MÉXICO C.P. 55630"),
        ("esi", "ESI / EJECUTIVA DE VENTAS", cotizacion.get("cot_esi")),
        ("correo_esi", "CORREO ESI", cotizacion.get("cot_esi_correo")),
        ("telefono_esi", "TELÉFONO ESI", cotizacion.get("cot_esi_telefono")),
    ]
    right_defs = [
        ("jefe", "JEFE DE OPERACIONES", cotizacion.get("cot_jefe_operaciones")),
        ("supervisor", "SUPERVISOR", cotizacion.get("cot_supervisor")),
        ("dias", "DÍAS", cotizacion.get("cot_dias")),
        ("personas", "PERSONAS", cotizacion.get("cot_personas")),
    ]
    left_rows = [[p(t, label, ""), p(v, normal, "")] for k, t, v in left_defs if ver(k)]
    right_rows = [[p(t, label, ""), p(v, normal, "")] for k, t, v in right_defs if ver(k)]

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

    # Reservar esquina de logo AXIA aun cuando se oculten filas.
    if left_rows or right_rows:
        left = info_table(left_rows, [1.45*inch, 3.95*inch]) if left_rows else Spacer(1, 1)
        right = info_table(right_rows, [1.45*inch, 1.75*inch]) if right_rows else Spacer(1, 1)
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
    quote_defs = [
        ("fecha", "FECHA DE COTIZACIÓN", cotizacion.get("cot_fecha")),
        ("folio", "NO. COTIZACIÓN", folio),
        ("levantamiento", "NO. LEVANTAMIENTO", cotizacion.get("lev_folio")),
        ("cliente", "CLIENTE", cotizacion.get("cot_cliente")),
        ("contacto", "CONTACTO", cotizacion.get("cot_contacto")),
        ("sucursal", "SUCURSAL", cotizacion.get("cot_sucursal")),
        ("asunto", "TÍTULO / CONCEPTO", cotizacion.get("cot_asunto")),
    ]
    terms_defs = [
        ("plan_pagos", "PLAN DE PAGOS", cotizacion.get("cot_plan_pagos") or "PPD"),
        ("vigencia", "VIGENCIA DE COTIZACIÓN", cotizacion.get("cot_vigencia")),
    ]
    quote_rows = [[p(t, label, ""), p(v, normal, "")] for k, t, v in quote_defs if ver(k)]
    terms_rows = [[p(t, label, ""), p(v, normal, "")] for k, t, v in terms_defs if ver(k)]
    if quote_rows or terms_rows:
        quote = info_table(quote_rows, [1.45*inch, 3.95*inch]) if quote_rows else Spacer(1, 1)
        terms = info_table(terms_rows, [1.55*inch, 2.65*inch]) if terms_rows else Spacer(1, 1)
        quote_grid = Table([[quote, terms]], colWidths=[5.55*inch, 4.65*inch], hAlign="LEFT")
        quote_grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.extend([quote_grid, Spacer(1, 4)])
    if ver("partidas"):
        story.extend([section_title("Partidas de cotización", usable_width), Spacer(1, 2)])

    partidas = cotizacion.get("cot_partidas_json") or []
    if isinstance(partidas, str):
        try:
            partidas = json.loads(partidas)
        except Exception:
            partidas = []
    partidas = partidas if isinstance(partidas, list) else []

    # Sólo se muestran las columnas seleccionadas; nunca expone costos internos.
    columnas = [
        ("lote", "LOTE", "lote", 0.40),
        ("unidad", "UNIDAD / TIPO", "unidad_tipo", 0.84),
        ("cantidad", "CANT.", "cantidad", 0.45),
        ("modelo", "MODELO", "modelo", 0.78),
        ("sku", "SKU", "sku", 0.64),
        ("marca", "MARCA", "marca", 0.65),
        ("concepto", "CONCEPTO", "concepto", 2.45),
        ("precio_unitario", "P. UNIT.", "precio_unitario", 0.87),
        ("importe", "IMPORTE", "importe", 0.90),
        ("observaciones", "OBSERVACIONES", "observaciones", 1.40),
    ]
    columnas = [(key, t, field, width) for key, t, field, width in columnas if ver(key)]
    if ver("partidas") and columnas:
        table_data = [[Paragraph(t, header) for _, t, _, _ in columnas]]
        for item in partidas:
            row = []
            for key, _, field, _ in columnas:
                value = _money(item.get(field)) if key in {"precio_unitario", "importe"} else item.get(field)
                row.append(p(value, row_center if key in {"lote", "cantidad", "precio_unitario", "importe"} else row_style, ""))
            table_data.append(row)
        if len(table_data) == 1:
            table_data.append([p("", row_style, "")] * len(columnas))
        weights = [c[3] for c in columnas]
        widths = [usable_width * w / sum(weights) for w in weights]
        commercial = LongTable(table_data, colWidths=widths, repeatRows=1, splitByRow=1)
        commercial.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2.2),
            ("TOPPADDING", (0, 0), (-1, -1), 1.4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ]))
        story.extend([commercial, Spacer(1, 4)])

    totals_defs = [
        ("subtotal", "SUBTOTAL", _money(cotizacion.get("cot_subtotal"))),
        ("descuento", "DESCUENTO", f"{cotizacion.get('cot_descuento_pct', 0)}%"),
        ("subtotal_desc", "SUBTOTAL CON DESCUENTO", _money(cotizacion.get("cot_subtotal_descuento"))),
        ("iva", "IVA", f"{cotizacion.get('cot_iva_pct', 16)}% / {_money(cotizacion.get('cot_iva'))}"),
        ("total", "TOTAL", _money(cotizacion.get("cot_total"))),
    ]
    totals_rows = [[p(t, label, ""), p(v, label if k == "total" else normal, "")] for k, t, v in totals_defs if ver(k)]
    if ver("totales") and totals_rows:
        totals = Table(totals_rows, colWidths=[1.55*inch, 1.45*inch], hAlign="RIGHT")
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
    if not story:
        story.append(Paragraph("Cotización sin campos seleccionados", normal))

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
