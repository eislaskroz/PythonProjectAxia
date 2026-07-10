"""
Formulario Orden de Servicio AXIA.
Actualizado: campos compactos, renglones dinámicos, firma del cliente y preview PDF.
"""

import json
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
from services.ordenes_servicio_service import crear_orden_servicio, buscar_orden_por_folio
from security.permissions import puede_generar_orden
from views.formato_helpers import ENTRY_H, OPTION_H, LABEL_FONT, SMALL_FONT, SECTION_FONT, obtener_textbox, enfocar_inicio_formulario, firmar_en_popup, generar_pdf_preview, generar_pdf_archivo

TIPOS_SERVICIO = ["Urgente", "Correctivo", "Capacitación", "Póliza", "Reubicación", "Ordinario", "Preventivo", "Desmantelamiento", "Siniestro", "Otro"]
EVALUACIONES = ["Excelente", "Bueno", "Regular", "Malo", "No aplica"]
MOVIMIENTOS_EQUIPO = ["Instalación", "Reparación", "Garantía"]


def mostrar_orden_servicio(parent, app, aco=None):
    usuario_activo = obtener_usuario_actual()
    if not puede_generar_orden(usuario_activo):
        messagebox.showerror("Acceso denegado", "No tienes permisos para generar órdenes de servicio.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=14, pady=10)

    datos_aco = normalizar_datos_aco(aco)
    entradas_bloqueadas = []
    campos_validables = []
    textboxes_validables = []
    btn_preview = None

    var_folio = ctk.StringVar(value=generar_siguiente_folio("OS"))
    var_fecha = ctk.StringVar()
    var_cliente = ctk.StringVar(value=datos_aco.get("cliente", ""))
    var_sucursal = ctk.StringVar(value=datos_aco.get("sucursal", ""))
    var_domicilio = ctk.StringVar(value=datos_aco.get("direccion", ""))
    var_encargado_general = ctk.StringVar(value=datos_aco.get("contacto", ""))
    var_solicitante = ctk.StringVar()
    var_correo = ctk.StringVar(value=datos_aco.get("correo", ""))
    var_celular = ctk.StringVar(value=datos_aco.get("telefono", ""))
    var_hora_llegada = ctk.StringVar()
    var_hora_salida = ctk.StringVar()
    var_aco = ctk.StringVar(value=datos_aco.get("aco_numero", ""))
    var_supervisor = ctk.StringVar(value=datos_aco.get("supervisor", ""))
    var_encargado_servicio = ctk.StringVar(value=datos_aco.get("contacto", ""))
    var_tecnicos = ctk.StringVar()
    var_eval_trato = ctk.StringVar(value="Bueno")
    var_eval_habilidades = ctk.StringVar(value="Bueno")
    var_eval_velocidad = ctk.StringVar(value="Bueno")
    var_eval_otro = ctk.StringVar(value="No aplica")
    var_firma_cliente = ctk.StringVar()
    var_estado_firma = ctk.StringVar(value="Sin firma")

    tipos_vars = {tipo: ctk.BooleanVar(value=False) for tipo in TIPOS_SERVICIO}
    tipo_previo = datos_aco.get("tipo_servicio", "")
    if tipo_previo in tipos_vars:
        tipos_vars[tipo_previo].set(True)

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

    def option(texto, var, values, fila=0, col=0, required=True):
        c = celda(fila, col)
        label(c, texto)
        ctk.CTkOptionMenu(c, variable=var, values=values, height=OPTION_H, font=SMALL_FONT).pack(fill="x")
        if required:
            campos_validables.append(var)
            var.trace_add("write", lambda *_: validar_preview())

    def texto_largo(texto, fila, alto=70, required=True):
        c = celda(fila, 0, 4)
        label(c, texto)
        box = ctk.CTkTextbox(c, height=alto, corner_radius=8, font=SMALL_FONT)
        box.pack(fill="x")
        box.bind("<KeyRelease>", lambda _event: validar_preview())
        if required:
            textboxes_validables.append(box)
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
        var_sucursal.set(datos_aco.get("sucursal", ""))
        var_domicilio.set(datos_aco.get("direccion", ""))
        var_encargado_general.set(datos_aco.get("contacto", ""))
        var_encargado_servicio.set(datos_aco.get("contacto", ""))
        var_correo.set(datos_aco.get("correo", ""))
        var_celular.set(datos_aco.get("telefono", ""))
        var_supervisor.set(datos_aco.get("supervisor", ""))
        tipo = datos_aco.get("tipo_servicio", "")
        if tipo:
            for t, v in tipos_vars.items():
                v.set(t == tipo)
        bloquear_autollenados()
        validar_preview()

    def validar_preview():
        try:
            if btn_preview is not None:
                btn_preview.configure(state="normal" if formulario_completo() else "disabled")
        except Exception:
            pass

    seccion("Información General", 0)
    entry("Folio OS", var_folio, "Automático", 1, 0, state="disabled", required=False)
    entry("Fecha", var_fecha, "YYYY-MM-DD", 1, 1, date=True)
    e_aco = entry("ACO", var_aco, "Número de ACO", 1, 2)
    e_aco.bind("<FocusOut>", lambda _event: cargar_aco())
    e_aco.bind("<Return>", lambda _event: cargar_aco())
    entry("Cliente", var_cliente, "Autollenado", 1, 3, lock=True)
    entry("Sucursal", var_sucursal, "Autollenado", 2, 0, lock=True)
    entry("Domicilio", var_domicilio, "Autollenado", 2, 1, lock=True)
    entry("Encargado", var_encargado_general, "Autollenado", 2, 2, lock=True)
    entry("Solicitante", var_solicitante, "Nombre", 2, 3)
    entry("Correo", var_correo, "Autollenado", 3, 0, lock=True)
    entry("Celular", var_celular, "Autollenado", 3, 1, lock=True)
    entry("Hora de Llegada", var_hora_llegada, "HH:MM", 3, 2)
    entry("Hora de Salida", var_hora_salida, "HH:MM", 3, 3)

    seccion("Tipo de Servicios", 4)
    c_tipos = celda(5, 0, 4)
    grid = ctk.CTkFrame(c_tipos, fg_color="transparent")
    grid.pack(fill="x")
    for i, tipo in enumerate(TIPOS_SERVICIO):
        cb = ctk.CTkCheckBox(grid, text=tipo, variable=tipos_vars[tipo], font=SMALL_FONT, text_color=TEXT_PRIMARY, height=24, command=lambda: validar_preview())
        cb.grid(row=i // 5, column=i % 5, sticky="w", padx=8, pady=2)
    entry("Supervisor", var_supervisor, "Nombre", 6, 0)
    entry("Encargado", var_encargado_servicio, "Autollenado", 6, 1, lock=True)
    entry("Técnicos", var_tecnicos, "Técnicos asignados", 6, 2)

    seccion("Proveedor", 7)
    txt_descripcion = texto_largo("Descripción del servicio y/o instalación", 8, 70)
    txt_observaciones = texto_largo("Observaciones", 9, 60)

    seccion("Entrada/Salida de Equipos", 10)
    equipos = []
    acciones_equipos = celda(11, 0, 4)
    equipos_frame = celda(12, 0, 4)
    headers = ["Equipo", "Número de Serie", "Movimiento", "Diagnóstico de la Falla"]

    def agregar_equipo():
        row_vars = {"Equipo": ctk.StringVar(), "Número de Serie": ctk.StringVar(), "Movimiento": ctk.StringVar(value="Instalación"), "Diagnóstico de la Falla": ctk.StringVar()}
        equipos.append(row_vars)
        fila = ctk.CTkFrame(equipos_frame, fg_color="transparent")
        fila.pack(fill="x", pady=2)
        for j, h in enumerate(headers):
            sub = ctk.CTkFrame(fila, fg_color="transparent")
            sub.grid(row=0, column=j, sticky="ew", padx=3)
            fila.grid_columnconfigure(j, weight=1)
            ctk.CTkLabel(sub, text=h, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w")
            if h == "Movimiento":
                ctk.CTkOptionMenu(sub, variable=row_vars[h], values=MOVIMIENTOS_EQUIPO, height=OPTION_H, font=SMALL_FONT, command=lambda _v=None: validar_preview()).pack(fill="x")
            else:
                ctk.CTkEntry(sub, textvariable=row_vars[h], height=ENTRY_H, corner_radius=8, font=SMALL_FONT).pack(fill="x")
                row_vars[h].trace_add("write", lambda *_: validar_preview())
        validar_preview()

    ctk.CTkButton(acciones_equipos, text="+ Nuevo equipo", width=150, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_equipo).pack(anchor="w")
    agregar_equipo()

    seccion("Evaluación del Servicio", 13)
    option("Trato y actitud del técnico", var_eval_trato, EVALUACIONES, 14, 0)
    option("Habilidades y conocimientos", var_eval_habilidades, EVALUACIONES, 14, 1)
    option("Velocidad y calidad", var_eval_velocidad, EVALUACIONES, 14, 2)
    option("Otro", var_eval_otro, EVALUACIONES, 14, 3)

    seccion("Firma del Cliente", 15)
    c_firma = celda(16, 0, 4)
    ctk.CTkLabel(c_firma, textvariable=var_estado_firma, font=SMALL_FONT, text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 10))
    ctk.CTkButton(c_firma, text="✍ Capturar firma", width=160, height=32, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=lambda: firmar_en_popup(parent, var_firma_cliente, actualizar_firma)).pack(side="left")

    def actualizar_firma():
        var_estado_firma.set("Firma capturada" if var_firma_cliente.get() else "Sin firma")
        validar_preview()

    def equipos_limpios():
        salida = []
        for row in equipos:
            item = {"Equipo": row["Equipo"].get().strip(), "Número de Serie": row["Número de Serie"].get().strip(), "Movimiento": row["Movimiento"].get().strip(), "Diagnóstico de la Falla": row["Diagnóstico de la Falla"].get().strip()}
            if item["Equipo"] or item["Número de Serie"] or item["Diagnóstico de la Falla"]:
                salida.append(item)
        return salida

    def formulario_completo():
        if not all(v.get().strip() for v in campos_validables):
            return False
        if not all(obtener_textbox(b) for b in textboxes_validables):
            return False
        if not any(v.get() for v in tipos_vars.values()):
            return False
        if not equipos_limpios():
            return False
        if not var_firma_cliente.get().strip():
            return False
        return True

    def datos_pdf():
        return {
            "Folio OS": var_folio.get(), "Fecha": var_fecha.get(), "ACO": var_aco.get(), "Cliente": var_cliente.get(), "Sucursal": var_sucursal.get(),
            "Domicilio": var_domicilio.get(), "Encargado": var_encargado_general.get(), "Solicitante": var_solicitante.get(), "Correo": var_correo.get(),
            "Celular": var_celular.get(), "Hora de Llegada": var_hora_llegada.get(), "Hora de Salida": var_hora_salida.get(),
            "Tipo de Servicio": ", ".join([t for t, v in tipos_vars.items() if v.get()]), "Supervisor": var_supervisor.get(), "Encargado Servicio": var_encargado_servicio.get(),
            "Técnicos": var_tecnicos.get(), "Descripción": obtener_textbox(txt_descripcion), "Observaciones": obtener_textbox(txt_observaciones),
            "Trato y actitud": var_eval_trato.get(), "Habilidades y conocimientos": var_eval_habilidades.get(), "Velocidad y calidad": var_eval_velocidad.get(), "Otro": var_eval_otro.get()
        }

    def preview_pdf():
        if not formulario_completo():
            messagebox.showwarning("Preview", "El preview se activa cuando todos los campos estén completos, incluyendo firma y al menos un equipo.")
            return
        generar_pdf_preview("Orden de Servicio", datos_pdf(), [("Entrada/Salida de Equipos", headers, equipos_limpios())], firma_base64=var_firma_cliente.get())

    def guardar_orden():
        if not formulario_completo():
            messagebox.showwarning("Campos obligatorios", "Debes llenar todos los campos, capturar al menos un equipo, seleccionar tipo de servicio y agregar firma del cliente.")
            return
        folio = var_folio.get().strip()
        if buscar_orden_por_folio(folio):
            folio = generar_siguiente_folio("OS")
            var_folio.set(folio)
        tipos_seleccionados = [tipo for tipo, var in tipos_vars.items() if var.get()]
        equipos_db = [{"equipo": e["Equipo"], "numero_serie": e["Número de Serie"], "movimiento": e["Movimiento"], "diagnostico_falla": e["Diagnóstico de la Falla"]} for e in equipos_limpios()]
        datos = {
            "id_aco": datos_aco.get("id_aco"), "id_sucursal": datos_aco.get("id_sucursal"), "id_contacto": datos_aco.get("id_contacto"), "os_folio": folio, "os_fecha": var_fecha.get().strip() or None, "os_aco_numero": var_aco.get().strip(),
            "os_cliente": var_cliente.get().strip(), "os_sucursal": var_sucursal.get().strip(), "os_domicilio": var_domicilio.get().strip(),
            "os_encargado": var_encargado_general.get().strip(), "os_solicitante": var_solicitante.get().strip(), "os_correo": var_correo.get().strip(), "os_celular": var_celular.get().strip(),
            "os_hora_llegada": var_hora_llegada.get().strip(), "os_hora_salida": var_hora_salida.get().strip(), "os_tipos_servicio_json": json.dumps(tipos_seleccionados, ensure_ascii=False),
            "os_tipo_servicio": ", ".join(tipos_seleccionados), "os_supervisor": var_supervisor.get().strip(), "os_encargado_servicio": var_encargado_servicio.get().strip(),
            "os_tecnicos": var_tecnicos.get().strip(), "os_descripcion": obtener_textbox(txt_descripcion), "os_observaciones": obtener_textbox(txt_observaciones),
            "os_equipos_json": json.dumps(equipos_db, ensure_ascii=False), "os_eval_trato": var_eval_trato.get(), "os_eval_habilidades": var_eval_habilidades.get(),
            "os_eval_velocidad": var_eval_velocidad.get(), "os_eval_otro": var_eval_otro.get(), "os_firma_cliente": var_firma_cliente.get(), "os_estatus": 1, "os_prioridad": 2,
            "creado_por": usuario_activo.get("usuario")
        }
        resultado = crear_orden_servicio(datos)
        if resultado:
            registrar_movimiento(modulo="Órdenes de Servicio", accion="CREAR", descripcion=f"El usuario creó la orden {folio}", registro_afectado=folio)
            ruta_pdf = generar_pdf_archivo("Orden de Servicio", datos_pdf(), nombre_archivo=folio, subcarpeta="ordenes_servicio", secciones_tabla=[("Entrada/Salida de Equipos", headers, equipos_limpios())], firma_base64=var_firma_cliente.get())
            mensaje_pdf = f"\n\nPDF guardado en:\n{ruta_pdf}" if ruta_pdf else "\n\nNo se pudo guardar el PDF local."
            messagebox.showinfo("Registro correcto", "La orden de servicio fue registrada correctamente." + mensaje_pdf)
            app.mostrar_vista_inicio_aco()
        else:
            messagebox.showerror("Error", "No se pudo registrar la orden. Revisa que las columnas existan en Supabase.")


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
    btn_guardar = ctk.CTkButton(barra_botones, text="💾 Guardar Orden", width=185, height=38, corner_radius=10, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=guardar_orden)
    btn_preview = ctk.CTkButton(barra_botones, text="👁 Preview PDF", width=165, height=38, corner_radius=10, fg_color="#1F4E79", hover_color="#173B5C", font=BUTTON_FONT, command=preview_pdf, state="disabled")
    ctk.CTkButton(barra_botones, text="⬅ Atrás", width=120, height=38, corner_radius=10, fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT, command=volver_a_selector_aco).grid(row=0, column=0, padx=8)
    btn_guardar.grid(row=0, column=1, padx=8)
    btn_preview.grid(row=0, column=2, padx=8)
    ctk.CTkButton(barra_botones, text="↩ Cancelar", width=130, height=38, corner_radius=10, fg_color="gray", font=BUTTON_FONT, command=app.mostrar_vista_inicio_aco).grid(row=0, column=3, padx=8)

    enfocar_inicio_formulario(card)
    validar_preview()

    if aco:
        bloquear_autollenados()
    validar_preview()
