from __future__ import annotations

from ui.pdf_fonts import FONT_PDF_REGULAR, FONT_PDF_BOLD

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
from reportlab.platypus import CondPageBreak, KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.logger import configurar_logger
from core.pdf.base_pdf import BasePdfGenerator

logger = configurar_logger(__name__)

BLUE = colors.HexColor("#1F4E79")
LIGHT_BLUE = colors.HexColor("#EAF1F7")
BORDER = colors.HexColor("#8FA3B5")
TEXT = colors.HexColor("#243447")
WHITE = colors.white


from ui.pdf_progress import con_progreso_pdf, progreso_pdf, dialogo_pdf

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


def _titulo_del_levantamiento(cotizacion: dict) -> str:
    if cotizacion.get("lev_descripcion"):
        return str(cotizacion["lev_descripcion"]).strip()
    id_lev = cotizacion.get("id_levantamiento")
    folio_lev = str(cotizacion.get("lev_folio") or "").strip()
    if id_lev in (None, "") and not folio_lev:
        return str(cotizacion.get("cot_asunto") or "").strip()
    try:
        from supabase_config import supabase
        consulta = supabase.table("db_levantamientos").select("lev_descripcion")
        if id_lev not in (None, ""):
            consulta = consulta.eq("id_levantamiento", id_lev)
        else:
            consulta = consulta.eq("lev_folio", folio_lev)
        respuesta = consulta.limit(1).execute()
        filas = respuesta.data or []
        if filas:
            titulo = str(filas[0].get("lev_descripcion") or "").strip()
            if titulo:
                return titulo
    except Exception:
        logger.exception("No se pudo consultar el nombre del servicio del levantamiento para la cotización")
    return str(cotizacion.get("cot_asunto") or "").strip()


@con_progreso_pdf
def generar_pdf_cotizacion(cotizacion: dict, ruta_salida: str | Path | None = None, abrir: bool = True, campos_visibles=None) -> Path:
    progreso_pdf("Generando cotización PDF…")
    cotizacion = dict(cotizacion or {})
    titulo_servicio = _titulo_del_levantamiento(cotizacion)
    if titulo_servicio:
        cotizacion["cot_asunto"] = titulo_servicio
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
        "AxiaCotNormal", parent=styles["normal"], fontName=FONT_PDF_REGULAR,
        fontSize=5.7, leading=6.7, textColor=TEXT,
    )
    label = ParagraphStyle(
        "AxiaCotLabel", parent=normal, fontName=FONT_PDF_BOLD,
        fontSize=5.65, leading=6.6,
    )
    header = ParagraphStyle(
        "AxiaCotHeader", parent=normal, fontName=FONT_PDF_BOLD,
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
    body_width = BasePdfGenerator.landscape_body_width(page_w)
    # Solo la primera sección evita el logo superior derecho; el resto mantiene el ancho completo.
    header_safe_width = body_width - 116
    story = []

    left_defs = [
        ("empresa", "NOMBRE", "AXIA COMUNICACIONES SA DE CV"),
        ("rfc", "RFC", "ACO1402056N2"),
        ("domicilio_axia", "DIRECCIÓN", "ÁLVARO OBREGÓN MZ 2 LT 3, SAN JUAN DE GUADALUPE, ZUMPANGO, ESTADO DE MÉXICO C.P. 55630"),
        ("esi", "ESI / EJECUTIVA DE VENTAS", cotizacion.get("cot_esi")),
        ("correo_esi", "CORREO ESI", cotizacion.get("cot_esi_correo")),
        ("telefono_esi", "TELÉFONO ESI", cotizacion.get("cot_esi_telefono")),
        ("jefe", "JEFE DE OPERACIONES", cotizacion.get("cot_jefe_operaciones")),
        ("supervisor", "SUPERVISOR", cotizacion.get("cot_supervisor")),
        ("dias", "DÍAS", cotizacion.get("cot_dias")),
        ("personas", "PERSONAS", cotizacion.get("cot_personas")),
    ]
    quote_defs = [
        ("fecha", "FECHA DE COTIZACIÓN", cotizacion.get("cot_fecha")),
        ("folio", "NO. COTIZACIÓN", folio),
        ("levantamiento", "NO. LEVANTAMIENTO", cotizacion.get("lev_folio")),
        ("cliente", "CLIENTE", cotizacion.get("cot_cliente")),
        ("contacto", "CONTACTO", cotizacion.get("cot_contacto")),
        ("sucursal", "SUCURSAL", cotizacion.get("cot_sucursal")),
        ("asunto", "TÍTULO / CONCEPTO", cotizacion.get("cot_asunto")),
        ("plan_pagos", "PLAN DE PAGOS", cotizacion.get("cot_plan_pagos") or "PPD"),
        ("vigencia", "VIGENCIA DE COTIZACIÓN", cotizacion.get("cot_vigencia")),
    ]

    def datos_compactos(definiciones, ancho):
        seleccionados = [(etiqueta, valor) for clave, etiqueta, valor in definiciones if ver(clave)]
        if not seleccionados:
            return None
        datos = []
        spans = []
        for i in range(0, len(seleccionados), 2):
            etiqueta, valor = seleccionados[i]
            fila = [p(etiqueta, label, ""), p(valor, normal, "")]
            if i + 1 < len(seleccionados):
                etiqueta2, valor2 = seleccionados[i + 1]
                fila += [p(etiqueta2, label, ""), p(valor2, normal, "")]
            else:
                fila += ["", ""]
                spans.append(len(datos))
            datos.append(fila)
        ancho_etiqueta = 0.16 * ancho
        ancho_valor = ancho / 2 - ancho_etiqueta
        t = Table(datos, colWidths=[ancho_etiqueta, ancho_valor] * 2, hAlign="LEFT")
        reglas = [
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
            ("BACKGROUND", (2, 0), (2, -1), LIGHT_BLUE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ]
        for n in spans:
            reglas.append(("SPAN", (1, n), (3, n)))
            reglas.append(("BACKGROUND", (2, n), (3, n), WHITE))
        t.setStyle(TableStyle(reglas))
        return t

    generales = datos_compactos(left_defs, header_safe_width)
    if generales is not None:
        story.append(section_title("Datos generales de cotización", header_safe_width))
        story.append(Spacer(1, 2))
        story.append(generales)
        story.append(Spacer(1, 3))

    comerciales = datos_compactos(quote_defs, body_width)
    if comerciales is not None:
        story.append(comerciales)
        story.append(Spacer(1, 4))
    if ver("partidas"):
        story.extend([section_title("Partidas de cotización", body_width), Spacer(1, 2)])

    partidas = cotizacion.get("cot_partidas_json") or []
    if isinstance(partidas, str):
        try:
            partidas = json.loads(partidas)
        except Exception:
            partidas = []
    partidas = partidas if isinstance(partidas, list) else []

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
        widths = [body_width * w / sum(weights) for w in weights]
        commercial = LongTable(table_data, colWidths=widths, repeatRows=1, splitByRow=1, hAlign="LEFT")
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
        story.append(commercial)

    totals_defs = [
        ("subtotal", "SUBTOTAL", _money(cotizacion.get("cot_subtotal"))),
        ("descuento", "DESCUENTO", f"{cotizacion.get('cot_descuento_pct', 0)}%"),
        ("subtotal_desc", "SUBTOTAL CON DESCUENTO", _money(cotizacion.get("cot_subtotal_descuento"))),
        ("iva", "IVA", f"{cotizacion.get('cot_iva_pct', 16)}% / {_money(cotizacion.get('cot_iva'))}"),
        ("total", "TOTAL", _money(cotizacion.get("cot_total"))),
    ]
    totals_rows = [[p(t, label, ""), p(v, label if k == "total" else normal, "")] for k, t, v in totals_defs if ver(k)]
    if ver("totales") and totals_rows:
        # El resumen económico conserva siempre su tamaño: ocultar columnas
        # de partidas no debe estirar ni desplazar esta tabla.
        totals = Table(totals_rows, colWidths=[1.65 * inch, 1.30 * inch], hAlign="RIGHT")
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
        # Protección 1: si el resumen ya no cabe limpio, se mueve completo a la siguiente hoja.
        estimated_totals_height = max(1.05 * inch, len(totals_rows) * 0.24 * inch + 0.22 * inch)
        story.append(CondPageBreak(estimated_totals_height))
        story.append(KeepTogether([Spacer(1, 1.5), totals]))
    if not story:
        story.append(Paragraph("Cotización sin campos seleccionados", normal))

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=landscape(letter),
        rightMargin=BasePdfGenerator.LANDSCAPE_SIDE_MARGIN,
        leftMargin=BasePdfGenerator.LANDSCAPE_SIDE_MARGIN,
        topMargin=92,  # Cotizaciones: inicia bajo el título, con el logo protegido por ancho reducido
        bottomMargin=BasePdfGenerator.LANDSCAPE_BOTTOM_MARGIN,
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