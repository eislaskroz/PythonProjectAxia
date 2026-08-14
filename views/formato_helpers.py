"""
Helpers visuales y de preview para formularios operativos AXIA.
"""
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

ENTRY_H = 30
OPTION_H = 30
LABEL_FONT = ("Montserrat", 10, "bold")
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
    """Editor gráfico básico tipo Paint para anotaciones de levantamiento.

    Herramientas: lápiz, borrador, línea, rectángulo y texto. La imagen se
    conserva como PNG base64 para poder persistirla directamente en Supabase.
    """
    win = Toplevel(parent)
    win.title(titulo)
    # Ventana compacta y adaptable: evita recortes en pantallas con escalado de Windows.
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    ww = min(1180, max(900, int(sw * 0.90)))
    wh = min(760, max(640, int(sh * 0.82)))
    win.geometry(f"{ww}x{wh}")
    win.minsize(900, 640)
    win.transient(parent.winfo_toplevel())
    win.grab_set()

    root = ctk.CTkFrame(win, fg_color=WHITE)
    root.pack(fill="both", expand=True, padx=8, pady=8)
    ctk.CTkLabel(root, text=titulo, font=("Montserrat", 17, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
    ctk.CTkLabel(root, text="Dibuja croquis, rutas, zonas, medidas o notas. Puedes usar mouse, touchpad o pantalla táctil.", font=SMALL_FONT, text_color=TEXT_SECONDARY).pack(anchor="w", pady=(0, 5))

    toolbar = ctk.CTkFrame(root, fg_color="#F8FAFC", corner_radius=10)
    toolbar.pack(fill="x", pady=(0, 6))
    for _col in range(7):
        toolbar.grid_columnconfigure(_col, weight=1, uniform="plano_tools")
    herramienta = ctk.StringVar(value="lapiz")

    # El lienzo conserva una proporción útil para croquis, dejando siempre
    # visibles la barra de herramientas y los botones inferiores.
    lienzo_w, lienzo_h = 980, 460
    valor_previo = str(variable_base64.get() or "").strip()
    if valor_previo:
        try:
            img = Image.open(io.BytesIO(base64.b64decode(valor_previo))).convert("RGB").resize((lienzo_w, lienzo_h))
        except Exception:
            img = Image.new("RGB", (lienzo_w, lienzo_h), "white")
    else:
        img = Image.new("RGB", (lienzo_w, lienzo_h), "white")
    draw = ImageDraw.Draw(img)
    undo_stack = []
    canvas = Canvas(root, width=lienzo_w, height=lienzo_h, bg="white", highlightthickness=1, highlightbackground="#AAB7C4")
    canvas.pack(fill="both", expand=True, pady=(0, 2))
    state = {"x": None, "y": None, "preview": None, "bg": None}

    def snapshot():
        undo_stack.append(img.copy())
        if len(undo_stack) > 30:
            del undo_stack[0]

    def mostrar_imagen_base():
        canvas.delete("all")
        state["bg"] = ImageTk.PhotoImage(img)
        canvas.create_image(0, 0, image=state["bg"], anchor="nw")

    def seleccionar(nombre):
        herramienta.set(nombre)

    botones = [
        ("✏ Lápiz", "lapiz"), ("⌫ Borrador", "borrador"),
        ("╱ Línea", "linea"), ("▭ Rectángulo", "rectangulo"), ("T Texto", "texto"),
    ]
    for i, (texto, nombre) in enumerate(botones):
        ctk.CTkButton(toolbar, text=texto, height=36, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=lambda n=nombre: seleccionar(n)).grid(row=0, column=i, padx=3, pady=5, sticky="ew")

    def deshacer():
        nonlocal img, draw
        if not undo_stack:
            return
        img = undo_stack.pop()
        draw = ImageDraw.Draw(img)
        mostrar_imagen_base()

    def limpiar():
        nonlocal img, draw
        snapshot()
        img = Image.new("RGB", (lienzo_w, lienzo_h), "white")
        draw = ImageDraw.Draw(img)
        mostrar_imagen_base()

    ctk.CTkButton(toolbar, text="↶ Deshacer", height=36, fg_color="#64748B", command=deshacer).grid(row=0, column=5, padx=3, pady=5, sticky="ew")
    ctk.CTkButton(toolbar, text="Limpiar", height=36, fg_color="#DC2626", hover_color="#B91C1C", command=limpiar).grid(row=0, column=6, padx=3, pady=5, sticky="ew")

    def iniciar(event):
        state["x"], state["y"] = max(0, min(lienzo_w-1, event.x)), max(0, min(lienzo_h-1, event.y))
        if herramienta.get() in ("lapiz", "borrador", "linea", "rectangulo"):
            snapshot()
        if herramienta.get() == "texto":
            texto = simpledialog.askstring("Texto", "Escribe la anotación:", parent=win)
            if texto:
                snapshot()
                try:
                    fuente = ImageFont.truetype("arial.ttf", 20)
                except Exception:
                    fuente = ImageFont.load_default()
                draw.text((state["x"], state["y"]), texto, fill="black", font=fuente)
                mostrar_imagen_base()
            state["x"], state["y"] = None, None

    def mover(event):
        if state["x"] is None:
            return
        x, y = max(0, min(lienzo_w-1, event.x)), max(0, min(lienzo_h-1, event.y))
        tool = herramienta.get()
        if tool in ("lapiz", "borrador"):
            color = "white" if tool == "borrador" else "black"
            ancho = 16 if tool == "borrador" else 3
            canvas.create_line(state["x"], state["y"], x, y, width=ancho, fill=color, capstyle="round", smooth=True)
            draw.line((state["x"], state["y"], x, y), fill=color, width=ancho)
            state["x"], state["y"] = x, y
        elif tool in ("linea", "rectangulo"):
            if state["preview"]:
                canvas.delete(state["preview"])
            if tool == "linea":
                state["preview"] = canvas.create_line(state["x"], state["y"], x, y, width=3, fill="black")
            else:
                state["preview"] = canvas.create_rectangle(state["x"], state["y"], x, y, width=3, outline="black")

    def soltar(event):
        if state["x"] is None:
            return
        x, y = max(0, min(lienzo_w-1, event.x)), max(0, min(lienzo_h-1, event.y))
        tool = herramienta.get()
        if tool == "linea":
            draw.line((state["x"], state["y"], x, y), fill="black", width=3)
            mostrar_imagen_base()
        elif tool == "rectangulo":
            x0, x1 = sorted((state["x"], x)); y0, y1 = sorted((state["y"], y))
            draw.rectangle((x0, y0, x1, y1), outline="black", width=3)
            mostrar_imagen_base()
        state["x"], state["y"], state["preview"] = None, None, None

    canvas.bind("<ButtonPress-1>", iniciar)
    canvas.bind("<B1-Motion>", mover)
    canvas.bind("<ButtonRelease-1>", soltar)
    mostrar_imagen_base()

    pie = ctk.CTkFrame(root, fg_color="transparent")
    pie.pack(fill="x", pady=(6, 0))
    def guardar():
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        variable_base64.set(base64.b64encode(buffer.getvalue()).decode("utf-8"))
        if on_change:
            on_change()
        win.destroy()
    ctk.CTkButton(pie, text="Cancelar", width=130, height=36, fg_color="#64748B", command=win.destroy).pack(side="left")
    ctk.CTkButton(pie, text="Guardar anotación", width=180, height=36, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=guardar).pack(side="right")

def firmar_en_popup(parent, variable_firma_base64, on_change=None, titulo="Firma del cliente"):
    """Abre una ventana para capturar firma y guardarla como PNG base64."""
    win = Toplevel(parent)
    win.title(titulo)
    win.geometry("620x340")
    win.transient(parent.winfo_toplevel())
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


def ruta_documentos_axia(subcarpeta="documentos"):
    """Devuelve una carpeta externa y estable para documentos generados por AXIA."""
    base = Path.home() / "Documents" / "AXIA" / str(subcarpeta or "documentos")
    base.mkdir(parents=True, exist_ok=True)
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
    """Genera y guarda un PDF definitivo sin abrir vista previa.

    Se utiliza después de guardar formularios en Supabase para conservar
    una copia local en Documents/AXIA/<subcarpeta>.
    """
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
    """Render corporativo específico para Orden de Servicio.

    Replica la estructura del formato físico AXIA: datos generales en dos bloques,
    descripción del servicio, observaciones, evaluación y firma del cliente.
    Los campos operativos pueden permanecer vacíos hasta que el formulario móvil
    de OS sea habilitado; el PDF conserva desde ahora la estructura definitiva.
    """
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

    def pair_table(rows, widths):
        t = Table([[p(a,label), p(b)] for a,b in rows], colWidths=widths)
        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.45, BORDER),
            ("BACKGROUND", (0,0), (0,-1), LIGHT_BLUE),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 2.5), ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ]))
        return t

    def box(title, body, height=None):
        """Caja corporativa cuya altura crece únicamente con el contenido.

        ``height`` se conserva sólo por compatibilidad con llamadas antiguas, pero
        no se fuerza una altura mínima. Así evitamos grandes áreas vacías cuando
        la descripción del servicio contiene una o dos líneas.
        """
        body_p = p(body, normal)
        t = Table([[p(title.upper(), header)], [body_p]], colWidths=[6.90*inch], rowHeights=[0.23*inch, None])
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
        ("Solicitante", text("Solicitante")), ("Correo", text("Correo")), ("Celular", text("Celular")),
        ("Hora de llegada", text("Hora de llegada")), ("Hora de salida", text("Hora de salida")),
    ]
    right_rows = [
        ("Tipo de Servicio", text("Tipo de Servicio")), ("No. ACO", text("ACO")),
        ("Supervisor", text("Supervisor")), ("Encargado AXIA", text("Encargado Servicio")),
        ("Técnicos", text("Técnicos")),
    ]
    left = pair_table(left_rows, [0.92*inch, 2.30*inch])
    right = pair_table(right_rows, [0.98*inch, 2.70*inch])
    top = Table([[left, right]], colWidths=[3.22*inch, 3.68*inch])
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
        colWidths=[1.725*inch] * 4,
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

    evaluacion_titulo = Table([[p("Evaluación del Servicio".upper(), header)]], colWidths=[6.90*inch])
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

    tarjetas_fotos = []
    foto_caption = ParagraphStyle("AxiaOsFotoCaption", parent=normal, fontSize=6.5, leading=8, alignment=1)
    for item in evidencias_raw or []:
        try:
            if isinstance(item, dict):
                nombre = str(item.get("nombre") or item.get("storage_path") or "Evidencia")
                origen = str(item.get("url") or item.get("ruta") or item.get("path") or "").strip()
            else:
                origen = str(item or "").strip(); nombre = Path(origen).name or "Evidencia"
            contenido = None
            if origen and Path(origen).is_file():
                contenido = Path(origen).read_bytes()
            elif origen.lower().startswith(("http://", "https://")):
                import requests
                resp = requests.get(origen, timeout=12); resp.raise_for_status(); contenido = resp.content
            elif isinstance(item, dict) and str(item.get("storage_path") or "").strip():
                from supabase_config import supabase
                contenido = supabase.storage.from_("bitacoras-evidencias").download(str(item.get("storage_path")).strip())
            if not contenido:
                continue
            with Image.open(io.BytesIO(contenido)) as src:
                img = ImageOps.exif_transpose(src)
                if img.mode not in ("RGB", "RGBA"): img = img.convert("RGB")
                buff = io.BytesIO(); img.save(buff, format="PNG", optimize=True); buff.seek(0)
                wpx, hpx = img.size
            max_w, max_h = 3.22*inch, 2.05*inch
            escala = min(max_w/max(wpx,1), max_h/max(hpx,1))
            foto = RLImage(buff, width=max(1,wpx*escala), height=max(1,hpx*escala))
            tarjeta = Table([[foto],[Paragraph(html_escape(nombre), foto_caption)]], colWidths=[3.30*inch])
            tarjeta.setStyle(TableStyle([
                ("BOX",(0,0),(-1,-1),0.4,BORDER),("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BACKGROUND",(0,1),(0,1),LIGHT_BLUE),
                ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
                ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
            ]))
            tarjetas_fotos.append(tarjeta)
        except Exception:
            logger.warning("No se pudo incorporar evidencia al PDF de Orden de Servicio", exc_info=True)
    if tarjetas_fotos:
        fotos_header = Table([[p("EVIDENCIA FOTOGRÁFICA", header)]], colWidths=[6.90*inch])
        fotos_header.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),BLUE),("BOX",(0,0),(-1,-1),0.45,BORDER)]))
        story.extend([fotos_header, Spacer(1,5)])
        for i in range(0, len(tarjetas_fotos), 2):
            der = tarjetas_fotos[i+1] if i+1 < len(tarjetas_fotos) else ""
            fila = Table([[tarjetas_fotos[i], der]], colWidths=[3.40*inch,3.40*inch], hAlign="CENTER")
            fila.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
            story.append(fila)
        story.append(Spacer(1,8))

    # Firma capturada desde el formulario operativo. Si todavía no existe, se
    # conserva el recuadro para que el formato sea visualmente definitivo.
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
    firma = Table([[firma_content], [p("FIRMA CLIENTE / ENCARGADO", center)]], colWidths=[2.0*inch], rowHeights=[0.68*inch, 0.24*inch])
    firma.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.55, BORDER), ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    firma_wrap = Table([["", firma, ""]], colWidths=[2.45*inch, 2.0*inch, 2.45*inch])
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
    """Render maestro de Orden de Trabajo con la misma identidad de los LEV.

    La OT reutiliza la retícula, barras azules, tablas compactas y fondo corporativo
    de los levantamientos. Preview, PDF administrativo y PDF posterior al guardado
    llegan a esta misma función, por lo que no existen dos diseños distintos.
    """
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

    # Misma paleta y jerarquía visual que la plantilla maestra de levantamientos.
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

    width = 6.90 * inch

    # Cabecera de la OT: misma retícula 4 columnas de los levantamientos.
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
        colWidths=[1.18 * inch, 2.05 * inch, 1.25 * inch, 2.42 * inch],
        repeatRows=0,
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

    # Servicio en bloque azul + celda de descripción, igual que las secciones del LEV.
    service = text("Asunto", "Descripción", "Servicio", fallback="Sin descripción capturada.")
    service_table = Table(
        [[Paragraph("SERVICIO", header)], [p(service, normal, "")]],
        colWidths=[width],
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

    # Cada colección de OT se presenta en una tabla independiente.
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

    # Compatibilidad: si una ruta antigua entrega _partidas_ot sin secciones,
    # se muestran como Materiales en lugar de perder información.
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
            colWidths=[0.58*inch, 0.70*inch, 0.72*inch, 0.92*inch, 1.05*inch, 2.93*inch],
            repeatRows=2, splitByRow=1,
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
    """Render corporativo específico para Bitácoras de Avance.

    Mantiene la identidad visual de Levantamientos y Órdenes de Trabajo y toma
    como referencia el formato operativo físico: datos vinculados LEV/ACO/OT,
    técnico(s), descripción del servicio y porcentaje acumulado de avance.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
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

    def p(value, style=normal):
        return Paragraph(html_escape(str(value or "")), style)

    def lp(value):
        return Paragraph(html_escape(str(value or "")).upper(), label)

    story = []
    folio = text("Folio Bitácora", "Folio de bitácora", "Folio BIT")
    fecha = text("Fecha")

    # Retícula equivalente a los datos generales de Levantamientos y OTs.
    rows = [
        [lp("Folio Bitácora"), p(folio), lp("Fecha"), p(fecha)],
        [lp("No. ACO"), p(text("Número de ACO", "No. ACO", "ACO")), lp("Levantamiento"), p(text("Levantamiento"))],
        [lp("OT"), p(text("OT", "Orden de Trabajo")), lp("Cliente"), p(text("Cliente", "Nombre del Cliente"))],
        [lp("Dirección de Servicio"), p(text("Dirección de Servicio", "Dirección de la sucursal")), "", ""],
        [lp("Nombre del Encargado"), p(text("Nombre del Encargado", "Encargado del proyecto AXIA")), lp("Técnico(s)"), p(text("Técnico(s)", "Técnico en sitio"))],
        [lp("Hora de Llegada"), p(text("Hora de Llegada")), lp("Hora de Salida"), p(text("Hora de Salida"))],
    ]
    general = Table(rows, colWidths=[1.32*inch, 2.16*inch, 1.20*inch, 2.22*inch])
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

    # Descripción como bloque de altura dinámica. La celda crece únicamente
    # según el contenido capturado, evitando un recuadro vacío de altura fija.
    desc_header = Table([[Paragraph("DESCRIPCIÓN DEL SERVICIO", header)]], colWidths=[6.90*inch])
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
    desc_body = Table([[p(descripcion or "Sin descripción registrada.")]], colWidths=[6.90*inch])
    desc_body.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.45, BORDER),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
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
    story.append(avance_tabla)

    # Evidencia fotográfica real. Acepta rutas locales (preview antes de guardar)
    # y los metadatos JSON guardados en Supabase Storage (PDF administrativo/definitivo).
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

    def _imagen_evidencia(item):
        """Devuelve (flowable, nombre) o (None, nombre) sin romper el PDF."""
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
            if not origen:
                return None, nombre

            # Algunas respuestas antiguas podían persistir el prefijo visible "Url:".
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
                    # Si el bucket deja de ser público, intentamos descargar por
                    # storage_path usando la sesión de Supabase configurada en AXIA.
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

            # Normalizamos a PNG para que ReportLab soporte de manera uniforme
            # JPG, PNG y WEBP, además de respetar orientación EXIF de celulares.
            with Image.open(io.BytesIO(contenido)) as img_src:
                img = ImageOps.exif_transpose(img_src)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                png_buffer = io.BytesIO()
                img.save(png_buffer, format="PNG", optimize=True)
                png_buffer.seek(0)
                ancho_px, alto_px = img.size

            max_w, max_h = 3.22 * inch, 2.18 * inch
            escala = min(max_w / max(ancho_px, 1), max_h / max(alto_px, 1))
            # Las dimensiones de ReportLab son puntos; 1 px ~= 1 pt es suficiente
            # aquí porque el objetivo es encajar la foto sin deformarla.
            ancho = max(1, ancho_px * escala)
            alto = max(1, alto_px * escala)
            return RLImage(png_buffer, width=ancho, height=alto), nombre
        except Exception:
            logger.warning("No se pudo incorporar una evidencia fotográfica al PDF de Bitácora: %s", nombre, exc_info=True)
            return None, nombre

    tarjetas = []
    caption_style = ParagraphStyle(
        "AxiaBitFotoCaption", parent=normal, fontSize=6.6, leading=8, alignment=1, textColor=TEXT
    )
    for item in evidencias_raw or []:
        imagen, nombre = _imagen_evidencia(item)
        if imagen is None:
            continue
        tarjeta = Table(
            [[imagen], [Paragraph(html_escape(nombre), caption_style)]],
            colWidths=[3.30 * inch],
        )
        tarjeta.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.40, BORDER),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("BACKGROUND", (0,1), (0,1), LIGHT_BLUE),
        ]))
        tarjetas.append(tarjeta)

    if tarjetas:
        story.append(Spacer(1, 10))
        fotos_header = Table([[Paragraph("EVIDENCIA FOTOGRÁFICA", header)]], colWidths=[6.90 * inch])
        fotos_header.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), BLUE),
            ("BOX", (0,0), (-1,-1), 0.45, BORDER),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        filas_fotos = []
        for i in range(0, len(tarjetas), 2):
            izquierda = tarjetas[i]
            derecha = tarjetas[i + 1] if i + 1 < len(tarjetas) else ""
            fila = Table([[izquierda, derecha]], colWidths=[3.40 * inch, 3.40 * inch], hAlign="CENTER")
            fila.setStyle(TableStyle([
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 3),
                ("RIGHTPADDING", (0,0), (-1,-1), 3),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ]))
            filas_fotos.append(fila)

        # Evita que el encabezado quede huérfano al pie de una página.
        # El título de la sección viaja siempre junto con la primera fila de fotos.
        story.append(KeepTogether([fotos_header, Spacer(1, 5), filas_fotos[0]]))
        for fila in filas_fotos[1:]:
            story.append(fila)

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
    """Genera PDF temporal y lo abre con el visor predeterminado.

    El PDF incluye encabezado operativo, folio, fecha y zona de firmas
    cuando corresponda. La plantilla corporativa se aplica en cada página.
    """
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
            """Convierte bloques tipo '--- SECCION ---' en secciones PDF ordenadas."""
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
            """Construye tabla compacta de pares etiqueta/valor en 2 o 3 columnas visuales."""
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
            if k in ("Descripción", "Observaciones") or len(valor) > 95:
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
                # No se fuerza salto de página entre secciones.
                # Se deja únicamente separación visual para aprovechar la hoja.
                if indice > 0:
                    contenido.append(Spacer(1, 4))

                titulo = seccion.get("titulo", "SECCIÓN")
                lineas = seccion.get("lineas", [])

                # Caso especial para que no aparezca como título corrido:
                # LEVANTAMIENTO Seguridad y Monitoreo -> LEVANTAMIENTO: Seguridad y Monitoreo
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
                    # Cada sección técnica usa una tabla compacta en 3 columnas cuando los valores son cortos.
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

        # Anotación gráfica tipo plano capturada desde el levantamiento.
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


        # Evidencias fotográficas opcionales del levantamiento/obra civil.
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

        for nombre, columnas, registros in (secciones_tabla or []):
            if not registros:
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
            contenido.append(Spacer(1, 3))
            # ReportLab no puede dividir una sola fila alta entre páginas.
            # Normalizamos cada registro en filas de continuación para que textos
            # extensos (principalmente Concepto/Descripción) siempre puedan paginarse.
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

            # El color de un Paragraph se define en su propio estilo; TableStyle(TEXTCOLOR)
            # no sobreescribe de forma fiable el textColor interno del Paragraph.
            # Usamos un estilo blanco explícito para asegurar contraste sobre el fondo azul.
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

        # Los levantamientos son documentos de diagnóstico y no requieren firmas.
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
    """Compatibilidad de formularios con AXIA PDF ENGINE Fase 4.

    Preview y guardado usan el mismo motor; esta función solo conserva la API
    histórica de las vistas existentes.

    Orden de Trabajo es una excepción intencional: utiliza el formato operativo
    oficial de AXIA (dos bloques superiores + servicio + tabla de partidas) y no
    el perfil genérico del PDF Engine.
    """
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
    """Coloca el scroll al inicio y el foco en el primer campo editable.

    Si no se envía primer_widget, recorre los hijos del formulario y busca
    el primer Entry / Textbox / OptionMenu disponible. Esto ayuda a que TAB
    siempre arranque desde arriba.
    """
    root = None
    if primer_widget is not None:
        root = primer_widget.winfo_toplevel()
    elif scroll_widget is not None:
        root = scroll_widget.winfo_toplevel()
    if root is None:
        return

    def _estado_normal(widget):
        try:
            return str(widget.cget("state")) != "disabled"
        except Exception:
            return True

    def _buscar_primer(widget):
        for child in widget.winfo_children():
            if isinstance(child, (ctk.CTkEntry, ctk.CTkTextbox, NativeComboBox)) and _estado_normal(child):
                return child
            encontrado = _buscar_primer(child)
            if encontrado is not None:
                return encontrado
        return None

    def _run():
        try:
            if scroll_widget is not None and hasattr(scroll_widget, "_parent_canvas"):
                scroll_widget._parent_canvas.yview_moveto(0)
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)
        try:
            objetivo = primer_widget or (_buscar_primer(scroll_widget) if scroll_widget is not None else None)
            if objetivo is not None:
                objetivo.focus_set()
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    try:
        root.after(delay, _run)
    except Exception:
        logger.debug("Excepción recuperable controlada.", exc_info=True)


def generar_pdf_preview_async(parent, titulo, datos, **kwargs):
    """Genera la vista previa fuera del hilo visual para evitar congelamientos."""
    from core.performance import run_in_background
    return run_in_background(
        lambda: generar_pdf_preview(titulo, datos, **kwargs),
        widget=parent,
        on_error=lambda exc: messagebox.showerror("Preview PDF", f"No fue posible generar el PDF.\n\n{exc}"),
        name="AXIA-pdf-preview",
    )
