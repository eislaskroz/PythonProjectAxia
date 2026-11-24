from __future__ import annotations

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import base64
import io
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from tkinter import Toplevel, Canvas, messagebox, simpledialog

import customtkinter as ctk
from ui.native_combobox import NativeComboBox
from PIL import Image, ImageDraw, ImageOps, ImageTk, ImageFont

from ui.colors import SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER, WHITE
from ui.fonts import TEXT_SM, BUTTON_FONT
from core.pdf import BasePdfGenerator
from utils import centrar_ventana

ENTRY_H = 30
OPTION_H = 30
LABEL_FONT = ("Montserrat", 10)
SMALL_FONT = ("Montserrat", 10)
SECTION_FONT = ("Montserrat", 14, "bold")


def obtener_textbox(box):
    return box.get("1.0", "end").strip()


def limpiar_json(valor):
    try:
        return json.loads(valor) if isinstance(valor, str) and valor.strip() else valor
    except Exception:
        return valor




def anotacion_plano_popup(parent, variable_base64, on_change=None, titulo="Anotaciones tipo plano"):
    from views.croquis_editor_view import anotacion_plano_popup as abrir_editor
    return abrir_editor(parent, variable_base64, on_change=on_change, titulo=titulo)


def firmar_en_popup(parent, variable_firma_base64, on_change=None, titulo="Firma del cliente"):
    win = Toplevel(parent)
    win.title(titulo)
    win.transient(parent.winfo_toplevel())
    centrar_ventana(win, 620, 340, padre=parent.winfo_toplevel())
    win.grab_set()

    frame = ctk.CTkFrame(win, fg_color=WHITE)
    frame.pack(fill="both", expand=True, padx=6, pady=6)
    ctk.CTkLabel(frame, text=titulo, font=SECTION_FONT, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 4))
    ctk.CTkLabel(frame, text="Dibuje la firma con el panel táctil, mouse o pantalla táctil.", font=SMALL_FONT, text_color=TEXT_SECONDARY).pack(anchor="w", pady=(0, 4))

    canvas_w, canvas_h = 560, 190
    canvas = Canvas(frame, width=canvas_w, height=canvas_h, bg="white", highlightthickness=1, highlightbackground="#B8C2CC")
    canvas.pack(pady=(0, 5))

    img = Image.new("RGB", (canvas_w, canvas_h), "white")
    draw = ImageDraw.Draw(img)
    last = {"x": None, "y": None}
    tiene_trazos = {"valor": False}

    def iniciar(event):
        last["x"], last["y"] = event.x, event.y

    def dibujar(event):
        if last["x"] is not None:
            canvas.create_line(last["x"], last["y"], event.x, event.y, width=3, fill="black", capstyle="round", smooth=True)
            draw.line((last["x"], last["y"], event.x, event.y), fill="black", width=3)
            tiene_trazos["valor"] = True
        last["x"], last["y"] = event.x, event.y

    def soltar(_event):
        last["x"], last["y"] = None, None

    def limpiar():
        canvas.delete("all")
        draw.rectangle((0, 0, canvas_w, canvas_h), fill="white")
        variable_firma_base64.set("")
        tiene_trazos["valor"] = False
        if on_change:
            on_change()

    def guardar():
        if not tiene_trazos["valor"]:
            messagebox.showwarning("Firma", "El cliente debe dibujar su firma antes de guardar.")
            return
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        variable_firma_base64.set(base64.b64encode(buffer.getvalue()).decode("utf-8"))
        if on_change:
            on_change()
        win.destroy()

    canvas.bind("<ButtonPress-1>", iniciar)
    canvas.bind("<B1-Motion>", dibujar)
    canvas.bind("<ButtonRelease-1>", soltar)

    botones = ctk.CTkFrame(frame, fg_color="transparent")
    botones.pack(fill="x")
    ctk.CTkButton(botones, text="Limpiar", width=120, height=34, fg_color="gray", command=limpiar).pack(side="left", padx=3)
    ctk.CTkButton(botones, text="Guardar firma", width=160, height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=guardar).pack(side="right", padx=3)

from services.movimientos_service import registrar_movimiento_seguro


def _nombre_archivo_seguro(texto):
    texto = str(texto or "").strip() or "documento"
    reemplazos = {"á":"a", "é":"e", "í":"i", "ó":"o", "ú":"u", "Á":"A", "É":"E", "Í":"I", "Ó":"O", "Ú":"U", "ñ":"n", "Ñ":"N"}
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)
    permitidos = []
    for c in texto:
        if c.isalnum() or c in ("-", "_", "."):
            permitidos.append(c)
        elif c.isspace():
            permitidos.append("_")
    limpio = "".join(permitidos).strip("._-")
    while "__" in limpio:
        limpio = limpio.replace("__", "_")
    return limpio or "documento"


def _documentos_windows_real():
    if os.name != "nt":
        return Path.home() / "Documents"
    try:
        import ctypes
        from ctypes import wintypes
        from uuid import UUID

        guid = UUID("FDD39AD0-238F-46AF-ADB4-6C85480369C7")
        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                        ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
        data = guid.bytes_le
        folder_id = GUID.from_buffer_copy(data)
        path_ptr = ctypes.c_wchar_p()
        shell = ctypes.windll.shell32
        shell.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD,
                                                wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
        shell.SHGetKnownFolderPath.restype = ctypes.c_long
        result = shell.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path_ptr))
        if result == 0 and path_ptr.value:
            resolved = Path(path_ptr.value)
            ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(path_ptr, ctypes.c_void_p))
            return resolved
    except Exception:
        logger.warning("No fue posible consultar Documentos de Windows; se usará la ruta alternativa.", exc_info=True)
    return Path.home() / "Documents"


def ruta_documentos_axia(subcarpeta="documentos"):
    nombre = str(subcarpeta or "documentos").strip()
    if not nombre or Path(nombre).name != nombre or nombre in (".", ".."):
        raise ValueError("Subcarpeta AXIA no válida")
    base = _documentos_windows_real() / "AXIA" / nombre
    base.mkdir(parents=True, exist_ok=True)
    logger.info("Carpeta local AXIA para %s: %s", nombre, base)
    return base


def _auditar_pdf(titulo, resultado, ruta_salida=None, abrir=True):
    if resultado:
        accion = "PREVISUALIZAR_PDF" if abrir else "GENERAR_PDF"
        registrar_movimiento_seguro(
            modulo="PDF", accion=accion,
            descripcion=f"{accion.replace('_', ' ').title()}: {titulo}",
            registro_afectado=str(ruta_salida or titulo),
        )
    return resultado


def generar_pdf_archivo(titulo, datos, nombre_archivo=None, subcarpeta="documentos", secciones_tabla=None, firma_base64=None, firma_tecnico_base64=None, mostrar_firmas=None):
    if not nombre_archivo:
        folio = ""
        if isinstance(datos, dict):
            for clave in ("Folio OS", "Folio OT", "Folio BIT", "Folio OBC", "Folio LEV", "Folio de Levantamiento", "Folio Bitácora", "Folio de bitácora"):
                if str(datos.get(clave) or "").strip():
                    folio = str(datos.get(clave)).strip()
                    break
        nombre_archivo = folio or titulo
    nombre_archivo = _nombre_archivo_seguro(nombre_archivo)
    if not nombre_archivo.lower().endswith(".pdf"):
        nombre_archivo += ".pdf"
    ruta = ruta_documentos_axia(subcarpeta) / nombre_archivo
    return generar_pdf_preview(
        titulo,
        datos,
        secciones_tabla=secciones_tabla,
        firma_base64=firma_base64,
        firma_tecnico_base64=firma_tecnico_base64,
        mostrar_firmas=mostrar_firmas,
        ruta_salida=ruta,
        abrir=False,
    )





def _generar_pdf_orden_servicio_axia(datos, firma_base64=None, ruta_salida=None, abrir=True):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, Image as RLImage
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from html import escape as html_escape
    except Exception as error:
        messagebox.showerror("Preview PDF", f"No está instalado reportlab.\n\n{error}")
        return False

    datos = dict(datos or {})
    if ruta_salida:
        ruta = Path(ruta_salida); ruta.parent.mkdir(parents=True, exist_ok=True)
    else:
        ruta = Path(tempfile.gettempdir()) / f"AXIA_preview_Orden_Servicio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    BLUE = colors.HexColor("#1F4E79")
    LIGHT_BLUE = colors.HexColor("#EAF1F7")
    BORDER = colors.HexColor("#8FA3B5")
    TEXT = colors.HexColor("#243447")
    estilos = BasePdfGenerator.styles()
    normal = ParagraphStyle("AxiaOsNormal", parent=estilos["normal"], fontName="Helvetica", fontSize=7.4, leading=9.1, textColor=TEXT)
    label = ParagraphStyle("AxiaOsLabel", parent=normal, fontName="Helvetica-Bold", fontSize=7.1, leading=8.5)
    header = ParagraphStyle("AxiaOsHeader", parent=normal, fontName="Helvetica-Bold", fontSize=7.2, leading=8.6, textColor=colors.white, alignment=1)
    center = ParagraphStyle("AxiaOsCenter", parent=normal, alignment=1)

    def text(*keys, fallback=""):
        for key in keys:
            value = str(datos.get(key) or "").strip()
            if value:
                return value
        return fallback

    def p(value, style=normal):
        return Paragraph(html_escape(str(value or "")), style)

    # Ancho compartido de todos los bloques, dejando libre el logo sin bajar nada.
    ancho_os = 6.55 * inch

    def pair_table(rows, widths):
        t = Table([[p(a,label), p(b)] for a,b in rows], colWidths=widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.45, BORDER),
            ("BACKGROUND", (0,0), (0,-1), LIGHT_BLUE),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 2.5), ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ]))
        return t

    def box(title, body, height=None):
        body_p = p(body, normal)
        t = Table([[p(title.upper(), header)], [body_p]], colWidths=[ancho_os], rowHeights=[0.23*inch, None], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BLUE), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.45, BORDER), ("VALIGN", (0,1), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,1), (-1,1), 6), ("BOTTOMPADDING", (0,1), (-1,1), 6),
        ]))
        return t

    left_rows = [
        ("Fecha", text("Fecha")), ("Cliente", text("Cliente")), ("Sucursal", text("Sucursal")),
        ("Domicilio", text("Domicilio")), ("Encargado", text("Encargado")),
        ("Solicitante", text("Solicitante")),
        ("Hora de llegada", text("Hora de Llegada", "Hora de llegada")),
        ("Hora de salida", text("Hora de Salida", "Hora de salida")),
    ]
    right_rows = [
        ("Tipo de Servicio", text("Tipo de Servicio")), ("No. ACO", text("ACO")),
        ("Supervisor AXIA", text("Supervisor")), ("Encargado AXIA", text("Encargado Servicio")),
        ("Técnicos AXIA", text("Técnicos")),
    ]
    left = pair_table(left_rows, [0.88*inch, 2.18*inch])
    right = pair_table(right_rows, [0.94*inch, 2.55*inch])
    top = Table([[left, right]], colWidths=[3.06*inch, 3.49*inch], hAlign="LEFT")
    top.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0)]))

    descripcion = text("Descripción", fallback="")
    observaciones = text("Observaciones", fallback="")
    evaluaciones = [
        ("TRATO Y ACTITUD", text("Evaluación trato", "Eval trato", "Trato y actitud", "Trato")),
        ("HABILIDADES", text("Evaluación habilidades", "Eval habilidades", "Habilidades y conocimientos", "Habilidades")),
        ("VELOCIDAD Y CALIDAD", text("Evaluación velocidad", "Eval velocidad", "Velocidad y calidad", "Velocidad")),
        ("OTRO", text("Evaluación otro", "Eval otro", "Otro")),
    ]

    eval_header_cells = [p(etiqueta, header) for etiqueta, _ in evaluaciones]
    eval_value_cells = [p(valor or "No aplica", center) for _, valor in evaluaciones]
    evaluacion_tabla = Table(
        [eval_header_cells, eval_value_cells],
        colWidths=[ancho_os / 4] * 4,
        hAlign="LEFT",
    )
    evaluacion_tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLUE),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.45, BORDER),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))

    evaluacion_titulo = Table([[p("Evaluación del Servicio".upper(), header)]], colWidths=[ancho_os], hAlign="LEFT")
    evaluacion_titulo.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BLUE),
        ("BOX", (0,0), (-1,-1), 0.45, BORDER),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))

    story = [
        Paragraph("ORDEN DE SERVICIO", ParagraphStyle("AxiaOsTitle", parent=estilos["title"], fontName="Helvetica-Bold", fontSize=13, leading=15, alignment=1, textColor=TEXT)),
        Spacer(1, 4), top, Spacer(1, 8),
        box("Descripción del Servicio y/o Instalación", descripcion), Spacer(1, 8),
        evaluacion_titulo, evaluacion_tabla, Spacer(1, 8),
    ]

    evidencias_raw = datos.get("Evidencia Fotográfica") or datos.get("Fotos") or []
    if isinstance(evidencias_raw, str):
        try:
            evidencias_raw = json.loads(evidencias_raw) if evidencias_raw.strip() else []
        except Exception:
            evidencias_raw = [evidencias_raw]
    if isinstance(evidencias_raw, dict):
        evidencias_raw = [evidencias_raw]

    from services.pdf_fotos_inteligentes import FotoPdf, construir_filas_fotos
    fotos_preparadas = []
    for item in evidencias_raw or []:
        try:
            if isinstance(item, dict):
                nombre = str(item.get("nombre") or item.get("storage_path") or "Evidencia")
                origen = str(item.get("url") or item.get("ruta") or item.get("path") or "").strip()
            else:
                origen = str(item or "").strip()
                nombre = Path(origen).name or "Evidencia"
            contenido = None
            if origen and Path(origen).is_file():
                contenido = Path(origen).read_bytes()
            elif origen.lower().startswith(("http://", "https://")):
                import requests
                resp = requests.get(origen, timeout=12)
                resp.raise_for_status()
                contenido = resp.content
            elif isinstance(item, dict) and str(item.get("storage_path") or "").strip():
                from supabase_config import supabase
                contenido = supabase.storage.from_("bitacoras-evidencias").download(
                    str(item.get("storage_path")).strip()
                )
            if not contenido:
                logger.warning("Evidencia no disponible para OS: %s", nombre)
                continue
            with Image.open(io.BytesIO(contenido)) as src:
                img = ImageOps.exif_transpose(src)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
                ancho_px, alto_px = img.size
                buff = io.BytesIO()
                img.save(buff, format="JPEG", quality=85, optimize=True)
            fotos_preparadas.append(FotoPdf(buff.getvalue(), nombre, ancho_px, alto_px))
        except Exception:
            logger.warning("No se pudo incorporar evidencia al PDF de Orden de Servicio", exc_info=True)
    if fotos_preparadas:
        fotos_header = Table([[p("EVIDENCIA FOTOGRÁFICA", header)]], colWidths=[ancho_os], hAlign="LEFT")
        fotos_header.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), BLUE),
            ("BOX", (0,0), (-1,-1), 0.45, BORDER),
        ]))
        filas_fotos = construir_filas_fotos(
            fotos_preparadas, estilo_texto=normal,
            ancho_total=ancho_os, alineacion="LEFT",
        )
        story.append(KeepTogether([fotos_header, Spacer(1, 5), filas_fotos[0]]))
        story.extend(filas_fotos[1:])
        story.append(Spacer(1, 8))

    firma_flow = None
    if firma_base64:
        try:
            raw = str(firma_base64)
            if "," in raw and "base64" in raw[:80].lower(): raw = raw.split(",",1)[1]
            img_bytes = base64.b64decode(raw)
            firma_flow = RLImage(io.BytesIO(img_bytes), width=1.55*inch, height=0.58*inch)
        except Exception:
            firma_flow = None
    firma_content = firma_flow or p("", center)
    firmante_nombre = text("Nombre del encargado firmante", "Encargado")
    firmante_puesto = text("Puesto del encargado firmante")
    firmante_correo = text("Correo")
    firmante_celular = text("Celular")
    leyenda_firma = "FIRMA CLIENTE / ENCARGADO"
    if firmante_nombre:
        leyenda_firma += f"<br/><b>{html_escape(firmante_nombre)}</b>"
    if firmante_puesto:
        leyenda_firma += f"<br/>{html_escape(firmante_puesto)}"
    if firmante_correo:
        leyenda_firma += f"<br/>Correo: {html_escape(firmante_correo)}"
    if firmante_celular:
        leyenda_firma += f"<br/>Celular: {html_escape(firmante_celular)}"
    firma = Table([[firma_content], [Paragraph(leyenda_firma, center)]], colWidths=[2.55*inch], rowHeights=[0.68*inch, None])
    firma.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.55, BORDER), ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    firma_wrap = Table([["", firma, ""]], colWidths=[2.00*inch, 2.55*inch, 2.00*inch], hAlign="LEFT")
    firma_wrap.setStyle(TableStyle([("ALIGN", (1,0), (1,0), "CENTER"), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(firma_wrap)

    try:
        doc = SimpleDocTemplate(str(ruta), pagesize=letter, rightMargin=BasePdfGenerator.RIGHT_MARGIN, leftMargin=BasePdfGenerator.LEFT_MARGIN, topMargin=BasePdfGenerator.TOP_MARGIN, bottomMargin=BasePdfGenerator.BOTTOM_MARGIN)
        title = "Orden de Servicio"; doc.title=f"AXIA - {title}"; doc.author="AXIA Comunicaciones S.A. de C.V."; doc.subject=title; doc.creator="Sistema AXIA"
        def _on_page(canvas, document): BasePdfGenerator.draw_page(canvas, document, title=title)
        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page, canvasmaker=BasePdfGenerator.canvas_factory(title))
        if abrir:
            try: os.startfile(str(ruta))
            except AttributeError:
                import subprocess; subprocess.Popen(["xdg-open", str(ruta)])
            except Exception: logger.debug("No fue posible abrir el PDF automáticamente.", exc_info=True)
        return str(ruta)
    except Exception as error:
        messagebox.showerror("Preview PDF", f"No se pudo generar el preview.\n\n{error}")
        logger.exception("Error generando Orden de Servicio PDF")
        return False

def _generar_pdf_orden_trabajo_axia(datos, secciones_tabla=None, ruta_salida=None, abrir=True):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from html import escape as html_escape
    except Exception as error:
        messagebox.showerror("Preview PDF", f"No está instalado reportlab.\n\n{error}")
        return False

    datos = dict(datos or {})
    if ruta_salida:
        ruta = Path(ruta_salida)
        ruta.parent.mkdir(parents=True, exist_ok=True)
    else:
        ruta = Path(tempfile.gettempdir()) / f"AXIA_preview_Orden_Trabajo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    BLUE = colors.HexColor("#1F4E79")
    LIGHT_BLUE = colors.HexColor("#EAF1F7")
    BORDER = colors.HexColor("#8FA3B5")
    TEXT = colors.HexColor("#243447")
    WHITE_BG = colors.white

    estilos = BasePdfGenerator.styles()
    normal = ParagraphStyle(
        "AxiaOtMasterNormal", parent=estilos["normal"], fontName="Helvetica",
        fontSize=7.4, leading=9.2, textColor=TEXT,
    )
    label = ParagraphStyle(
        "AxiaOtMasterLabel", parent=normal, fontName="Helvetica-Bold",
        fontSize=7.1, leading=8.6,
    )
    header = ParagraphStyle(
        "AxiaOtMasterHeader", parent=normal, fontName="Helvetica-Bold",
        fontSize=7.0, leading=8.4, textColor=colors.white,
    )

    def text(*keys, fallback="-"):
        for key in keys:
            value = str(datos.get(key) or "").strip()
            if value:
                return value
        return fallback

    def p(value, style=normal, fallback="-"):
        value = str(value if value not in (None, "") else fallback)
        return Paragraph(html_escape(value), style)

    def section_title(title, width):
        table = Table([[Paragraph(html_escape(str(title).upper()), header)]], colWidths=[width])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, BLUE),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return table

    # Se reserva espacio uniforme del lado derecho para respetar el área del logo,
    # sin empujar el contenido hacia abajo.
    width = 6.55 * inch

    general_rows = [
        ["NOMBRE DE ORDEN DE TRABAJO", "Orden de Trabajo", "FOLIO ORDEN DE TRABAJO", text("Folio OT")],
        ["CLIENTE", text("Cliente"), "FECHA", text("Fecha")],
        ["SUCURSAL", text("Sucursal"), "CONTACTO", text("Contacto")],
        ["JEFE DE OPERACIONES", text("Jefe de Operación", "Jefe de Operaciones"), "SUPERVISOR", text("Supervisor")],
        ["NO. ACO", text("ACO"), "ESI / RESPONSABLE", text("ESI", "Técnico / responsable")],
        ["NÚMERO DE DÍAS", text("Número de Días"), "NÚMERO DE PERSONAS", text("Número de Personas")],
    ]
    general_data = []
    for row in general_rows:
        general_data.append([
            p(row[0], label, ""), p(row[1], normal, ""),
            p(row[2], label, ""), p(row[3], normal, ""),
        ])
    general = Table(
        general_data,
        colWidths=[1.12 * inch, 1.95 * inch, 1.19 * inch, 2.29 * inch],
        repeatRows=0,
        hAlign="LEFT",
    )
    general.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE_BG),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
        ("BACKGROUND", (2, 0), (2, -1), LIGHT_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
    ]))

    service = text("Asunto", "Descripción", "Servicio", fallback="Sin descripción capturada.")
    service_table = Table(
        [[Paragraph("SERVICIO", header)], [p(service, normal, "")]],
        colWidths=[width],
        hAlign="LEFT",
    )
    service_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 1), (-1, 1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 5),
    ]))

    aliases = {
        "partida": ("Partida", "partida", "part."),
        "unidad": ("Unidad", "unidad"),
        "cantidad": ("Cantidad", "cantidad"),
        "modelo": ("Modelo", "modelo"),
        "marca": ("Marca", "marca"),
        "concepto": ("Concepto", "concepto", "Material", "material", "Equipo", "equipo", "Descripción", "descripcion"),
    }

    def pick(row, names):
        for name in names:
            if name in row and str(row.get(name) or "").strip():
                return str(row.get(name) or "").strip()
        return ""

    story = [general, Spacer(1, 7), service_table]
    sections_render = []
    for section in secciones_tabla or []:
        try:
            section_title_text, _headers, rows = section
        except Exception:
            continue
        normalized_rows = []
        counter = 1
        for raw in rows or []:
            if not isinstance(raw, dict):
                continue
            row = {
                "Partida": pick(raw, aliases["partida"]) or str(counter),
                "Unidad": pick(raw, aliases["unidad"]),
                "Cantidad": pick(raw, aliases["cantidad"]),
                "Modelo": pick(raw, aliases["modelo"]),
                "Marca": pick(raw, aliases["marca"]),
                "Concepto": pick(raw, aliases["concepto"]),
            }
            if any(row[k] for k in ("Unidad", "Cantidad", "Modelo", "Marca", "Concepto")):
                normalized_rows.append(row)
                counter += 1
        if normalized_rows:
            sections_render.append((str(section_title_text or "Partidas"), normalized_rows))

    if not sections_render and datos.get("_partidas_ot"):
        normalized_rows = []
        for counter, raw in enumerate(datos.get("_partidas_ot") or [], 1):
            if not isinstance(raw, dict):
                continue
            row = {
                "Partida": pick(raw, aliases["partida"]) or str(counter),
                "Unidad": pick(raw, aliases["unidad"]),
                "Cantidad": pick(raw, aliases["cantidad"]),
                "Modelo": pick(raw, aliases["modelo"]),
                "Marca": pick(raw, aliases["marca"]),
                "Concepto": pick(raw, aliases["concepto"]),
            }
            if any(row[k] for k in ("Unidad", "Cantidad", "Modelo", "Marca", "Concepto")):
                normalized_rows.append(row)
        if normalized_rows:
            sections_render.append(("Materiales", normalized_rows))

    for section_title_text, normalized_rows in sections_render:
        story.append(Spacer(1, 7))
        table_data = [
            [Paragraph(html_escape(section_title_text.upper()), header), "", "", "", "", ""],
            [Paragraph(h, header) for h in ("PARTIDA", "UNIDAD", "CANTIDAD", "MODELO", "MARCA", "CONCEPTO")],
        ]
        for row in normalized_rows:
            table_data.append([
                p(row["Partida"], normal, ""), p(row["Unidad"], normal, ""),
                p(row["Cantidad"], normal, ""), p(row["Modelo"], normal, ""),
                p(row["Marca"], normal, ""), p(row["Concepto"], normal, ""),
            ])
        tabla = LongTable(
            table_data,
            colWidths=[0.55*inch, 0.66*inch, 0.68*inch, 0.87*inch, 0.99*inch, 2.80*inch],
            repeatRows=2, splitByRow=1,
            hAlign="LEFT",
        )
        tabla.setStyle(TableStyle([
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 0), (-1, 1), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.white),
            ("GRID", (0, 1), (-1, -1), 0.45, BORDER),
            ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 2), (2, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        story.append(tabla)

    try:
        doc = SimpleDocTemplate(
            str(ruta), pagesize=letter,
            rightMargin=BasePdfGenerator.RIGHT_MARGIN,
            leftMargin=BasePdfGenerator.LEFT_MARGIN,
            topMargin=BasePdfGenerator.TOP_MARGIN,
            bottomMargin=BasePdfGenerator.BOTTOM_MARGIN,
        )
        title = "Orden de Trabajo"
        doc.title = f"AXIA - {title}"
        doc.author = "AXIA Comunicaciones S.A. de C.V."
        doc.subject = title
        doc.creator = "Sistema AXIA"

        def _on_page(canvas, document):
            BasePdfGenerator.draw_page(canvas, document, title=title)

        doc.build(
            story,
            onFirstPage=_on_page,
            onLaterPages=_on_page,
            canvasmaker=BasePdfGenerator.canvas_factory(title),
        )
        if abrir:
            try:
                os.startfile(str(ruta))
            except AttributeError:
                import subprocess
                subprocess.Popen(["xdg-open", str(ruta)])
            except Exception:
                logger.debug("No fue posible abrir el PDF automáticamente.", exc_info=True)
        return str(ruta)
    except Exception as error:
        messagebox.showerror("Preview PDF", f"No se pudo generar el preview.\n\n{error}")
        logger.exception("Error generando Orden de Trabajo PDF maestra")
        return False


def _generar_pdf_bitacora_avance_axia(datos, ruta_salida=None, abrir=True):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, LongTable, TableStyle, Image as RLImage, KeepTogether
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from html import escape as html_escape
    except Exception as error:
        messagebox.showerror("Preview PDF", f"No está instalado reportlab.\n\n{error}")
        return False

    datos = dict(datos or {})
    if ruta_salida:
        ruta = Path(ruta_salida)
        ruta.parent.mkdir(parents=True, exist_ok=True)
    else:
        ruta = Path(tempfile.gettempdir()) / f"AXIA_preview_Bitacora_Avance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    BLUE = colors.HexColor("#1F4E79")
    LIGHT_BLUE = colors.HexColor("#EAF1F7")
    BORDER = colors.HexColor("#8FA3B5")
    TEXT = colors.HexColor("#243447")
    estilos = BasePdfGenerator.styles()
    normal = ParagraphStyle("AxiaBitNormal", parent=estilos["normal"], fontName="Helvetica", fontSize=7.4, leading=9.2, textColor=TEXT)
    label = ParagraphStyle("AxiaBitLabel", parent=normal, fontName="Helvetica-Bold", fontSize=7.1, leading=8.5)
    header = ParagraphStyle("AxiaBitHeader", parent=normal, fontName="Helvetica-Bold", fontSize=7.3, leading=8.7, textColor=colors.white, alignment=0)
    title_style = ParagraphStyle("AxiaBitTitle", parent=normal, fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.HexColor("#102A43"), alignment=1)
    subtitle_style = ParagraphStyle("AxiaBitSub", parent=normal, fontSize=7.7, leading=9.2, alignment=1)

    def text(*keys, fallback=""):
        for key in keys:
            value = str(datos.get(key) or "").strip()
            if value:
                return value
        return fallback

    def p(value, style=normal, conservar_saltos=False):
        contenido = html_escape(str(value or ""))
        if conservar_saltos:
            contenido = contenido.replace("\r\n", "\n").replace("\r", "\n")
            contenido = contenido.replace("\n", "<br/>")
        return Paragraph(contenido, style)

    def lp(value):
        return Paragraph(html_escape(str(value or "")).upper(), label)

    ancho_bitacora = 6.55 * inch
    story = []
    folio = text("Folio Bitácora", "Folio de bitácora", "Folio BIT")
    fecha = text("Fecha")

    rows = [
        [lp("Folio Bitácora"), p(folio), lp("Fecha"), p(fecha)],
        [lp("No. ACO"), p(text("Número de ACO", "No. ACO", "ACO")), lp("Levantamiento"), p(text("Levantamiento"))],
        [lp("OT"), p(text("OT", "Orden de Trabajo")), lp("Cliente"), p(text("Cliente", "Nombre del Cliente"))],
        [lp("Dirección de Servicio"), p(text("Dirección de Servicio", "Dirección de la sucursal")), "", ""],
        [lp("Nombre del Encargado"), p(text("Nombre del Encargado", "Encargado del proyecto AXIA")), lp("Técnico(s)"), p(text("Técnico(s)", "Técnico en sitio"))],
        [lp("Hora de Llegada"), p(text("Hora de Llegada")), lp("Hora de Salida"), p(text("Hora de Salida"))],
    ]
    general = Table(rows, colWidths=[1.25*inch, 2.05*inch, 1.14*inch, 2.11*inch], hAlign="LEFT")
    general.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.45, BORDER),
        ("BACKGROUND", (0,0), (0,-1), LIGHT_BLUE),
        ("BACKGROUND", (2,0), (2,-1), LIGHT_BLUE),
        ("SPAN", (1,2), (3,2)),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(general)
    story.append(Spacer(1, 8))

    desc_header = Table([[Paragraph("DESCRIPCIÓN DEL SERVICIO", header)]], colWidths=[ancho_bitacora], hAlign="LEFT")
    desc_header.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BLUE),
        ("BOX", (0,0), (-1,-1), 0.45, BORDER),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(desc_header)
    descripcion = text("Descripción del Servicio", "Descripción")
    lineas_descripcion = str(descripcion or "Sin descripción registrada.").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    filas_descripcion = [
        [p(linea)] if linea else [Spacer(1, normal.leading)]
        for linea in lineas_descripcion
    ]
    desc_body = LongTable(filas_descripcion, colWidths=[ancho_bitacora], hAlign="LEFT", splitByRow=1)
    desc_body.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.45, BORDER),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.5),
    ]))
    story.append(desc_body)
    story.append(Spacer(1, 8))

    avance = text("Porcentaje de Avance", "Porcentaje de avance", fallback="0%")
    avance_tabla = Table([[lp("Porcentaje de Avance"), p(avance)]], colWidths=[1.55*inch, 2.05*inch], hAlign="RIGHT")
    avance_tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.45, BORDER),
        ("BACKGROUND", (0,0), (0,0), LIGHT_BLUE),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    # El resumen conserva su tamaño compacto y termina en el mismo margen derecho
    # que el resto de las secciones, sin depender del ancho total de la página.
    avance_alineado = Table(
        [["", avance_tabla]],
        colWidths=[ancho_bitacora - 3.60 * inch, 3.60 * inch],
        hAlign="LEFT",
    )
    avance_alineado.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(avance_alineado)

    evidencias_raw = datos.get("Evidencia Fotográfica") or datos.get("Evidencias Fotográficas") or datos.get("Fotos") or []
    if isinstance(evidencias_raw, str):
        valor = evidencias_raw.strip()
        if valor:
            try:
                evidencias_raw = json.loads(valor)
            except Exception:
                evidencias_raw = [valor]
        else:
            evidencias_raw = []
    if isinstance(evidencias_raw, dict):
        evidencias_raw = [evidencias_raw]

    from services.pdf_fotos_inteligentes import FotoPdf, construir_filas_fotos

    def _imagen_evidencia(item):
        nombre = "Evidencia"
        origen = ""
        try:
            if isinstance(item, dict):
                nombre = str(item.get("nombre") or item.get("name") or item.get("storage_path") or "Evidencia").strip()
                origen = str(item.get("url") or item.get("public_url") or item.get("ruta") or item.get("path") or "").strip()
            else:
                origen = str(item or "").strip()
                if origen:
                    nombre = Path(origen).name or "Evidencia"
            if not origen and not (isinstance(item, dict) and item.get("storage_path")):
                return None, nombre

            if origen.lower().startswith("url:"):
                origen = origen.split(":", 1)[1].strip()

            contenido = None
            ruta_local = Path(origen)
            if ruta_local.is_file():
                contenido = ruta_local.read_bytes()
            elif origen.lower().startswith(("http://", "https://")):
                try:
                    import requests
                    respuesta = requests.get(origen, timeout=12)
                    respuesta.raise_for_status()
                    contenido = respuesta.content
                except Exception:
                    if isinstance(item, dict) and str(item.get("storage_path") or "").strip():
                        from supabase_config import supabase
                        contenido = supabase.storage.from_("bitacoras-evidencias").download(
                            str(item.get("storage_path") or "").strip()
                        )
                    else:
                        raise
            elif isinstance(item, dict) and str(item.get("storage_path") or "").strip():
                from supabase_config import supabase
                contenido = supabase.storage.from_("bitacoras-evidencias").download(
                    str(item.get("storage_path") or "").strip()
                )
            if not contenido:
                return None, nombre

            with Image.open(io.BytesIO(contenido)) as img_src:
                img = ImageOps.exif_transpose(img_src)
                img.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
                ancho_px, alto_px = img.size
                salida = io.BytesIO()
                extension = Path(nombre).suffix.lower()
                if extension in (".jpg", ".jpeg"):
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(salida, format="JPEG", quality=88, optimize=True)
                else:
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGB")
                    img.save(salida, format="PNG", optimize=True)

            return FotoPdf(
                contenido=salida.getvalue(), nombre=nombre,
                ancho_px=ancho_px, alto_px=alto_px,
            ), nombre
        except Exception:
            logger.warning("No se pudo incorporar una evidencia fotográfica al PDF de Bitácora: %s", nombre, exc_info=True)
            return None, nombre

    fotos_preparadas = []
    for item in evidencias_raw or []:
        foto, _nombre = _imagen_evidencia(item)
        if foto is not None:
            fotos_preparadas.append(foto)

    if fotos_preparadas:
        story.append(Spacer(1, 8))
        fotos_header = Table([[Paragraph("EVIDENCIA FOTOGRÁFICA", header)]], colWidths=[ancho_bitacora], hAlign="LEFT")
        fotos_header.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), BLUE),
            ("BOX", (0,0), (-1,-1), 0.45, BORDER),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        filas_fotos = construir_filas_fotos(
            fotos_preparadas, estilo_texto=normal,
            color_borde=BORDER, color_pie=LIGHT_BLUE,
            ancho_total=ancho_bitacora,
            alineacion="LEFT",
        )

        story.append(KeepTogether([fotos_header, Spacer(1, 5), filas_fotos[0]]))
        story.extend(filas_fotos[1:])

    try:
        doc = SimpleDocTemplate(
            str(ruta), pagesize=letter,
            rightMargin=BasePdfGenerator.RIGHT_MARGIN,
            leftMargin=BasePdfGenerator.LEFT_MARGIN,
            topMargin=BasePdfGenerator.TOP_MARGIN,
            bottomMargin=BasePdfGenerator.BOTTOM_MARGIN,
        )
        title = "Bitácora de Avance"
        doc.title = f"AXIA - {title}"
        doc.author = "AXIA Comunicaciones S.A. de C.V."
        doc.subject = title
        doc.creator = "Sistema AXIA"

        def _on_page(canvas, document):
            BasePdfGenerator.draw_page(canvas, document, title=title)

        doc.build(
            story,
            onFirstPage=_on_page,
            onLaterPages=_on_page,
            canvasmaker=BasePdfGenerator.canvas_factory(title),
        )
        if abrir:
            try:
                os.startfile(str(ruta))
            except AttributeError:
                import subprocess
                subprocess.Popen(["xdg-open", str(ruta)])
            except Exception:
                logger.debug("No fue posible abrir el PDF automáticamente.", exc_info=True)
        return str(ruta)
    except Exception as error:
        messagebox.showerror("Preview PDF", f"No se pudo generar el preview.\n\n{error}")
        logger.exception("Error generando Bitácora de Avance PDF maestra")
        return False

def _generar_pdf_base(titulo, datos, secciones_tabla=None, firma_base64=None, firma_tecnico_base64=None, mostrar_firmas=None, ruta_salida=None, abrir=True):
    if str(titulo or "").strip().casefold() == "orden de servicio":
        resultado = _generar_pdf_orden_servicio_axia(
            datos, firma_base64=firma_base64, ruta_salida=ruta_salida, abrir=abrir
        )
        return _auditar_pdf(titulo, resultado, ruta_salida, abrir)
    if str(titulo or "").strip().casefold() == "orden de trabajo":
        resultado = _generar_pdf_orden_trabajo_axia(
            datos, secciones_tabla=secciones_tabla, ruta_salida=ruta_salida, abrir=abrir
        )
        return _auditar_pdf(titulo, resultado, ruta_salida, abrir)
    if str(titulo or "").strip().casefold() in ("bitácora de avance", "bitacora de avance"):
        resultado = _generar_pdf_bitacora_avance_axia(datos, ruta_salida=ruta_salida, abrir=abrir)
        return _auditar_pdf(titulo, resultado, ruta_salida, abrir)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, LongTable, TableStyle, Image as RLImage, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
    except Exception as error:
        messagebox.showerror("Preview PDF", f"No está instalado reportlab.\n\n{error}")
        return False

    def _valor_por_clave(posibles):
        for clave in posibles:
            if clave in datos and str(datos.get(clave) or "").strip():
                return str(datos.get(clave) or "").strip()
        return ""

    folio = _valor_por_clave(["Folio", "Folio OS", "Folio OT", "Folio BIT", "Folio OBC", "Folio LEV", "Folio de Levantamiento", "Folio Bitácora", "Folio de bitácora"])
    fecha = _valor_por_clave(["Fecha"])
    if ruta_salida:
        ruta = Path(ruta_salida)
        ruta.parent.mkdir(parents=True, exist_ok=True)
    else:
        ruta = Path(tempfile.gettempdir()) / f"AXIA_preview_{titulo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    try:
        doc = SimpleDocTemplate(
            str(ruta), pagesize=letter,
            rightMargin=BasePdfGenerator.RIGHT_MARGIN,
            leftMargin=BasePdfGenerator.LEFT_MARGIN,
            topMargin=BasePdfGenerator.TOP_MARGIN,
            bottomMargin=BasePdfGenerator.BOTTOM_MARGIN,
        )
        estilos = getSampleStyleSheet()
        estilos_axia = BasePdfGenerator.styles()
        estilo_normal = estilos_axia["normal"]
        estilo_titulo = estilos_axia["title"]
        estilo_sub = estilos_axia["subtitle"]
        estilo_encabezado_tabla = estilos_axia["table_header"]

        contenido = []

        centro = [
            Paragraph(f"<b>{titulo}</b>", estilo_titulo),
            Paragraph(
                f"Folio: <b>{folio or 'Pendiente'}</b> &nbsp;&nbsp; Fecha: <b>{fecha or 'Pendiente'}</b>",
                estilo_sub,
            ),
        ]
        encabezado = Table([[centro]], colWidths=[6.90 * inch])
        encabezado.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        contenido.append(encabezado)
        contenido.append(Spacer(1, 3))

        def _limpiar_titulo_seccion(texto):
            limpio = str(texto or "").replace("---", "").strip()
            limpio = " ".join(limpio.split())
            return limpio

        def _parsear_detalle_tecnico(texto):
            secciones = []
            actual = None
            for linea in str(texto or "").splitlines():
                linea = linea.strip()
                if not linea:
                    continue
                if linea.startswith("---") and linea.endswith("---"):
                    titulo = _limpiar_titulo_seccion(linea)
                    actual = {"titulo": titulo, "lineas": []}
                    secciones.append(actual)
                elif actual is not None:
                    actual["lineas"].append(linea)
                else:
                    actual = {"titulo": "DETALLE TÉCNICO", "lineas": [linea]}
                    secciones.append(actual)
            return secciones

        detalle_tecnico = str(datos.get("Detalle técnico") or "").strip() if isinstance(datos, dict) else ""
        secciones_detalle = _parsear_detalle_tecnico(detalle_tecnico) if detalle_tecnico else []

        def _tabla_pares_compacta(pares, columnas=3):
            if not pares:
                return None
            filas_tabla = []
            fila_actual_pdf = []
            for etiqueta, valor in pares:
                texto_valor = str(valor or "").strip()
                celda = Paragraph(f"<b>{etiqueta}</b><br/>{texto_valor or '-'}", estilo_normal)
                fila_actual_pdf.append(celda)
                if len(fila_actual_pdf) == columnas:
                    filas_tabla.append(fila_actual_pdf)
                    fila_actual_pdf = []
            if fila_actual_pdf:
                while len(fila_actual_pdf) < columnas:
                    fila_actual_pdf.append(Paragraph("", estilo_normal))
                filas_tabla.append(fila_actual_pdf)

            ancho_total = 6.90 * inch
            tabla = Table(filas_tabla, colWidths=[ancho_total / columnas] * columnas)
            tabla.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C2CC")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            return tabla

        pares_cortos = []
        bloques_largos = []
        for k, v in datos.items():
            if str(k).startswith("__"):
                continue
            if k == "Detalle técnico" and secciones_detalle:
                continue
            if isinstance(v, (list, dict)):
                continue
            valor = str(v or "").strip()
            if k in ("Descripción", "Observaciones", "Descripción detallada del servicio") or len(valor) > 95:
                bloques_largos.append((k, valor))
            else:
                pares_cortos.append((k, valor))

        columnas_generales = 4
        tabla_general = _tabla_pares_compacta(pares_cortos, columnas=columnas_generales)
        if tabla_general:
            contenido.append(tabla_general)
            contenido.append(Spacer(1, 3))

        if bloques_largos:
            tabla_largos = Table(
                [[Paragraph(f"<b>{k}</b>", estilo_normal), Paragraph(v or "-", estilo_normal)] for k, v in bloques_largos],
                colWidths=[1.55 * inch, 5.35 * inch]
            )
            tabla_largos.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C2CC")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            contenido.append(tabla_largos)
            contenido.append(Spacer(1, 5))

        if secciones_detalle:
            estilo_seccion = ParagraphStyle(
                "AxiaSection",
                parent=estilos["Heading2"],
                fontSize=8.5,
                leading=10,
                textColor=colors.HexColor("#1F4E79"),
                spaceAfter=4,
            )

            for indice, seccion in enumerate(secciones_detalle):
                if indice > 0:
                    contenido.append(Spacer(1, 4))

                titulo = seccion.get("titulo", "SECCIÓN")
                lineas = seccion.get("lineas", [])

                if titulo.upper().startswith("LEVANTAMIENTO "):
                    valor = titulo[len("LEVANTAMIENTO "):].strip()
                    titulo_pdf = "LEVANTAMIENTO: <b>%s</b>" % valor
                else:
                    titulo_pdf = titulo.upper()

                encabezado_seccion = Table(
                    [[Paragraph(titulo_pdf, estilo_seccion)]],
                    colWidths=[6.90 * inch],
                )
                encabezado_seccion.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2F7")),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C2CC")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]))
                contenido.append(encabezado_seccion)
                contenido.append(Spacer(1, 3))

                filas = []
                parrafos = []
                for linea in lineas:
                    if ":" in linea:
                        etiqueta, valor = linea.split(":", 1)
                        filas.append([Paragraph(f"<b>{etiqueta.strip()}</b>", estilo_normal), Paragraph(valor.strip(), estilo_normal)])
                    else:
                        parrafos.append(Paragraph(linea, estilo_normal))

                bloque_seccion = []
                if filas:
                    pares_seccion = []
                    filas_largas = []
                    for fila_pdf in filas:
                        try:
                            etiqueta_txt = fila_pdf[0].getPlainText().strip()
                            valor_txt = fila_pdf[1].getPlainText().strip()
                        except Exception:
                            etiqueta_txt = ""
                            valor_txt = ""
                        if len(valor_txt) > 80:
                            filas_largas.append(fila_pdf)
                        else:
                            pares_seccion.append((etiqueta_txt, valor_txt))

                    tabla_compacta = _tabla_pares_compacta(pares_seccion, columnas=3)
                    if tabla_compacta:
                        bloque_seccion.append(tabla_compacta)

                    if filas_largas:
                        if tabla_compacta:
                            bloque_seccion.append(Spacer(1, 2))
                        tabla_detalle = Table(filas_largas, colWidths=[2.05 * inch, 4.85 * inch])
                        tabla_detalle.setStyle(TableStyle([
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C2CC")),
                            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F7FB")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ]))
                        bloque_seccion.append(tabla_detalle)

                for parrafo in parrafos:
                    bloque_seccion.append(parrafo)
                    bloque_seccion.append(Spacer(1, 2))

                if not filas and not parrafos:
                    bloque_seccion.append(Paragraph("Sin información adicional.", estilo_normal))

                contenido.extend(bloque_seccion)

        anotacion_b64 = str(datos.get("__anotacion_plano_base64") or "").strip() if isinstance(datos, dict) else ""
        if anotacion_b64:
            try:
                contenido.append(Spacer(1, 5))
                encabezado_anotacion = Table([[Paragraph("ANOTACIONES TIPO PLANO", estilo_encabezado_tabla)]], colWidths=[6.90 * inch])
                encabezado_anotacion.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#1F4E79")),
                    ("TEXTCOLOR", (0,0), (-1,-1), colors.white),
                    ("LEFTPADDING", (0,0), (-1,-1), 4),
                    ("TOPPADDING", (0,0), (-1,-1), 3),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                ]))
                contenido.append(encabezado_anotacion)
                contenido.append(Spacer(1, 3))
                tmp_img = Path(tempfile.gettempdir()) / f"axia_anotacion_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
                tmp_img.write_bytes(base64.b64decode(anotacion_b64))
                imagen = RLImage(str(tmp_img), width=6.75*inch, height=3.72*inch)
                contenido.append(imagen)
            except Exception:
                logger.warning("No fue posible insertar la anotación tipo plano en el PDF.", exc_info=True)

        evidencias_pdf = datos.get("__evidencias_fotograficas") or [] if isinstance(datos, dict) else []
        if isinstance(evidencias_pdf, str):
            try:
                evidencias_pdf = json.loads(evidencias_pdf)
            except Exception:
                evidencias_pdf = [evidencias_pdf] if evidencias_pdf.strip() else []
        if isinstance(evidencias_pdf, dict):
            evidencias_pdf = [evidencias_pdf]
        tarjetas_fotos = []
        for item in evidencias_pdf or []:
            try:
                origen = str(item.get("ruta") or item.get("path") or item.get("url") or "").strip() if isinstance(item, dict) else str(item or "").strip()
                storage_path = str(item.get("storage_path") or "").strip() if isinstance(item, dict) else ""
                raw = None
                if origen and Path(origen).is_file():
                    raw = Path(origen).read_bytes()
                elif origen.lower().startswith(("http://", "https://")):
                    try:
                        import requests
                        resp = requests.get(origen, timeout=12)
                        resp.raise_for_status()
                        raw = resp.content
                    except Exception:
                        pass
                if not raw and storage_path:
                    from supabase_config import supabase
                    raw = supabase.storage.from_("bitacoras-evidencias").download(storage_path)
                if not raw:
                    continue
                with Image.open(io.BytesIO(raw)) as im0:
                    im = ImageOps.exif_transpose(im0)
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGB")
                    buf = io.BytesIO()
                    im.save(buf, format="PNG")
                    buf.seek(0)
                    iw, ih = im.size
                max_w, max_h = 3.18*inch, 2.18*inch
                escala = min(max_w/max(iw,1), max_h/max(ih,1))
                foto = RLImage(buf, width=max(1, iw*escala), height=max(1, ih*escala))
                tarjeta = Table([[foto]], colWidths=[3.30*inch])
                tarjeta.setStyle(TableStyle([
                    ("BOX", (0,0), (-1,-1), 0.35, colors.HexColor("#8FA3B5")),
                    ("ALIGN", (0,0), (-1,-1), "CENTER"),
                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                    ("LEFTPADDING", (0,0), (-1,-1), 4),
                    ("RIGHTPADDING", (0,0), (-1,-1), 4),
                    ("TOPPADDING", (0,0), (-1,-1), 4),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ]))
                tarjetas_fotos.append(tarjeta)
            except Exception:
                logger.warning("No fue posible insertar una evidencia fotográfica en el PDF.", exc_info=True)
        if tarjetas_fotos:
            contenido.append(Spacer(1, 5))
            encabezado_fotos = Table([[Paragraph("EVIDENCIA FOTOGRÁFICA", estilo_encabezado_tabla)]], colWidths=[6.90 * inch])
            encabezado_fotos.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0,0), (-1,-1), colors.white),
                ("LEFTPADDING", (0,0), (-1,-1), 4),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            contenido.append(encabezado_fotos)
            filas_fotos = []
            for i in range(0, len(tarjetas_fotos), 2):
                filas_fotos.append([tarjetas_fotos[i], tarjetas_fotos[i+1] if i+1 < len(tarjetas_fotos) else ""])
            tabla_fotos = Table(filas_fotos, colWidths=[3.45*inch, 3.45*inch])
            tabla_fotos.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
            contenido.append(Spacer(1, 3))
            contenido.append(tabla_fotos)

        from services.pdf_canalizacion_agrupada import desglosar_secciones_pdf
        for nombre, columnas, registros in desglosar_secciones_pdf(secciones_tabla):
            if not registros and columnas is not None:
                continue
            contenido.append(Spacer(1, 3))
            encabezado_tabla = Table([[Paragraph(str(nombre).upper(), ParagraphStyle("AxiaTableSection", parent=estilos["Heading3"], fontSize=8.5, leading=10, textColor=colors.HexColor("#1F4E79")))]], colWidths=[6.90 * inch])
            encabezado_tabla.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2F7")),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C2CC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            contenido.append(encabezado_tabla)

            if columnas is None:
                continue
            contenido.append(Spacer(1, 3))

            def _fragmentar_celda(valor, limite):
                texto = str(valor or "").strip()
                if not texto:
                    return [""]
                fragmentos = []
                for linea in texto.splitlines() or [texto]:
                    restante = linea.strip()
                    if not restante:
                        fragmentos.append("")
                        continue
                    while len(restante) > limite:
                        corte = restante.rfind(" ", 0, limite + 1)
                        if corte < max(20, limite // 3):
                            corte = limite
                        fragmentos.append(restante[:corte].strip())
                        restante = restante[corte:].strip()
                    if restante:
                        fragmentos.append(restante)
                return fragmentos or [""]

            limite_celda = 120 if len(columnas) >= 7 else 190
            filas_seguras = []
            for registro in registros:
                fragmentos_por_columna = {
                    columna: _fragmentar_celda(registro.get(columna, ""), limite_celda)
                    for columna in columnas
                }
                total_fragmentos = max(len(v) for v in fragmentos_por_columna.values())
                for indice in range(total_fragmentos):
                    fila_continuacion = {}
                    for columna in columnas:
                        partes = fragmentos_por_columna[columna]
                        fila_continuacion[columna] = partes[indice] if indice < len(partes) else ""
                    filas_seguras.append(fila_continuacion)

            data = [[Paragraph(str(c), estilo_encabezado_tabla) for c in columnas]]
            for r in filas_seguras:
                data.append([Paragraph(str(r.get(c, "") or ""), estilo_normal) for c in columnas])

            ancho_total = 6.90 * inch
            pesos = []
            for columna in columnas:
                clave_col = str(columna).strip().casefold()
                if clave_col in {"concepto", "descripción", "descripcion", "actividades", "observaciones"}:
                    pesos.append(3.2)
                elif clave_col in {"partida", "parte", "cantidad", "unidad", "día", "dia", "total"}:
                    pesos.append(0.8)
                else:
                    pesos.append(1.25)
            suma_pesos = sum(pesos) or len(columnas)
            anchos = [ancho_total * peso / suma_pesos for peso in pesos]
            t = LongTable(data, colWidths=anchos, repeatRows=1, splitByRow=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]))
            contenido.append(t)
            contenido.append(Spacer(1, 5))

        if mostrar_firmas is None:
            mostrar_firmas = "levantamiento" not in str(titulo or "").lower()

        if mostrar_firmas:
            firma_cliente_obj = Paragraph("<br/><br/><br/>______________________________<br/><b>Firma Cliente</b>", estilo_sub)
            if firma_base64:
                try:
                    img_bytes = base64.b64decode(firma_base64)
                    img_path = Path(tempfile.gettempdir()) / f"firma_axia_{datetime.now().strftime('%H%M%S')}.png"
                    img_path.write_bytes(img_bytes)
                    firma_cliente_obj = RLImage(str(img_path), width=2.8 * inch, height=0.95 * inch)
                except Exception:
                    firma_cliente_obj = Paragraph("Firma Cliente capturada", estilo_sub)

            firma_tecnico_obj = Paragraph("<br/><br/><br/>______________________________<br/><b>Firma Técnico</b>", estilo_sub)
            if firma_tecnico_base64:
                try:
                    img_bytes = base64.b64decode(firma_tecnico_base64)
                    img_path = Path(tempfile.gettempdir()) / f"firma_tecnico_axia_{datetime.now().strftime('%H%M%S')}.png"
                    img_path.write_bytes(img_bytes)
                    firma_tecnico_obj = RLImage(str(img_path), width=2.8 * inch, height=0.95 * inch)
                except Exception:
                    firma_tecnico_obj = Paragraph("Firma Técnico capturada", estilo_sub)

            firmas = Table([
                [firma_cliente_obj, firma_tecnico_obj]
            ], colWidths=[3.35 * inch, 3.35 * inch])
            firmas.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
            ]))
            contenido.append(Spacer(1, 8))
            contenido.append(firmas)

        def _pagina_corporativa(canvas, documento):
            BasePdfGenerator.draw_page(canvas, documento, title=titulo)

        doc.title = f"AXIA - {titulo}"
        doc.author = "AXIA Comunicaciones S.A. de C.V."
        doc.subject = f"Formato operativo estandarizado: {titulo}"
        doc.creator = "Sistema AXIA"
        doc.build(
            contenido,
            canvasmaker=BasePdfGenerator.canvas_factory(titulo),
            onFirstPage=_pagina_corporativa,
            onLaterPages=_pagina_corporativa,
        )
        if abrir:
            os.startfile(str(ruta)) if os.name == "nt" else os.system(f'xdg-open "{ruta}" >/dev/null 2>&1 &')
        return str(ruta)
    except Exception as error:
        messagebox.showerror("Preview PDF", f"No se pudo generar el preview.\n\n{error}")
        return False



def generar_pdf_preview(titulo, datos, secciones_tabla=None, firma_base64=None, firma_tecnico_base64=None, mostrar_firmas=None, ruta_salida=None, abrir=True):
    if str(titulo or "").strip().casefold() == "orden de servicio":
        resultado = _generar_pdf_orden_servicio_axia(
            datos, firma_base64=firma_base64, ruta_salida=ruta_salida, abrir=abrir
        )
        return _auditar_pdf(titulo, resultado, ruta_salida, abrir)
    if str(titulo or "").strip().casefold() == "orden de trabajo":
        resultado = _generar_pdf_orden_trabajo_axia(
            datos, secciones_tabla=secciones_tabla, ruta_salida=ruta_salida, abrir=abrir
        )
        return _auditar_pdf(titulo, resultado, ruta_salida, abrir)
    if str(titulo or "").strip().casefold() in ("bitácora de avance", "bitacora de avance"):
        resultado = _generar_pdf_bitacora_avance_axia(datos, ruta_salida=ruta_salida, abrir=abrir)
        return _auditar_pdf(titulo, resultado, ruta_salida, abrir)

    from services.axia_pdf_engine import AxiaPdfEngine
    kwargs = dict(
        secciones_tabla=secciones_tabla,
        firma_base64=firma_base64,
        firma_tecnico_base64=firma_tecnico_base64,
        mostrar_firmas=mostrar_firmas,
    )
    if ruta_salida is None and abrir:
        resultado = AxiaPdfEngine.preview(titulo, datos, **kwargs)
        return _auditar_pdf(titulo, resultado, ruta_salida, abrir)
    if ruta_salida is None:
        ruta_salida = AxiaPdfEngine._preview_path(titulo)
    request = AxiaPdfEngine.prepare(titulo=titulo, datos=datos, **kwargs)
    if abrir:
        from dataclasses import replace
        resultado = AxiaPdfEngine.render(replace(request, ruta_salida=ruta_salida, abrir=True))
        return _auditar_pdf(titulo, resultado, ruta_salida, abrir)
    resultado = AxiaPdfEngine.save_request(request, ruta_salida)
    return _auditar_pdf(titulo, resultado, ruta_salida, abrir)


def enfocar_inicio_formulario(scroll_widget=None, primer_widget=None, delay=180):
    root = None
    if primer_widget is not None:
        root = primer_widget.winfo_toplevel()
    elif scroll_widget is not None:
        root = scroll_widget.winfo_toplevel()
    if root is None:
        return

    def _run():
        try:
            if scroll_widget is not None and hasattr(scroll_widget, "_parent_canvas"):
                scroll_widget._parent_canvas.yview_moveto(0)
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    try:
        root.after(delay, _run)
    except Exception:
        logger.debug("Excepción recuperable controlada.", exc_info=True)


def generar_pdf_preview_async(parent, titulo, datos, **kwargs):
    from core.performance import run_in_background
    return run_in_background(
        lambda: generar_pdf_preview(titulo, datos, **kwargs),
        widget=parent,
        on_error=lambda exc: messagebox.showerror("Preview PDF", f"No fue posible generar el PDF.\n\n{exc}"),
        name="AXIA-pdf-preview",
    )