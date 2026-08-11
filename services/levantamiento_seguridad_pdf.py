"""Plantilla maestra PDF para Seguridad y Monitoreo / Instalación.

Primera migración del nuevo esquema visual de levantamientos AXIA. La plantilla
trabaja directamente con el mismo registro que se persiste en Supabase y usa
bloques/tablas dinámicas que crecen y paginan sin recortar información.
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.pdf import BasePdfGenerator


BLUE = colors.HexColor("#1F4E79")
LIGHT_BLUE = colors.HexColor("#EAF1F7")
LIGHT = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#8FA3B5")
TEXT = colors.HexColor("#243447")
WHITE = colors.white


def _json(value: Any, default: Any = None) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if text and text[:1] in "[{":
            try:
                return json.loads(text)
            except Exception:
                return default if default is not None else value
    return value if value not in (None, "") else (default if default is not None else value)


def _text(value: Any, fallback: str = "-") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _p(value: Any, style, fallback: str = "-") -> Paragraph:
    return Paragraph(escape(_text(value, fallback)), style)


def _detail(registro: Mapping[str, Any]) -> dict[str, Any]:
    value = _json(registro.get("lev_detalle_tecnico_json"), {})
    return dict(value) if isinstance(value, Mapping) else {}


def es_seguridad_instalacion(registro: Mapping[str, Any]) -> bool:
    tipo = str(registro.get("lev_tipo_levantamiento") or "").strip().casefold()
    modalidad = str(registro.get("lev_modalidad_operativa") or "").strip().casefold()
    if not tipo:
        detalle = _detail(registro)
        tipo = str(detalle.get("tipo_levantamiento") or "").strip().casefold()
        modalidad = modalidad or str(detalle.get("modalidad_operativa") or "").strip().casefold()
    return tipo == "seguridad y monitoreo" and modalidad in {"instalación", "instalacion"}


def _section_title(title: str, width: float, header_style) -> Table:
    table = Table([[Paragraph(escape(title.upper()), header_style)]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("BOX", (0, 0), (-1, -1), 0.5, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _key_value_table(rows: Sequence[Sequence[Any]], widths: Sequence[float], normal, label) -> Table:
    data = []
    for row in rows:
        converted = []
        for idx, value in enumerate(row):
            converted.append(_p(value, label if idx % 2 == 0 else normal, ""))
        data.append(converted)
    table = Table(data, colWidths=list(widths))
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
    ]))
    # Suave diferenciación visual de columnas de etiqueta.
    for col in range(0, len(widths), 2):
        table.setStyle(TableStyle([("BACKGROUND", (col, 0), (col, -1), LIGHT_BLUE)]))
    return table


def _matrix_table(headers: Sequence[str], rows: Sequence[Sequence[Any]], widths: Sequence[float], normal, table_header) -> LongTable:
    data = [[Paragraph(escape(str(h)), table_header) for h in headers]]
    for row in rows:
        data.append([_p(value, normal, "") for value in row])
    table = LongTable(data, colWidths=list(widths), repeatRows=1, splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return table



def _section_matrix_table(title: str, headers: Sequence[str], rows: Sequence[Sequence[Any]], widths: Sequence[float], normal, table_header) -> LongTable:
    """Tabla dinámica cuyo título viaja con la propia tabla.

    Evita títulos huérfanos al final de página y repite título + encabezados cuando
    una tabla continúa en páginas posteriores.
    """
    total_cols = len(headers)
    data = [[Paragraph(escape(str(title).upper()), table_header)] + [""] * (total_cols - 1)]
    data.append([Paragraph(escape(str(h)), table_header) for h in headers])
    for row in rows:
        data.append([_p(value, normal, "") for value in row])
    table = LongTable(data, colWidths=list(widths), repeatRows=2, splitByRow=1)
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 1), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 1), WHITE),
        ("GRID", (0, 1), (-1, -1), 0.45, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return table

def _description_table(text: str, width: float, normal, table_header) -> LongTable:
    """Descripción con borde y paginación segura.

    Se fragmenta por párrafos y tamaño máximo para que una sola celda nunca sea
    más alta que el marco disponible de ReportLab.
    """
    chunks: list[str] = []
    source = str(text or "").strip() or "Sin descripción capturada."
    # Evita títulos duplicados cuando un registro histórico ya contiene la leyenda
    # dentro del propio texto. El título visual lo aporta únicamente esta tabla.
    cleaned_lines = []
    for line in source.splitlines():
        normalized = line.strip().strip("- ").casefold()
        if normalized in {
            "descripción detallada del servicio",
            "descripcion detallada del servicio",
        }:
            continue
        cleaned_lines.append(line)
    source = "\n".join(cleaned_lines).strip() or "Sin descripción capturada."
    for paragraph in source.splitlines() or [source]:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        while len(paragraph) > 900:
            cut = paragraph.rfind(" ", 0, 900)
            if cut < 300:
                cut = 900
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        if paragraph:
            chunks.append(paragraph)
    data = [[Paragraph("DESCRIPCIÓN DETALLADA DEL SERVICIO", table_header)]]
    data.extend([[_p(chunk, normal, "")]] for chunk in chunks)
    table = LongTable(data, colWidths=[width], repeatRows=0, splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ]))
    return table


def generar_pdf_seguridad_instalacion(
    registro: Mapping[str, Any],
    *,
    ruta_salida: str | Path,
    abrir: bool = False,
) -> str:
    """Genera el nuevo formato maestro de Seguridad y Monitoreo / Instalación."""
    import os

    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    styles = BasePdfGenerator.styles()
    normal = styles["normal"]
    header = styles["table_header"]
    section_header = styles["table_header"]
    # Etiqueta compacta, compatible con Paragraph.
    from reportlab.lib.styles import ParagraphStyle
    label = ParagraphStyle(
        "AxiaMasterLabel",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=7.0,
        leading=8.4,
        textColor=BasePdfGenerator.PRIMARY,
    )

    detail = _detail(registro)
    infra = dict(detail.get("infraestructura_existente") or {})
    rack = dict(detail.get("rack_gabinete_energia") or {})
    access = dict(detail.get("acceso_alturas_riesgos") or {})
    cctv = dict(detail.get("datos_tecnicos_cctv") or {})

    canalizacion = detail.get("canalizacion_materiales") or []
    if not isinstance(canalizacion, (list, tuple)):
        canalizacion = []
    equipos = detail.get("equipos_principales") or []
    if not isinstance(equipos, (list, tuple)):
        equipos = []
    materiales = detail.get("materiales_miscelaneos") or []
    if not isinstance(materiales, (list, tuple)):
        materiales = []

    width = 6.90 * inch
    doc = SimpleDocTemplate(
        str(ruta),
        pagesize=(612, 792),
        rightMargin=BasePdfGenerator.RIGHT_MARGIN,
        leftMargin=BasePdfGenerator.LEFT_MARGIN,
        topMargin=BasePdfGenerator.TOP_MARGIN,
        bottomMargin=BasePdfGenerator.BOTTOM_MARGIN,
    )
    story = []

    # 1) Datos generales - estructura equivalente al formato de referencia.
    general_rows = [
        ["NOMBRE DE LEVANTAMIENTO", registro.get("lev_tipo_levantamiento") or "Seguridad y Monitoreo",
         "FOLIO LEVANTAMIENTO", registro.get("lev_folio") or "Pendiente"],
        ["CLIENTE", registro.get("lev_cliente"), "FECHA", registro.get("lev_fecha_programada") or registro.get("fecha_registro")],
        ["DIRECCIÓN", registro.get("lev_direccion"), "CONTACTO", registro.get("lev_contacto")],
        ["TÉCNICO AXIA", registro.get("lev_tecnico"), "SUPERVISOR", registro.get("lev_supervisor")],
        ["CORREO", registro.get("lev_correo"), "TIPO DE TRABAJO", registro.get("lev_modalidad_operativa") or "Instalación"],
    ]
    story.append(_key_value_table(general_rows, [1.35*inch, 2.75*inch, 1.18*inch, 1.62*inch], normal, label))

    # Recursos estimados: inmediatamente debajo de los datos generales.
    resource_table = _key_value_table([
        ["Días de trabajo", cctv.get("dias_trabajo"), "Personas a considerar", cctv.get("personas_considerar")],
    ], [1.35*inch, 1.0*inch, 1.75*inch, 2.80*inch], normal, label)
    story.append(resource_table)
    story.append(Spacer(1, 7))

    # 2) Infraestructura existente y rack/energía en paralelo.
    left = _key_value_table([
        ["Existe infraestructura", infra.get("existe_infraestructura")],
        ["Tipo de infraestructura", infra.get("tipo_infraestructura_existente") or "No aplica"],
        ["Estado general", infra.get("estado_general") or "No aplica"],
    ], [1.55*inch, 1.70*inch], normal, label)
    right_rows = [
        ["Rack", rack.get("rack_requerido"), rack.get("tipo_rack") or "No aplica"],
        ["Gabinete", rack.get("gabinete_requerido"), rack.get("tipo_gabinete") or "No aplica"],
        ["UPS", rack.get("ups_requerida"), rack.get("tipo_ups") or "No aplica"],
        ["Contacto regulado", rack.get("contacto_regulado"), rack.get("detalle_contacto_regulado") or "No aplica"],
        ["Tierra física", rack.get("tierra_fisica"), rack.get("detalle_tierra_fisica") or "No aplica"],
    ]
    right_data = [[_p(a, label, ""), _p(b, normal, ""), _p(c, normal, "")] for a,b,c in right_rows]
    right = Table(right_data, colWidths=[1.25*inch, .72*inch, 1.38*inch])
    right.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), .45, BORDER),
        ("BACKGROUND", (0,0), (0,-1), LIGHT_BLUE),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 2.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
    ]))
    pair = Table([[left, right]], colWidths=[3.35*inch, 3.45*inch])
    pair.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0)]))
    story.append(pair)
    story.append(Spacer(1, 6))

    # 3) Acceso, alturas y riesgos.
    access_rows = [[
        "¿Se requiere escalera/andamio?", access.get("escalera_andamio"),
        "Altura", access.get("altura_trabajo") or "No aplica",
        "Riesgo", access.get("riesgo_instalacion") or "No aplica",
    ]]
    access_table = Table([[ _p(v, label if i in (0,2,4) else normal, "") for i,v in enumerate(access_rows[0]) ]],
                         colWidths=[1.65*inch, .62*inch, .62*inch, .85*inch, .62*inch, 2.54*inch])
    access_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), .45, BORDER), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (0,0), LIGHT_BLUE), ("BACKGROUND", (2,0), (2,0), LIGHT_BLUE),
        ("BACKGROUND", (4,0), (4,0), LIGHT_BLUE),
        ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 2.5), ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
    ]))
    story.append(access_table)
    story.append(Spacer(1, 6))

    # 4) Datos técnicos CCTV.
    cctv_headers = ["¿Cuántas cámaras?", "¿Tipo de cámaras?", "Ubicación NVR/DVR", "Punto de enlace de red", "Punto de energía"]
    cctv_rows = [[
        cctv.get("cantidad_camaras"), cctv.get("tipo_camaras"), cctv.get("ubicacion_nvr_dvr"),
        cctv.get("punto_red"), cctv.get("punto_energia")
    ]]
    story.append(_matrix_table(cctv_headers, cctv_rows, [1.0*inch,1.15*inch,1.45*inch,1.65*inch,1.65*inch], normal, header))
    story.append(Spacer(1, 6))

    # 5) Canalización dinámica.
    requires = "Sí" if canalizacion else "No"
    story.append(_key_value_table([["¿Se requiere canalización?", requires]], [1.8*inch, .85*inch], normal, label))
    if canalizacion:
        story.append(Spacer(1, 5))
        rows = []
        for item in canalizacion:
            if not isinstance(item, Mapping):
                continue
            rows.append([
                item.get("categoria"), item.get("tipo"), item.get("tamano_calibre_especificacion") or "No aplica",
                item.get("cantidad"), item.get("unidad")
            ])
        if rows:
            story.append(_matrix_table(
                ["Categoría", "Tipo", "Tamaño/Calibre", "Cantidad", "Unidad"], rows,
                [1.05*inch, 2.35*inch, 1.55*inch, .88*inch, 1.07*inch], normal, header
            ))
    story.append(Spacer(1, 7))

    # 6) Equipos principales: aparece únicamente cuando hay registros.
    equipment_rows = []
    for item in equipos:
        if isinstance(item, Mapping):
            equipment_rows.append([
                item.get("familia"), item.get("subfamilia"), item.get("cantidad"), item.get("marca"),
                item.get("modelo"), item.get("caracteristicas")
            ])
    if equipment_rows:
        story.append(_section_matrix_table(
            "Equipos principales requeridos",
            ["Familia", "Subfamilia", "Cantidad", "Marca", "Modelo", "Características técnicas"],
            equipment_rows,
            [1.05*inch,1.15*inch,.65*inch,.95*inch,.95*inch,2.15*inch], normal, header
        ))
        story.append(Spacer(1, 7))

    # 7) Materiales misceláneos: aparece únicamente cuando hay registros.
    material_rows = []
    for item in materiales:
        if isinstance(item, Mapping):
            material_rows.append([
                item.get("material"), item.get("cantidad"), item.get("unidad"), item.get("especificacion")
            ])
    if material_rows:
        story.append(_section_matrix_table(
            "Materiales misceláneos y consumibles",
            ["Material", "Cantidad", "Unidad", "Especificación/Medida"], material_rows,
            [2.15*inch,.9*inch,1.0*inch,2.85*inch], normal, header
        ))
        story.append(Spacer(1, 7))

    # 8) Descripción final dinámica.
    description = registro.get("lev_observaciones") or registro.get("lev_descripcion") or ""
    story.append(_description_table(str(description), width, normal, header))

    title = "Levantamiento Seguridad y Monitoreo - Instalación"
    doc.title = f"AXIA - {title}"
    doc.author = "AXIA Comunicaciones S.A. de C.V."
    doc.subject = title
    doc.creator = "Sistema AXIA"

    def _page(canvas, document):
        BasePdfGenerator.draw_page(canvas, document, title=title)

    doc.build(
        story,
        canvasmaker=BasePdfGenerator.canvas_factory(title),
        onFirstPage=_page,
        onLaterPages=_page,
    )
    if abrir:
        if os.name == "nt":
            os.startfile(str(ruta))
        else:
            os.system(f'xdg-open "{ruta}" >/dev/null 2>&1 &')
    return str(ruta)
