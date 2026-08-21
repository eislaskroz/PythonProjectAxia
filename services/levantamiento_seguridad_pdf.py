"""Plantilla maestra PDF para levantamientos AXIA.

La plantilla trabaja directamente con el registro persistido en Supabase y
renderiza cada tipo de levantamiento con bloques compactos y tablas dinámicas.
Seguridad y Monitoreo / Instalación conserva su distribución validada; el resto
de levantamientos reutiliza la misma lógica visual y de paginación.
"""
from __future__ import annotations

import base64
import json
from io import BytesIO
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
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




def _anotacion_plano_base64(registro: Mapping[str, Any]) -> str:
    """Extrae la imagen persistida de la anotación tipo plano, si existe."""
    payload = _json(registro.get("lev_anotacion_plano_json"), {})
    if not isinstance(payload, Mapping):
        return ""
    habilitado = payload.get("habilitado", True)
    if habilitado in (False, 0, "0", "false", "False", "No", "no"):
        return ""
    value = str(payload.get("imagen_base64") or "").strip()
    if value.startswith("data:image") and "," in value:
        value = value.split(",", 1)[1].strip()
    return value


def _append_anotacion_plano(story: list, registro: Mapping[str, Any], width: float, header) -> None:
    """Añade al PDF final el croquis/anotación gráfica conservando proporción."""
    encoded = _anotacion_plano_base64(registro)
    if not encoded:
        return
    try:
        raw = base64.b64decode(encoded, validate=False)
        stream = BytesIO(raw)
        image = RLImage(stream)
        iw = float(getattr(image, "imageWidth", 0) or 1)
        ih = float(getattr(image, "imageHeight", 0) or 1)
        max_w = min(width, 6.75 * inch)
        max_h = 4.55 * inch
        scale = min(max_w / iw, max_h / ih, 1.0)
        image.drawWidth = iw * scale
        image.drawHeight = ih * scale
        title = _section_title("Anotaciones tipo plano", width, header)
        story.append(Spacer(1, 7))
        story.append(KeepTogether([title, Spacer(1, 4), image]))
    except Exception:
        # Una anotación corrupta nunca debe impedir generar el levantamiento.
        return



def _evidencias_levantamiento(registro: Mapping[str, Any]) -> list:
    """Resuelve evidencias locales de preview o metadatos persistidos en Supabase."""
    locales = registro.get("__evidencias_locales") or []
    if locales:
        return list(locales) if isinstance(locales, (list, tuple)) else [locales]
    value = _json(registro.get("lev_evidencias_json"), [])
    if isinstance(value, Mapping):
        return [dict(value)]
    return list(value) if isinstance(value, (list, tuple)) else []


def _cargar_imagen_evidencia(item):
    """Devuelve bytes de una fotografía desde ruta local, URL o Storage."""
    try:
        origen = ""
        storage_path = ""
        if isinstance(item, Mapping):
            origen = str(item.get("url") or item.get("public_url") or item.get("ruta") or item.get("path") or "").strip()
            storage_path = str(item.get("storage_path") or "").strip()
        else:
            origen = str(item or "").strip()
        if origen and Path(origen).is_file():
            return Path(origen).read_bytes()
        if origen.lower().startswith(("http://", "https://")):
            try:
                import requests
                r = requests.get(origen, timeout=12)
                r.raise_for_status()
                return r.content
            except Exception:
                pass
        if storage_path:
            from supabase_config import supabase
            return supabase.storage.from_("bitacoras-evidencias").download(storage_path)
    except Exception:
        return None
    return None


def _append_evidencias_fotograficas(story: list, registro: Mapping[str, Any], width: float, header) -> None:
    """Añade evidencias fotográficas en cuadrícula de dos columnas."""
    items = _evidencias_levantamiento(registro)
    if not items:
        return
    try:
        from PIL import Image as PILImage, ImageOps
        cards = []
        for item in items:
            raw = _cargar_imagen_evidencia(item)
            if not raw:
                continue
            with PILImage.open(BytesIO(raw)) as im0:
                im = ImageOps.exif_transpose(im0)
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGB")
                buf = BytesIO()
                im.save(buf, format="PNG")
                buf.seek(0)
                iw, ih = im.size
            max_w, max_h = 3.18 * inch, 2.18 * inch
            scale = min(max_w / max(iw, 1), max_h / max(ih, 1))
            img = RLImage(buf, width=max(1, iw * scale), height=max(1, ih * scale))
            card = Table([[img]], colWidths=[3.28 * inch])
            card.setStyle(TableStyle([
                ("BOX", (0,0), (-1,-1), 0.4, BORDER),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("LEFTPADDING", (0,0), (-1,-1), 4),
                ("RIGHTPADDING", (0,0), (-1,-1), 4),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            cards.append(card)
        if not cards:
            return
        rows = []
        for i in range(0, len(cards), 2):
            rows.append([cards[i], cards[i+1] if i+1 < len(cards) else ""])
        grid = Table(rows, colWidths=[width/2, width/2], hAlign="LEFT")
        grid.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
        story.append(Spacer(1, 7))
        story.append(_section_title("Evidencia fotográfica", width, header))
        story.append(Spacer(1, 4))
        story.append(grid)
    except Exception:
        return

def _tipo_y_modalidad(registro: Mapping[str, Any], detail: Mapping[str, Any] | None = None) -> tuple[str, str]:
    """Resuelve la especialidad/modalidad igual para registros en memoria y Supabase.

    La tabla histórica conserva ``lev_tipo`` como código general, mientras la
    especialidad real vive en ``lev_detalle_tecnico_json.tipo_levantamiento``.
    Centralizar esta normalización evita PDFs distintos entre Operador y
    Administrativo.
    """
    detail = dict(detail or _detail(registro))
    tipo = str(
        registro.get("lev_tipo_levantamiento")
        or detail.get("tipo_levantamiento")
        or "Levantamiento"
    ).strip()
    modalidad = str(
        registro.get("lev_modalidad_operativa")
        or detail.get("modalidad_operativa")
        or ""
    ).strip()
    return tipo or "Levantamiento", modalidad


def es_seguridad_instalacion(registro: Mapping[str, Any]) -> bool:
    tipo, modalidad = _tipo_y_modalidad(registro)
    return tipo.casefold() == "seguridad y monitoreo" and modalidad.casefold() in {"instalación", "instalacion"}


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
    tipo_master, modalidad = _tipo_y_modalidad(registro, detail)
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
    duracion = registro.get("lev_duracion_proyecto") or ("Un día" if str(registro.get("lev_dias_trabajo") or "") == "1" else "Varios días")
    recurso_valor = (f"{registro.get('lev_horas_estimadas')} h" if duracion == "Un día" and registro.get("lev_horas_estimadas") not in (None, "") else (cctv.get("dias_trabajo") or registro.get("lev_dias_trabajo") or "No definido"))
    recurso_etiqueta = "HORAS ESTIMADAS" if duracion == "Un día" else "DÍAS DE TRABAJO"
    general_rows = [
        ["NOMBRE DE LEVANTAMIENTO", tipo_master or "Seguridad y Monitoreo",
         "FOLIO LEVANTAMIENTO", registro.get("lev_folio") or "Pendiente"],
        ["CLIENTE", registro.get("lev_cliente"), "FECHA", registro.get("lev_fecha_programada") or registro.get("fecha_registro")],
        ["DIRECCIÓN FISCAL", registro.get("lev_direccion"), "CONTACTO", registro.get("lev_contacto")],
        ["DIRECCIÓN SUCURSAL", registro.get("lev_direccion_sucursal") or registro.get("lev_ubicacion"), "CORREO", registro.get("lev_correo")],
        ["TIPO DE TRABAJO", modalidad or "Instalación", "DURACIÓN", duracion],
        [recurso_etiqueta, recurso_valor, "PERSONAS ESTIMADAS", registro.get("lev_personas_considerar") or cctv.get("personas_considerar") or "No definido"],
    ]
    if registro.get("lev_notas"):
        general_rows.append(["NOTAS", registro.get("lev_notas"), "", ""])
    # Días y personas forman parte del mismo bloque de datos generales para mantener
    # exactamente las mismas columnas, bordes y proporciones. Personas queda debajo
    # de Tipo de trabajo.
    story.append(_key_value_table(general_rows, [1.35*inch, 2.75*inch, 1.18*inch, 1.62*inch], normal, label))
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
    _append_anotacion_plano(story, registro, width, header)
    _append_evidencias_fotograficas(story, registro, width, header)

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


# ---------------------------------------------------------------------------
# Plantilla maestra general para TODOS los levantamientos
# ---------------------------------------------------------------------------

SECTION_TITLES = {
    "necesidad_inicial": "Necesidad inicial y alcance",
    "necesidad_alcance": "Necesidad inicial y alcance",
    "necesidad_respaldo": "Necesidad inicial y respaldo",
    "condiciones_sitio": "Condiciones del sitio",
    "equipo_requerido": "Equipo requerido",
    "ubicacion_instalacion": "Ubicación de instalación",
    "infraestructura_necesaria": "Infraestructura necesaria",
    "materiales_consumibles": "Materiales y consumibles estimados",
    "preparativos_riesgos": "Preparativos, permisos y riesgos",
    "instalacion_entrega_pruebas": "Instalación, pruebas y entrega",
    "datos_electricos_carga": "Datos eléctricos y carga",
    "ubicacion_sitio_maniobras": "Ubicación, sitio y maniobras",
    "combustible_escape_seguridad": "Combustible, escape y seguridad",
    "datos_electricos_tablero_protecciones": "Datos eléctricos, tablero y protecciones",
    "canalizacion_cableado_materiales": "Canalización, cableado y materiales",
    "cableado_canalizacion_consumibles": "Cableado, canalización y consumibles",
    "rack_equipo_activo_energia": "Rack, gabinete, equipo activo y energía",
    "seguridad_operacion": "Seguridad y operación",
    "estimacion_recursos": "Estimación de recursos",
    "infraestructura_existente": "Infraestructura existente",
    "rack_gabinete_energia": "Rack, gabinete y energía",
    "acceso_alturas_riesgos": "Acceso, alturas y riesgos",
    "datos_tecnicos_cctv": "Datos técnicos",
    "consumibles_conectividad": "Conectividad y consumibles",
    "ubicacion_estado_sintomas": "Ubicación, acceso, estado y síntomas",
    "alimentacion_energia": "Alimentación y energía",
    "conectividad_transmision_video": "Conectividad y transmisión de video",
    "configuracion_grabador": "Configuración y grabador",
    "mantenimiento": "Mantenimiento",
}

FIELD_LABELS = {
    "dias_trabajo": "Días de trabajo",
    "personas_trabajo": "Personas a considerar",
    "personas_considerar": "Personas a considerar",
    "cantidad_equipos": "Cantidad de equipos",
    "cantidad_camaras": "Cantidad de cámaras",
    "tipo_camaras": "Tipo de cámaras",
    "ubicacion_nvr_dvr": "Ubicación NVR/DVR",
    "punto_red": "Punto de red",
    "punto_energia": "Punto de energía",
    "tipo_servicio": "Tipo de servicio",
    "tipo_levantamiento": "Tipo de levantamiento",
    "modalidad_operativa": "Tipo de trabajo",
    "requiere": "¿Se requiere?",
    "partidas": "Partidas",
    "descripcion_detallada_servicio": "Descripción detallada del servicio",
    "descripcion_general_fallas": "Descripción general de fallas",
    "elemento_a_reparar": "¿Qué se desea reparar?",
    "codigo_error_dvr_nvr": "Código de error",
    "horario_falla": "Horario de la falla",
}

RESOURCE_KEYS_DAYS = {"dias_trabajo", "dias_trabajo_proyectados"}
RESOURCE_KEYS_PEOPLE = {"personas_trabajo", "personas_considerar", "personas_consideradas"}
SPECIAL_ROOT_KEYS = {
    "tipo_levantamiento", "modalidad_operativa", "canalizacion_materiales",
    "equipos_principales", "materiales_miscelaneos", "equipos_danados",
    "descripcion_general_fallas", "mantenimiento",
}


def es_levantamiento(registro: Mapping[str, Any]) -> bool:
    """True cuando el registro corresponde a un levantamiento AXIA."""
    return bool(
        str(registro.get("lev_tipo_levantamiento") or "").strip()
        or str(registro.get("lev_folio") or "").strip()
        or "lev_detalle_tecnico_json" in registro
    )


def _humanize(key: str) -> str:
    if key in FIELD_LABELS:
        return FIELD_LABELS[key]
    text = str(key or "").replace("_", " ").strip()
    replacements = {
        "nvr dvr": "NVR/DVR", "rj45": "RJ45", "ups": "UPS", "cfe": "CFE",
        "ip": "IP", "poe": "PoE", "esi": "ESI", "cctv": "CCTV",
    }
    low = text.casefold()
    if low in replacements:
        return replacements[low]
    return text[:1].upper() + text[1:]


def _section_name(key: str) -> str:
    return SECTION_TITLES.get(key, _humanize(key))


def _visible_declarative_sections(tipo: str, sections: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    """Devuelve únicamente los bloques que corresponden al flujo seleccionado.

    Los formularios declarativos guardan todos sus campos en ``lev_detalle_tecnico_json``
    aunque algunos estén ocultos en la interfaz. El PDF debe reproducir lo que el usuario
    vio/capturó, no imprimir bloques ocultos con valores por defecto como "No aplica".
    """
    items = [(str(k), v) for k, v in sections.items() if isinstance(v, Mapping)]
    if tipo.casefold() != "tecnología, equipos y periféricos".casefold():
        return items

    # La acción detonante vive en la primera sección del formulario TI.
    accion = ""
    for key, value in items:
        if "tipo_de_solicitud_y_alcance" in key.casefold():
            accion = _text(value.get("accion_ti"), "")
            break
    accion_cf = accion.casefold()

    # Debe ser idéntico a la visibilidad de la interfaz (levantamiento_view.py).
    # 0 Tipo solicitud, 1 Identificación, 2 Revisión, 3 Mant./Reparación,
    # 4 Requerimientos suministro, 5 Instalación/configuración.
    if accion_cf == "suministro":
        allowed = {
            "tipo_de_solicitud_y_alcance",
            "identificación_y_características_generales",
            "requerimientos_para_suministro",
        }
    elif accion_cf in {"suministro e instalación", "suministro e instalacion", "instalación", "instalacion"}:
        allowed = {
            "tipo_de_solicitud_y_alcance",
            "identificación_y_características_generales",
            "requerimientos_para_suministro",
            "instalación_configuración_pruebas_y_entrega",
        }
    elif accion_cf in {"revisión", "revision"}:
        allowed = {
            "tipo_de_solicitud_y_alcance",
            "identificación_y_características_generales",
            "revisión_y_diagnóstico",
            "instalación_configuración_pruebas_y_entrega",
        }
    elif accion_cf in {"mantenimiento", "reparación", "reparacion"}:
        allowed = {
            "tipo_de_solicitud_y_alcance",
            "identificación_y_características_generales",
            "revisión_y_diagnóstico",
            "mantenimiento_o_reparación",
            "instalación_configuración_pruebas_y_entrega",
        }
    else:
        # Compatibilidad con registros antiguos: si no hay acción reconocible, no ocultamos datos.
        return items

    return [(key, value) for key, value in items if key.casefold() in {x.casefold() for x in allowed}]


def _find_resources(value: Any) -> tuple[str, str]:
    days = ""
    people = ""
    def walk(node: Any):
        nonlocal days, people
        if isinstance(node, Mapping):
            for key, val in node.items():
                k = str(key).casefold()
                if not days and k in RESOURCE_KEYS_DAYS and _text(val, ""):
                    days = _text(val, "")
                elif not people and k in RESOURCE_KEYS_PEOPLE and _text(val, ""):
                    people = _text(val, "")
                if isinstance(val, (Mapping, list, tuple)):
                    walk(val)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
    walk(value)
    return days, people


def _is_resource_key(key: str) -> bool:
    k = str(key).casefold()
    return k in RESOURCE_KEYS_DAYS or k in RESOURCE_KEYS_PEOPLE


def _mapping_rows(mapping: Mapping[str, Any]) -> list[list[Any]]:
    """Convierte un bloque técnico en filas etiqueta/valor de dos pares por fila."""
    pairs: list[tuple[str, Any]] = []
    for key, value in mapping.items():
        if _is_resource_key(key) or key in {"partidas"}:
            continue
        if isinstance(value, (Mapping, list, tuple)):
            continue
        if value in (None, ""):
            value = "No aplica"
        pairs.append((_humanize(key), value))
    rows: list[list[Any]] = []
    for i in range(0, len(pairs), 2):
        first = pairs[i]
        second = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        rows.append([first[0], first[1], second[0], second[1]])
    return rows


def _append_mapping_section(story: list, title: str, mapping: Mapping[str, Any], width: float, normal, label, header):
    rows = _mapping_rows(mapping)
    if rows:
        story.append(_section_title(title, width, header))
        story.append(_key_value_table(rows, [1.55*inch, 1.90*inch, 1.55*inch, 1.90*inch], normal, label))
        story.append(Spacer(1, 6))


def _dynamic_rows(detail: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = detail.get(key) or []
    if isinstance(value, str):
        value = _json(value, [])
    return [dict(x) for x in value if isinstance(x, Mapping)] if isinstance(value, (list, tuple)) else []


def _equipment_rows(detail: Mapping[str, Any]) -> list[list[Any]]:
    return [[
        x.get("familia"), x.get("subfamilia"), x.get("cantidad"), x.get("marca"),
        x.get("modelo"), x.get("caracteristicas") or x.get("caracteristicas_tecnicas")
    ] for x in _dynamic_rows(detail, "equipos_principales")]


def _material_rows(detail: Mapping[str, Any]) -> list[list[Any]]:
    return [[x.get("material"), x.get("cantidad"), x.get("unidad"), x.get("especificacion") or x.get("medida")]
            for x in _dynamic_rows(detail, "materiales_miscelaneos")]


def _canal_rows(detail: Mapping[str, Any]) -> list[list[Any]]:
    entries = _dynamic_rows(detail, "canalizacion_materiales")
    if not entries:
        # Compatibilidad con los bloques que almacenan las partidas dentro de la sección.
        for value in detail.values():
            if isinstance(value, Mapping) and isinstance(value.get("partidas"), (list, tuple)):
                entries = [dict(x) for x in value.get("partidas", []) if isinstance(x, Mapping)]
                if entries:
                    break
    return [[
        x.get("categoria"), x.get("tipo"),
        x.get("tamano_calibre_especificacion") or x.get("tamano") or x.get("calibre") or "No aplica",
        x.get("cantidad"), x.get("unidad")
    ] for x in entries]


def _damaged_rows(registro: Mapping[str, Any], detail: Mapping[str, Any]) -> list[list[Any]]:
    entries = detail.get("equipos_danados") or _json(registro.get("lev_equipos_danados_json"), []) or []
    if not isinstance(entries, (list, tuple)):
        return []
    rows=[]
    for x in entries:
        if isinstance(x, Mapping):
            rows.append([x.get("tipo"), x.get("marca"), x.get("modelo"), x.get("serie") or x.get("numero_serie")])
    return rows


def _general_story(registro: Mapping[str, Any], detail: Mapping[str, Any], story: list, normal, label, header):
    tipo, modalidad = _tipo_y_modalidad(registro, detail)
    duracion = _text(registro.get("lev_duracion_proyecto"), "") or ("Un día" if str(registro.get("lev_dias_trabajo") or "") == "1" else "Varios días")
    general_rows = [
        ["NOMBRE DE LEVANTAMIENTO", tipo,
         "FOLIO LEVANTAMIENTO", registro.get("lev_folio") or "Pendiente"],
        ["CLIENTE", registro.get("lev_cliente"), "FECHA", registro.get("lev_fecha_programada") or registro.get("fecha_registro")],
        ["DIRECCIÓN FISCAL", registro.get("lev_direccion"), "CONTACTO", registro.get("lev_contacto")],
        ["DIRECCIÓN SUCURSAL", registro.get("lev_direccion_sucursal") or registro.get("lev_ubicacion"), "CORREO", registro.get("lev_correo")],
        ["TIPO DE TRABAJO", modalidad or "Instalación", "DURACIÓN", duracion],
    ]
    days, people = _find_resources(detail)
    days = days or _text(registro.get("lev_dias_trabajo"), "")
    people = people or _text(registro.get("lev_personas_considerar"), "")
    if duracion == "Un día":
        general_rows.append([
            "HORAS ESTIMADAS", _text(registro.get("lev_horas_estimadas"), "No definido"),
            "PERSONAS ESTIMADAS", people or "No definido",
        ])
    else:
        general_rows.append([
            "DÍAS DE TRABAJO", days or "No definido",
            "PERSONAS ESTIMADAS", people or "No definido",
        ])
    if _text(registro.get("lev_notas"), ""):
        general_rows.append(["NOTAS", registro.get("lev_notas"), "", ""])
    story.append(_key_value_table(general_rows, [1.35*inch, 2.75*inch, 1.18*inch, 1.62*inch], normal, label))
    story.append(Spacer(1, 7))


def _description_for(registro: Mapping[str, Any], detail: Mapping[str, Any]) -> str:
    # Reparación tiene una descripción propia; mantenimiento también.
    if _text(registro.get("lev_descripcion_fallas"), ""):
        return _text(registro.get("lev_descripcion_fallas"), "")
    maint = detail.get("mantenimiento")
    if isinstance(maint, Mapping) and _text(maint.get("descripcion_detallada_servicio"), ""):
        return _text(maint.get("descripcion_detallada_servicio"), "")
    return _text(registro.get("lev_observaciones") or registro.get("lev_descripcion"), "Sin descripción capturada.")


def generar_pdf_levantamiento_maestro(
    registro: Mapping[str, Any], *, ruta_salida: str | Path, abrir: bool = False,
) -> str:
    """Genera la estructura maestra para cualquier tipo de levantamiento AXIA."""
    # Conserva 1:1 la plantilla ya aprobada para Seguridad / Instalación.
    if es_seguridad_instalacion(registro):
        return generar_pdf_seguridad_instalacion(registro, ruta_salida=ruta_salida, abrir=abrir)

    import os
    from reportlab.lib.styles import ParagraphStyle

    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    styles = BasePdfGenerator.styles()
    normal = styles["normal"]
    header = styles["table_header"]
    label = ParagraphStyle(
        "AxiaMasterLabelGeneral", parent=normal, fontName="Helvetica-Bold",
        fontSize=7.0, leading=8.4, textColor=BasePdfGenerator.PRIMARY,
    )
    detail = _detail(registro)
    width = 6.90 * inch
    doc = SimpleDocTemplate(
        str(ruta), pagesize=(612, 792), rightMargin=BasePdfGenerator.RIGHT_MARGIN,
        leftMargin=BasePdfGenerator.LEFT_MARGIN, topMargin=BasePdfGenerator.TOP_MARGIN,
        bottomMargin=BasePdfGenerator.BOTTOM_MARGIN,
    )
    story: list = []
    _general_story(registro, detail, story, normal, label, header)

    tipo, modalidad = _tipo_y_modalidad(registro, detail)

    # Seguridad / Reparación tiene una estructura propia derivada del formulario.
    if tipo.casefold() == "seguridad y monitoreo" and modalidad.casefold() in {"reparación", "reparacion"}:
        if detail.get("elemento_a_reparar"):
            _append_mapping_section(story, "Reparación: selección del elemento", {"elemento_a_reparar": detail.get("elemento_a_reparar")}, width, normal, label, header)
        # Reparación solo debe imprimir los bloques que realmente están visibles
        # en el formulario actual. Las secciones históricas de alimentación,
        # conectividad y grabador se ignoran incluso si existen en registros viejos.
        value = detail.get("ubicacion_estado_sintomas")
        if isinstance(value, Mapping):
            _append_mapping_section(story, _section_name("ubicacion_estado_sintomas"), value, width, normal, label, header)
        damaged = _damaged_rows(registro, detail)
        if damaged:
            story.append(_section_matrix_table(
                "Información de equipos dañados", ["Tipo de equipo", "Marca", "Modelo", "Número de serie"],
                damaged, [1.35*inch,1.55*inch,1.55*inch,2.45*inch], normal, header
            ))
            story.append(Spacer(1, 7))
    elif tipo.casefold() == "seguridad y monitoreo" and modalidad.casefold() == "mantenimiento":
        # Mantenimiento comparte con Instalación la evaluación de acceso,
        # alturas y riesgos. Es el único bloque técnico adicional aplicable.
        value = detail.get("acceso_alturas_riesgos")
        if isinstance(value, Mapping):
            _append_mapping_section(story, _section_name("acceso_alturas_riesgos"), value, width, normal, label, header)
    else:
        # Formularios declarativos almacenan sus bloques bajo `secciones`.
        sections = detail.get("secciones")
        if isinstance(sections, Mapping):
            for key, value in _visible_declarative_sections(tipo, sections):
                _append_mapping_section(story, _section_name(str(key)), value, width, normal, label, header)
        else:
            # Formularios especializados clásicos: un bloque por clave raíz.
            for key, value in detail.items():
                if key in SPECIAL_ROOT_KEYS:
                    continue
                if isinstance(value, Mapping):
                    _append_mapping_section(story, _section_name(str(key)), value, width, normal, label, header)

    # Partidas dinámicas comunes. En Seguridad y Monitoreo solo aplican
    # a Instalación; Reparación/Mantenimiento deben ignorar incluso datos
    # históricos que pudieran existir en registros anteriores.
    canal = _canal_rows(detail)
    if tipo.casefold() == "seguridad y monitoreo" and modalidad.casefold() not in {"instalación", "instalacion"}:
        canal = []
    if canal:
        story.append(_section_matrix_table(
            "Canalización, cableado y materiales",
            ["Categoría", "Tipo", "Tamaño/Calibre", "Cantidad", "Unidad"], canal,
            [1.05*inch,2.35*inch,1.55*inch,.88*inch,1.07*inch], normal, header
        ))
        story.append(Spacer(1, 7))

    equipment = _equipment_rows(detail)
    if equipment:
        story.append(_section_matrix_table(
            "Equipos principales requeridos",
            ["Familia", "Subfamilia", "Cantidad", "Marca", "Modelo", "Características técnicas"], equipment,
            [1.05*inch,1.15*inch,.65*inch,.95*inch,.95*inch,2.15*inch], normal, header
        ))
        story.append(Spacer(1, 7))

    materials = _material_rows(detail)
    if materials:
        story.append(_section_matrix_table(
            "Materiales misceláneos y consumibles",
            ["Material", "Cantidad", "Unidad", "Especificación/Medida"], materials,
            [2.15*inch,.9*inch,1.0*inch,2.85*inch], normal, header
        ))
        story.append(Spacer(1, 7))

    story.append(_description_table(_description_for(registro, detail), width, normal, header))
    _append_anotacion_plano(story, registro, width, header)
    _append_evidencias_fotograficas(story, registro, width, header)

    title = f"Levantamiento {tipo}" + (f" - {modalidad}" if modalidad else "")
    doc.title = f"AXIA - {title}"
    doc.author = "AXIA Comunicaciones S.A. de C.V."
    doc.subject = title
    doc.creator = "Sistema AXIA"
    def _page(canvas, document):
        BasePdfGenerator.draw_page(canvas, document, title=title)
    doc.build(story, canvasmaker=BasePdfGenerator.canvas_factory(title), onFirstPage=_page, onLaterPages=_page)
    if abrir:
        if os.name == "nt":
            os.startfile(str(ruta))
        else:
            os.system(f'xdg-open "{ruta}" >/dev/null 2>&1 &')
    return str(ruta)
