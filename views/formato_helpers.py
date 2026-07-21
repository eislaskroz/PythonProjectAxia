"""
Helpers visuales y de preview para formularios operativos AXIA.
"""
from __future__ import annotations

import base64
import io
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from tkinter import Toplevel, Canvas, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw

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


def generar_pdf_preview(titulo, datos, secciones_tabla=None, firma_base64=None, firma_tecnico_base64=None, mostrar_firmas=None, ruta_salida=None, abrir=True):
    """Genera PDF temporal y lo abre con el visor predeterminado.

    El PDF incluye encabezado operativo, folio, fecha y zona de firmas
    cuando corresponda. La plantilla corporativa se aplica en cada página.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
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

    folio = _valor_por_clave(["Folio OS", "Folio OT", "Folio BIT", "Folio OBC", "Folio LEV", "Folio de Levantamiento", "Folio Bitácora", "Folio de bitácora"])
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
            data = [[Paragraph(f"<b>{c}</b>", estilo_normal) for c in columnas]]
            for r in registros:
                data.append([Paragraph(str(r.get(c, "") or ""), estilo_normal) for c in columnas])
            t = Table(data, repeatRows=1)
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
            if isinstance(child, (ctk.CTkEntry, ctk.CTkTextbox, ctk.CTkOptionMenu)) and _estado_normal(child):
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
            pass
        try:
            objetivo = primer_widget or (_buscar_primer(scroll_widget) if scroll_widget is not None else None)
            if objetivo is not None:
                objetivo.focus_set()
        except Exception:
            pass

    try:
        root.after(delay, _run)
    except Exception:
        pass
