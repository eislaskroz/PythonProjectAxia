"""
Formulario Orden de Trabajo AXIA.
Actualizado: campos compactos, partidas dinámicas y preview PDF.
"""

import json
import customtkinter as ctk
from tkinter import messagebox

from ui.colors import SECONDARY, WHITE, TEXT_PRIMARY, BUTTON_HOVER
from ui.date_picker import abrir_selector_fecha
from ui.fonts import BUTTON_FONT
from app_context import obtener_usuario_actual
from services.movimientos_service import registrar_movimiento
from services.aco_context_service import normalizar_datos_aco
from services.acos_service import buscar_aco_por_numero
from services.folios_service import generar_siguiente_folio
from services.ordenes_trabajo_service import crear_orden_trabajo, buscar_orden_trabajo_por_folio
from security.permissions import puede_generar_orden
from views.formato_helpers import ENTRY_H, LABEL_FONT, SMALL_FONT, SECTION_FONT, generar_pdf_preview, generar_pdf_archivo, enfocar_inicio_formulario


def mostrar_orden_trabajo(parent, app, aco=None):
    usuario_activo = obtener_usuario_actual()
    if not puede_generar_orden(usuario_activo):
        messagebox.showerror("Acceso denegado", "No tienes permisos para generar órdenes de trabajo.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=14, pady=10)

    datos_aco = normalizar_datos_aco(aco)
    entradas_bloqueadas = []
    campos_validables = []
    btn_preview = None

    var_folio = ctk.StringVar(value=generar_siguiente_folio("OT"))
    var_fecha = ctk.StringVar()
    var_aco = ctk.StringVar(value=datos_aco.get("aco_numero", ""))
    var_cliente = ctk.StringVar(value=datos_aco.get("cliente", ""))
    var_contacto = ctk.StringVar(value=datos_aco.get("contacto", ""))
    var_sucursal = ctk.StringVar(value=datos_aco.get("sucursal", ""))
    var_jefe_operacion = ctk.StringVar(value=datos_aco.get("jefe_operacion", ""))
    var_supervisor = ctk.StringVar(value=datos_aco.get("supervisor", ""))
    var_esi = ctk.StringVar(value=datos_aco.get("esi", ""))
    var_numero_dias = ctk.StringVar()
    var_numero_personas = ctk.StringVar()
    var_asunto = ctk.StringVar()

    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_rowconfigure(1, weight=0)
    contenedor.grid_columnconfigure(0, weight=1)

    card = ctk.CTkScrollableFrame(contenedor, width=1280, fg_color=WHITE, corner_radius=18)
    card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
    form = ctk.CTkFrame(card, fg_color="transparent")
    form.pack(fill="x", expand=True, padx=24, pady=(18, 8))
    for col in range(4):
        form.grid_columnconfigure(col, weight=1, uniform="cols")

    def seccion(texto, fila):
        ctk.CTkLabel(form, text=texto, font=SECTION_FONT, text_color=TEXT_PRIMARY).grid(row=fila, column=0, columnspan=4, sticky="w", pady=(12, 6))

    def label(parent_, texto):
        ctk.CTkLabel(parent_, text=texto, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))

    def celda(fila, col, colspan=1):
        frame = ctk.CTkFrame(form, fg_color="transparent")
        frame.grid(row=fila, column=col, columnspan=colspan, sticky="ew", padx=5, pady=(0, 6))
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def entry(texto, var, placeholder="", fila=0, col=0, state="normal", lock=False, date=False, required=True):
        c = celda(fila, col)
        label(c, texto)
        e = ctk.CTkEntry(c, textvariable=var, placeholder_text=placeholder, height=ENTRY_H, corner_radius=8, font=SMALL_FONT, state=state)
        e.pack(fill="x")
        if date and state != "disabled":
            e.bind("<Button-1>", lambda _event, v=var: (abrir_selector_fecha(c, v), validar_preview()))
        if lock:
            entradas_bloqueadas.append(e)
        if required and state != "disabled":
            campos_validables.append(var)
            var.trace_add("write", lambda *_: validar_preview())
        return e

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
        var_contacto.set(datos_aco.get("contacto", ""))
        var_sucursal.set(datos_aco.get("sucursal", ""))
        var_jefe_operacion.set(datos_aco.get("jefe_operacion", ""))
        var_supervisor.set(datos_aco.get("supervisor", ""))
        var_esi.set(datos_aco.get("esi", ""))
        bloquear_autollenados()
        validar_preview()

    def validar_preview():
        try:
            if btn_preview is not None:
                btn_preview.configure(state="normal" if formulario_completo() else "disabled")
        except Exception:
            pass

    seccion("Datos generales", 0)
    entry("Folio OT", var_folio, "Automático", 1, 0, state="disabled", required=False)
    e_aco = entry("ACO", var_aco, "Número de ACO", 1, 1)
    e_aco.bind("<FocusOut>", lambda _event: cargar_aco())
    e_aco.bind("<Return>", lambda _event: cargar_aco())
    entry("Fecha", var_fecha, "YYYY-MM-DD", 1, 2, date=True)
    entry("Cliente", var_cliente, "Autollenado", 1, 3, lock=True)
    entry("Contacto", var_contacto, "Autollenado", 2, 0, lock=True)
    entry("Sucursal", var_sucursal, "Autollenado", 2, 1, lock=True)
    entry("Jefe de Operación", var_jefe_operacion, "Autollenado", 2, 2, lock=True)
    entry("Supervisor", var_supervisor, "Nombre", 2, 3)
    entry("ESI", var_esi, "ESI", 3, 0)
    entry("Número de Días", var_numero_dias, "Ej. 3", 3, 1)
    entry("Número de Personas", var_numero_personas, "Ej. 2", 3, 2)
    entry("Asunto", var_asunto, "Motivo", 3, 3)

    seccion("Partidas / conceptos", 4)
    partidas = []
    acciones_partidas = celda(5, 0, 4)
    partidas_frame = celda(6, 0, 4)
    headers = ["Parte", "Unidad", "Cantidad", "Modelo", "Marca", "Concepto", "Día", "Adicional", "Total"]

    def agregar_partida():
        row_vars = {h: ctk.StringVar() for h in headers}
        partidas.append(row_vars)
        fila = ctk.CTkFrame(partidas_frame, fg_color="transparent")
        fila.pack(fill="x", pady=2)
        for j, h in enumerate(headers):
            sub = ctk.CTkFrame(fila, fg_color="transparent")
            sub.grid(row=0, column=j, sticky="ew", padx=2)
            fila.grid_columnconfigure(j, weight=1)
            ctk.CTkLabel(sub, text=h, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkEntry(sub, textvariable=row_vars[h], height=ENTRY_H, corner_radius=8, font=SMALL_FONT).pack(fill="x")
            row_vars[h].trace_add("write", lambda *_: validar_preview())
        validar_preview()

    ctk.CTkButton(acciones_partidas, text="+ Nueva partida", width=150, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_partida).pack(anchor="w")
    agregar_partida()

    def partidas_limpias():
        salida = []
        for row in partidas:
            item = {k: v.get().strip() for k, v in row.items()}
            if any(item.values()):
                salida.append(item)
        return salida

    def formulario_completo():
        return all(v.get().strip() for v in campos_validables) and len(partidas_limpias()) > 0

    def datos_pdf():
        return {
            "Folio OT": var_folio.get(), "Fecha": var_fecha.get(), "ACO": var_aco.get(), "Cliente": var_cliente.get(), "Contacto": var_contacto.get(),
            "Sucursal": var_sucursal.get(), "Jefe de Operación": var_jefe_operacion.get(), "Supervisor": var_supervisor.get(), "ESI": var_esi.get(),
            "Número de Días": var_numero_dias.get(), "Número de Personas": var_numero_personas.get(), "Asunto": var_asunto.get()
        }

    def preview_pdf():
        if not formulario_completo():
            messagebox.showwarning("Preview", "El preview se activa cuando todos los campos estén completos y exista al menos una partida.")
            return
        generar_pdf_preview("Orden de Trabajo", datos_pdf(), [("Partidas / Conceptos", headers, partidas_limpias())])

    def guardar_orden():
        if not formulario_completo():
            messagebox.showwarning("Campos obligatorios", "Debes llenar todos los campos y capturar al menos una partida.")
            return
        folio = var_folio.get().strip()
        if buscar_orden_trabajo_por_folio(folio):
            folio = generar_siguiente_folio("OT")
            var_folio.set(folio)
        partidas_db = [{k.lower().replace(" ", "_").replace("í", "i"): v for k, v in p.items()} for p in partidas_limpias()]
        datos = {
            "id_aco": datos_aco.get("id_aco"), "id_sucursal": datos_aco.get("id_sucursal"), "id_contacto": datos_aco.get("id_contacto"), "ot_folio": folio, "ot_fecha": var_fecha.get().strip() or None, "ot_aco_numero": var_aco.get().strip(),
            "ot_cliente": var_cliente.get().strip(), "ot_contacto": var_contacto.get().strip(), "ot_sucursal": var_sucursal.get().strip(),
            "ot_jefe_operacion": var_jefe_operacion.get().strip(), "ot_supervisor": var_supervisor.get().strip(), "ot_esi": var_esi.get().strip(),
            "ot_numero_dias": var_numero_dias.get().strip(), "ot_numero_personas": var_numero_personas.get().strip(), "ot_asunto": var_asunto.get().strip(),
            "ot_partidas_json": json.dumps(partidas_db, ensure_ascii=False), "ot_descripcion": var_asunto.get().strip(), "ot_estatus": 1, "ot_prioridad": 2,
            "creado_por": usuario_activo.get("usuario")
        }
        resultado = crear_orden_trabajo(datos)
        if resultado:
            registrar_movimiento(modulo="Órdenes de Trabajo", accion="CREAR", descripcion=f"El usuario creó la orden de trabajo {folio}", registro_afectado=folio)
            ruta_pdf = generar_pdf_archivo("Orden de Trabajo", datos_pdf(), nombre_archivo=folio, subcarpeta="ordenes_trabajo", secciones_tabla=[("Partidas / Conceptos", headers, partidas_limpias())])
            mensaje_pdf = f"\n\nPDF guardado en:\n{ruta_pdf}" if ruta_pdf else "\n\nNo se pudo guardar el PDF local."
            messagebox.showinfo("Registro correcto", "La orden de trabajo fue registrada correctamente." + mensaje_pdf)
            app.mostrar_vista_inicio_aco()
        else:
            messagebox.showerror("Error", "No se pudo registrar la orden de trabajo. Revisa que las columnas existan en Supabase.")


    def volver_a_selector_aco():
        """Regresa al selector de formularios manteniendo el ACO validado."""
        if aco:
            app.mostrar_vista_inicio_aco_validado(aco)
        else:
            app.volver_atras()

    botones = ctk.CTkFrame(contenedor, fg_color="#F4F4F4", height=58, corner_radius=0)
    botones.grid(row=1, column=0, sticky="ew", pady=(0, 0))
    botones.grid_columnconfigure(0, weight=1)
    barra_botones = ctk.CTkFrame(botones, fg_color="transparent")
    barra_botones.pack(anchor="center", pady=8)
    ctk.CTkButton(barra_botones, text="⬅ Atrás", width=120, height=38, corner_radius=10, fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT, command=volver_a_selector_aco).grid(row=0, column=0, padx=8)
    ctk.CTkButton(barra_botones, text="💾 Guardar Orden", width=185, height=38, corner_radius=10, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=guardar_orden).grid(row=0, column=1, padx=8)
    btn_preview = ctk.CTkButton(barra_botones, text="👁 Preview PDF", width=165, height=38, corner_radius=10, fg_color="#1F4E79", hover_color="#173B5C", font=BUTTON_FONT, command=preview_pdf, state="disabled")
    btn_preview.grid(row=0, column=2, padx=8)
    ctk.CTkButton(barra_botones, text="↩ Cancelar", width=130, height=38, corner_radius=10, fg_color="gray", font=BUTTON_FONT, command=app.mostrar_vista_inicio_aco).grid(row=0, column=3, padx=8)

    enfocar_inicio_formulario(card)
    validar_preview()

    if aco:
        bloquear_autollenados()
    validar_preview()
