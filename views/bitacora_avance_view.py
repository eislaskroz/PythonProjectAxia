"""
=========================================================
MÓDULO: bitacora_avance_view.py
DESCRIPCIÓN:
Formulario operativo AXIA actualizado al formato físico vigente.
=========================================================
"""

import customtkinter as ctk
from tkinter import messagebox

from ui.colors import SECONDARY, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER
from ui.date_picker import abrir_selector_fecha
from ui.fonts import TEXT_SM, BUTTON_FONT
from app_context import obtener_usuario_actual
from services.movimientos_service import registrar_movimiento
from services.aco_context_service import normalizar_datos_aco
from services.acos_service import buscar_aco_por_numero
from services.folios_service import generar_siguiente_folio
from services.bitacoras_service import crear_bitacora, buscar_bitacora_por_folio
from security.permissions import puede_generar_bitacora
from views.formato_helpers import ENTRY_H, OPTION_H, LABEL_FONT, SMALL_FONT, SECTION_FONT, obtener_textbox, enfocar_inicio_formulario, generar_pdf_preview, generar_pdf_archivo


def mostrar_bitacora_avance(parent, app, aco=None):
    usuario_activo = obtener_usuario_actual()
    if not puede_generar_bitacora(usuario_activo):
        messagebox.showerror("Acceso denegado", "No tienes permisos para generar bitácoras.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=14, pady=10)

    datos_aco = normalizar_datos_aco(aco)
    entradas_bloqueadas = []

    var_folio = ctk.StringVar(value=generar_siguiente_folio("BIT"))
    var_fecha = ctk.StringVar()
    var_aco = ctk.StringVar(value=datos_aco.get("aco_numero", ""))
    var_direccion = ctk.StringVar(value=datos_aco.get("direccion", ""))
    var_cliente = ctk.StringVar(value=datos_aco.get("cliente", ""))
    var_encargado_proyecto = ctk.StringVar(value=datos_aco.get("jefe_operacion", "") or datos_aco.get("responsable", ""))
    var_hora_llegada = ctk.StringVar()
    var_hora_salida = ctk.StringVar()
    var_tecnico_sitio = ctk.StringVar()
    var_estatus = ctk.StringVar(value="En proceso")

    def mostrar_panel_datos_aco():
        panel = ctk.CTkFrame(contenedor, fg_color="#F4F7FB", corner_radius=14, border_width=1, border_color="#DDE6F3")
        panel.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 8))
        ctk.CTkLabel(panel, text="Información ligada al ACO  🔒 Solo lectura", font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(8, 4))
        campos = [("ACO", var_aco.get()), ("Cliente", var_cliente.get()), ("Dirección", var_direccion.get()), ("Encargado AXIA", var_encargado_proyecto.get())]
        for i, (etiqueta, valor) in enumerate(campos):
            fila, col = 1 + i // 3, i % 3
            item = ctk.CTkFrame(panel, fg_color="transparent")
            item.grid(row=fila, column=col, sticky="ew", padx=18, pady=(2, 5))
            ctk.CTkLabel(item, text=f"{etiqueta}: ", font=("Montserrat", 11, "bold"), text_color=TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(item, text=valor or "No registrado", font=("Montserrat", 11), text_color=TEXT_SECONDARY, wraplength=330).pack(side="left", fill="x", expand=True)
        for col in range(3):
            panel.grid_columnconfigure(col, weight=1, uniform="aco_panel")

    if aco:
        mostrar_panel_datos_aco()

    contenedor.grid_rowconfigure(0, weight=0)
    contenedor.grid_rowconfigure(1, weight=1)
    contenedor.grid_rowconfigure(2, weight=0)
    contenedor.grid_columnconfigure(0, weight=1)

    card = ctk.CTkScrollableFrame(contenedor, width=1280, fg_color=WHITE, corner_radius=18)
    card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
    form = ctk.CTkFrame(card, fg_color="transparent")
    form.pack(fill="x", expand=True, padx=24, pady=(18, 8))
    for col in range(3):
        form.grid_columnconfigure(col, weight=1, uniform="form_cols")

    def seccion(texto, fila):
        ctk.CTkLabel(form, text=texto, font=SECTION_FONT, text_color=TEXT_PRIMARY).grid(row=fila, column=0, columnspan=3, sticky="w", pady=(12, 6))

    def label(parent, texto):
        ctk.CTkLabel(parent, text=texto, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))

    def celda(fila, col, colspan=1):
        frame = ctk.CTkFrame(form, fg_color="transparent")
        frame.grid(row=fila, column=col, columnspan=colspan, sticky="ew", padx=(0,10) if col == 0 else ((10,10) if col == 1 else (10,0)), pady=(0, 6))
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def entry(texto, var, placeholder="", fila=0, col=0, state="normal", lock=False, date=False):
        c = celda(fila, col)
        label(c, texto)
        e = ctk.CTkEntry(c, textvariable=var, placeholder_text=placeholder, height=ENTRY_H, corner_radius=8, font=SMALL_FONT, state=state)
        e.pack(fill="x")
        if date and state != "disabled":
            e.bind("<Button-1>", lambda _event, v=var: abrir_selector_fecha(c, v))
        if lock:
            entradas_bloqueadas.append(e)
        return e

    def option(texto, var, values, fila=0, col=0):
        c = celda(fila, col)
        label(c, texto)
        ctk.CTkOptionMenu(c, variable=var, values=values, height=OPTION_H, font=SMALL_FONT).pack(fill="x")

    def texto_largo(texto, fila, alto=110):
        c = celda(fila, 0, 3)
        label(c, texto)
        box = ctk.CTkTextbox(c, height=alto, corner_radius=8, font=SMALL_FONT)
        box.pack(fill="x")
        return box

    def bloquear_autollenados():
        for e in entradas_bloqueadas:
            e.configure(state="disabled")

    def cargar_aco():
        nonlocal datos_aco
        numero = var_aco.get().strip()
        if not numero:
            return
        registro = buscar_aco_por_numero(numero)
        if not registro:
            messagebox.showwarning("ACO no encontrado", "No se encontró información para el ACO capturado.")
            return
        datos_aco = normalizar_datos_aco(registro)
        var_cliente.set(datos_aco.get("cliente", ""))
        var_direccion.set(datos_aco.get("direccion", ""))
        var_encargado_proyecto.set(datos_aco.get("jefe_operacion", "") or datos_aco.get("responsable", ""))
        bloquear_autollenados()

    seccion("Bitácora de Avance", 0)
    entry("Folio de bitácora", var_folio, "Automático", 1, 0, state="disabled")
    entry("Fecha", var_fecha, "YYYY-MM-DD", 1, 1, date=True)
    e_aco = entry("Número de ACO", var_aco, "Número de ACO", 1, 2)
    e_aco.bind("<FocusOut>", lambda _event: cargar_aco())
    e_aco.bind("<Return>", lambda _event: cargar_aco())
    entry("Dirección de la sucursal", var_direccion, "Autollenado por ACO", 2, 0, lock=True)
    entry("Nombre del Cliente", var_cliente, "Autollenado por ACO", 2, 1, lock=True)
    entry("Nombre del encargado del proyecto (AXIA)", var_encargado_proyecto, "Autollenado por ACO", 2, 2, lock=True)
    entry("Hora de Llegada", var_hora_llegada, "HH:MM", 3, 0)
    entry("Hora de Salida", var_hora_salida, "HH:MM", 3, 1)
    entry("Técnico en sitio", var_tecnico_sitio, "Nombre del técnico", 3, 2)
    option("Estatus", var_estatus, ["Pendiente", "En proceso", "Finalizada"], 4, 0)
    txt_observaciones = texto_largo("Observaciones", 5, 70)
    txt_descripcion = texto_largo("Descripción", 6, 80)

    if aco:
        bloquear_autollenados()

    def convertir_estatus(texto):
        return {"Pendiente": 1, "En proceso": 2, "Finalizada": 3}.get(texto, 2)

    def formulario_completo():
        return all([
            var_folio.get().strip(), var_fecha.get().strip(), var_aco.get().strip(),
            var_direccion.get().strip(), var_cliente.get().strip(), var_encargado_proyecto.get().strip(),
            var_hora_llegada.get().strip(), var_hora_salida.get().strip(), var_tecnico_sitio.get().strip(),
            obtener_textbox(txt_observaciones), obtener_textbox(txt_descripcion)
        ])

    def preview_pdf():
        if not formulario_completo():
            messagebox.showwarning("Preview", "El preview se activa cuando todos los campos estén completos.")
            return
        datos_pdf = {
            "Folio Bitácora": var_folio.get(), "Fecha": var_fecha.get(), "Número de ACO": var_aco.get(),
            "Dirección de la sucursal": var_direccion.get(), "Nombre del Cliente": var_cliente.get(),
            "Encargado del proyecto AXIA": var_encargado_proyecto.get(), "Hora de Llegada": var_hora_llegada.get(),
            "Hora de Salida": var_hora_salida.get(), "Técnico en sitio": var_tecnico_sitio.get(),
            "Estatus": var_estatus.get(), "Observaciones": obtener_textbox(txt_observaciones), "Descripción": obtener_textbox(txt_descripcion)
        }
        generar_pdf_preview("Bitácora de Avance", datos_pdf)

    def validar_preview():
        try:
            btn_preview.configure(state="normal" if formulario_completo() else "disabled")
        except Exception:
            pass

    for v in [var_folio, var_fecha, var_aco, var_direccion, var_cliente, var_encargado_proyecto, var_hora_llegada, var_hora_salida, var_tecnico_sitio, var_estatus]:
        v.trace_add("write", lambda *_: validar_preview())
    txt_observaciones.bind("<KeyRelease>", lambda _event: validar_preview())
    txt_descripcion.bind("<KeyRelease>", lambda _event: validar_preview())

    def guardar_bitacora():
        folio = var_folio.get().strip()
        descripcion = txt_descripcion.get("1.0", "end").strip()
        if not formulario_completo():
            messagebox.showwarning("Campos obligatorios", "Debes llenar todos los campos de la bitácora.")
            return
        if buscar_bitacora_por_folio(folio):
            folio = generar_siguiente_folio("BIT")
            var_folio.set(folio)
        datos = {
            "id_aco": datos_aco.get("id_aco"),
            "id_sucursal": datos_aco.get("id_sucursal"),
            "id_contacto": datos_aco.get("id_contacto"),
            "bit_folio": folio,
            "bit_fecha": var_fecha.get().strip() or None,
            "bit_aco_numero": var_aco.get().strip(),
            "bit_direccion_sucursal": var_direccion.get().strip(),
            "bit_cliente": var_cliente.get().strip(),
            "bit_encargado_proyecto_axia": var_encargado_proyecto.get().strip(),
            "bit_hora_llegada": var_hora_llegada.get().strip(),
            "bit_hora_salida": var_hora_salida.get().strip(),
            "bit_observaciones": txt_observaciones.get("1.0", "end").strip(),
            "bit_tecnico": var_tecnico_sitio.get().strip(),
            "bit_tecnico_sitio": var_tecnico_sitio.get().strip(),
            "bit_descripcion": descripcion,
            "bit_estatus": convertir_estatus(var_estatus.get()),
            "bit_porcentaje_avance": 0,
            "creado_por": usuario_activo.get("usuario")
        }
        resultado = crear_bitacora(datos)
        if resultado:
            registrar_movimiento(modulo="Bitácoras", accion="CREAR", descripcion=f"El usuario creó la bitácora {folio}", registro_afectado=folio)
            ruta_pdf = generar_pdf_archivo("Bitácora de Avance", datos_pdf(), nombre_archivo=folio, subcarpeta="bitacoras")
            mensaje_pdf = f"\n\nPDF guardado en:\n{ruta_pdf}" if ruta_pdf else "\n\nNo se pudo guardar el PDF local."
            messagebox.showinfo("Registro correcto", "La bitácora fue registrada correctamente." + mensaje_pdf)
            app.mostrar_vista_inicio_aco()
        else:
            messagebox.showerror("Error", "No se pudo registrar la bitácora. Revisa que las columnas existan en Supabase.")


    def volver_a_selector_aco():
        """Regresa al selector de formularios manteniendo el ACO validado."""
        if aco:
            app.mostrar_vista_inicio_aco_validado(aco)
        else:
            app.volver_atras()

    botones = ctk.CTkFrame(contenedor, fg_color="#F4F4F4", height=58, corner_radius=0)
    botones.grid(row=2, column=0, sticky="ew")
    botones.grid_columnconfigure(0, weight=1)
    barra_botones = ctk.CTkFrame(botones, fg_color="transparent")
    barra_botones.pack(anchor="center", pady=8)
    ctk.CTkButton(barra_botones, text="⬅ Atrás", width=120, height=38, corner_radius=10, fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT, command=volver_a_selector_aco).grid(row=0, column=0, padx=8)
    ctk.CTkButton(barra_botones, text="💾 Guardar Bitácora", width=190, height=38, corner_radius=10, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=guardar_bitacora).grid(row=0, column=1, padx=8)
    btn_preview = ctk.CTkButton(barra_botones, text="👁 Preview PDF", width=165, height=38, corner_radius=10, fg_color="#1F4E79", hover_color="#173B5C", font=BUTTON_FONT, command=preview_pdf, state="disabled")
    btn_preview.grid(row=0, column=2, padx=8)
    ctk.CTkButton(barra_botones, text="↩ Cancelar", width=130, height=38, corner_radius=10, fg_color="gray", font=BUTTON_FONT, command=app.mostrar_vista_inicio_aco).grid(row=0, column=3, padx=8)
    enfocar_inicio_formulario(card)
    validar_preview()
