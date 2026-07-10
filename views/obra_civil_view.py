"""Formulario Obra Civil / Proyecto Ejecutivo AXIA."""

import json
import customtkinter as ctk
from tkinter import messagebox, filedialog

from app_context import obtener_usuario_actual
from security.permissions import puede_generar_levantamiento
from services.aco_context_service import normalizar_datos_aco
from services.acos_service import buscar_aco_por_numero
from services.clientes_service import buscar_clientes, construir_direccion_cliente
from services.folios_service import generar_siguiente_folio
from services.movimientos_service import registrar_movimiento
from services.obras_civiles_service import crear_obra_civil, buscar_obra_civil_por_folio
from ui.colors import SECONDARY, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER
from ui.date_picker import abrir_selector_fecha
from ui.fonts import BUTTON_FONT
from views.formato_helpers import ENTRY_H, OPTION_H, LABEL_FONT, SMALL_FONT, SECTION_FONT, firmar_en_popup, generar_pdf_preview, generar_pdf_archivo, obtener_textbox, enfocar_inicio_formulario

SI_NO = ["Sí", "No"]
ESTADOS = ["Pendiente", "En proceso", "Terminado"]
RESULTADOS = ["Aprobadas", "Reprobadas", "Pendiente"]


def mostrar_obra_civil(parent, app, aco=None):
    usuario_activo = obtener_usuario_actual()
    if not puede_generar_levantamiento(usuario_activo):
        messagebox.showerror("Acceso denegado", "No tienes permisos para generar registros de obra civil.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    datos_aco = normalizar_datos_aco(aco)
    entradas_bloqueadas = []
    campos_validables = []
    evidencias = []
    materiales_miscelaneos_items = []
    btn_preview = None

    var_folio = ctk.StringVar(value=generar_siguiente_folio("OBC"))
    var_fecha = ctk.StringVar()
    var_aco = ctk.StringVar(value=datos_aco.get("aco_numero", ""))
    var_cliente = ctk.StringVar(value=datos_aco.get("cliente", ""))
    var_cliente_selector = ctk.StringVar()
    var_contacto = ctk.StringVar(value=datos_aco.get("contacto", ""))
    var_sucursal = ctk.StringVar(value=datos_aco.get("sucursal", ""))
    var_direccion = ctk.StringVar(value=datos_aco.get("direccion", ""))
    var_responsable = ctk.StringVar(value=datos_aco.get("responsable", "") or usuario_activo.get("nombre", "") or usuario_activo.get("usuario", ""))
    var_supervisor = ctk.StringVar(value=datos_aco.get("supervisor", ""))
    var_tipo_giro = ctk.StringVar()
    var_nombre_proyecto = ctk.StringVar()

    var_superficie = ctk.StringVar(value="Sí")
    var_superficie_ok = ctk.StringVar(value="Sí")
    var_planos_arq = ctk.StringVar(value="Sí")
    var_maquinaria = ctk.StringVar(value="No")
    var_permisos = ctk.StringVar(value="Sí")

    ejecucion_vars = {
        "Trazo y nivelación": ctk.StringVar(value="Pendiente"),
        "Trámites generales para instalaciones": ctk.StringVar(value="Pendiente"),
        "Construcción obra negra": ctk.StringVar(value="Pendiente"),
        "Instalación eléctrica": ctk.StringVar(value="Pendiente"),
        "Agua": ctk.StringVar(value="Pendiente"),
        "Drenaje": ctk.StringVar(value="Pendiente"),
        "Telefonía": ctk.StringVar(value="Pendiente"),
        "Datos y redes": ctk.StringVar(value="Pendiente"),
    }
    var_pruebas = ctk.StringVar(value="Pendiente")
    var_planos_acabados = ctk.StringVar(value="Sí")
    var_generacion_planos = ctk.StringVar(value="No aplica")
    var_etapa_acabados = ctk.StringVar(value="Pendiente")
    var_obra_blanca = ctk.StringVar(value="Pendiente")
    var_preentrega = ctk.StringVar(value="Pendiente")
    var_entrega_formal = ctk.StringVar(value="No")
    var_fecha_entrega = ctk.StringVar()
    var_firma_cliente = ctk.StringVar()
    var_firma_tecnico = ctk.StringVar()

    # En el flujo sin ACO, Obra Civil selecciona al cliente directamente de Supabase.
    clientes_disponibles = []
    clientes_por_nombre = {}
    if not aco:
        try:
            clientes_disponibles = buscar_clientes("", limite=500) or []
        except Exception:
            clientes_disponibles = []

        for cliente_db in clientes_disponibles:
            nombre = str(cliente_db.get("cli_razonsocial", "") or "").strip()
            if nombre:
                clientes_por_nombre[nombre] = cliente_db

        if clientes_por_nombre:
            primer_cliente = sorted(clientes_por_nombre.keys())[0]
            var_cliente_selector.set(primer_cliente)

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=14, pady=10)
    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_rowconfigure(1, weight=0)
    contenedor.grid_columnconfigure(0, weight=1)

    card = ctk.CTkScrollableFrame(contenedor, width=1280, height=520, fg_color=WHITE, corner_radius=18)
    card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
    form = ctk.CTkFrame(card, fg_color="transparent")
    form.pack(fill="x", expand=True, padx=24, pady=(18, 8))
    for col in range(4):
        form.grid_columnconfigure(col, weight=1, uniform="cols")

    def validar_preview():
        try:
            if btn_preview is not None:
                btn_preview.configure(state="normal" if formulario_completo() else "disabled")
        except Exception:
            pass

    def seccion(texto, fila):
        ctk.CTkLabel(form, text=texto, font=SECTION_FONT, text_color=TEXT_PRIMARY).grid(row=fila, column=0, columnspan=4, sticky="w", pady=(12, 6))

    def celda(fila, col, colspan=1):
        frame = ctk.CTkFrame(form, fg_color="transparent")
        frame.grid(row=fila, column=col, columnspan=colspan, sticky="ew", padx=5, pady=(0, 6))
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def label(parent_, texto):
        ctk.CTkLabel(parent_, text=texto, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 2))

    def entry(texto, var, fila, col, placeholder="", state="normal", lock=False, date=False, required=True, colspan=1):
        c = celda(fila, col, colspan)
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

    def option(texto, var, opciones, fila, col, required=True, colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        o = ctk.CTkOptionMenu(c, variable=var, values=opciones, height=OPTION_H, corner_radius=8, font=SMALL_FONT)
        o.pack(fill="x")
        if required:
            campos_validables.append(var)
            var.trace_add("write", lambda *_: validar_preview())
        return o

    def cliente_selector(texto, fila, col, colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        nombres = sorted(clientes_por_nombre.keys())
        o = ctk.CTkOptionMenu(
            c,
            variable=var_cliente_selector,
            values=nombres or ["Sin clientes registrados"],
            height=OPTION_H,
            corner_radius=8,
            font=SMALL_FONT,
            command=lambda nombre: cargar_cliente(nombre),
        )
        o.pack(fill="x")
        campos_validables.append(var_cliente)
        var_cliente.trace_add("write", lambda *_: validar_preview())
        return o

    def textbox(texto, fila, col, colspan=4, height=70):
        c = celda(fila, col, colspan)
        label(c, texto)
        box = ctk.CTkTextbox(c, height=height, corner_radius=8, font=SMALL_FONT)
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
        var_contacto.set(datos_aco.get("contacto", ""))
        var_sucursal.set(datos_aco.get("sucursal", ""))
        var_direccion.set(datos_aco.get("direccion", ""))
        var_responsable.set(datos_aco.get("responsable", ""))
        var_supervisor.set(datos_aco.get("supervisor", ""))
        bloquear_autollenados()
        validar_preview()

    def cargar_cliente(nombre=None):
        """Autollena datos generales desde db_clientes cuando el flujo no tiene ACO."""
        nombre_cliente = str(nombre or var_cliente_selector.get() or "").strip()
        cliente_db = clientes_por_nombre.get(nombre_cliente)
        if not cliente_db:
            return
        var_cliente.set(nombre_cliente)
        var_contacto.set(cliente_db.get("cli_contacto", "") or "")
        var_sucursal.set(cliente_db.get("cli_municipio", "") or "")
        var_direccion.set(construir_direccion_cliente(cliente_db))
        validar_preview()

    seccion("Datos generales", 0)
    entry("Folio OBC", var_folio, 1, 0, "Automático", state="disabled", required=False)
    entry("Fecha", var_fecha, 1, 1, "YYYY-MM-DD", date=True)

    if aco:
        # Con ACO: todos los datos maestros se heredan y permanecen en solo lectura.
        e_aco = entry("ACO", var_aco, 1, 2, "ACO asignado", state="disabled", required=False)
        entry("Cliente", var_cliente, 1, 3, "Autollenado desde ACO", lock=True)
        entry("Contacto", var_contacto, 2, 0, "Autollenado desde ACO", lock=True)
        entry("Sucursal", var_sucursal, 2, 1, "Autollenado desde ACO", lock=True)
        entry("Dirección", var_direccion, 2, 2, "Autollenado desde ACO", lock=True)
        entry("Responsable AXIA", var_responsable, 2, 3, "Autollenado desde ACO", lock=True)
        foco_inicial = e_aco
    else:
        # Sin ACO: no se muestra el campo ACO; se selecciona un cliente de db_clientes.
        cliente_selector("Cliente", 1, 2, colspan=2)
        entry("Contacto", var_contacto, 2, 0, "Autollenado desde cliente", lock=True)
        entry("Sucursal / municipio", var_sucursal, 2, 1, "Autollenado desde cliente", lock=True)
        entry("Dirección", var_direccion, 2, 2, "Autollenado desde cliente", lock=True)
        entry("Responsable AXIA", var_responsable, 2, 3, "Usuario actual", lock=True)
        foco_inicial = None
        if clientes_por_nombre:
            cargar_cliente(var_cliente_selector.get())

    entry("Supervisor", var_supervisor, 3, 0, "Supervisor")
    entry("Tipo de giro", var_tipo_giro, 3, 1, "Ej. Bancario, retail, oficina")
    entry("Nombre del proyecto", var_nombre_proyecto, 3, 2, "Proyecto ejecutivo", colspan=2)

    seccion("Planeación inicial", 4)
    option("¿Se cuenta con superficie?", var_superficie, SI_NO, 5, 0)
    option("¿La superficie es adecuada?", var_superficie_ok, SI_NO, 5, 1)
    option("¿Planos y diseño arquitectónico?", var_planos_arq, SI_NO, 5, 2)
    option("¿Requiere maquinaria?", var_maquinaria, SI_NO, 5, 3)
    option("¿Se cuenta con permisos?", var_permisos, SI_NO, 6, 0)
    txt_observaciones_iniciales = textbox("Observaciones iniciales", 7, 0, 4)

    seccion("Ejecución", 8)
    fila = 9
    col = 0
    for nombre, var in ejecucion_vars.items():
        option(nombre, var, ESTADOS, fila, col)
        col += 1
        if col == 4:
            col = 0
            fila += 1

    seccion("Pruebas de funcionamiento", 12)
    option("Resultado de pruebas", var_pruebas, RESULTADOS, 13, 0)
    txt_observaciones_pruebas = textbox("Observaciones / hallazgos / acciones correctivas", 14, 0, 4, height=80)

    seccion("Acabados", 15)
    option("¿Planos de detalles y acabados?", var_planos_acabados, SI_NO, 16, 0)
    option("Generación de planos", var_generacion_planos, ["Sí", "No", "No aplica"], 16, 1)
    option("Etapa de acabados", var_etapa_acabados, ESTADOS, 16, 2)
    option("Obra blanca", var_obra_blanca, ESTADOS, 16, 3)

    seccion("Materiales misceláneos y consumibles", 17)
    panel_misc = celda(18, 0, 4)
    panel_misc.grid_columnconfigure(0, weight=2)
    panel_misc.grid_columnconfigure(1, weight=1)
    panel_misc.grid_columnconfigure(2, weight=1)
    panel_misc.grid_columnconfigure(3, weight=1)
    panel_misc.grid_columnconfigure(4, weight=3)
    ctk.CTkLabel(panel_misc, text="Material", font=("Montserrat", 11, "bold")).grid(row=0, column=0, sticky="w", padx=6)
    ctk.CTkLabel(panel_misc, text="¿Se requiere?", font=("Montserrat", 11, "bold")).grid(row=0, column=1, sticky="w", padx=6)
    ctk.CTkLabel(panel_misc, text="Cantidad", font=("Montserrat", 11, "bold")).grid(row=0, column=2, sticky="w", padx=6)
    ctk.CTkLabel(panel_misc, text="Unidad", font=("Montserrat", 11, "bold")).grid(row=0, column=3, sticky="w", padx=6)
    ctk.CTkLabel(panel_misc, text="Especificación / medida", font=("Montserrat", 11, "bold")).grid(row=0, column=4, sticky="w", padx=6)

    def agregar_material_misc_obra(nombre=""):
        fila_misc = 1 + len(materiales_miscelaneos_items)
        vm = ctk.StringVar(value=nombre)
        vr = ctk.StringVar(value="No")
        vc = ctk.StringVar()
        vu = ctk.StringVar(value="Pieza(s)")
        ve = ctk.StringVar()
        em = ctk.CTkEntry(panel_misc, textvariable=vm, height=30)
        em.grid(row=fila_misc, column=0, sticky="ew", padx=6, pady=3)
        if nombre:
            em.configure(state="readonly")
        ec = ctk.CTkEntry(panel_misc, textvariable=vc, width=90, height=30, placeholder_text="Ej. 20", state="disabled")
        ec.grid(row=fila_misc, column=2, sticky="w", padx=6, pady=3)
        ou = ctk.CTkOptionMenu(panel_misc, variable=vu, values=["Pieza(s)", "Paquete(s)", "Caja(s)", "Metro(s)", "Rollo(s)", "Juego(s)", "Litro(s)"], width=120, height=30, state="disabled")
        ou.grid(row=fila_misc, column=3, sticky="w", padx=6, pady=3)
        ee = ctk.CTkEntry(panel_misc, textvariable=ve, height=30, placeholder_text="Medida, material o presentación", state="disabled")
        ee.grid(row=fila_misc, column=4, sticky="ew", padx=6, pady=3)
        def toggle(_=None):
            estado = "normal" if vr.get() == "Sí" else "disabled"
            ec.configure(state=estado); ou.configure(state=estado); ee.configure(state=estado)
            if estado == "disabled":
                vc.set(""); ve.set("")
            validar_preview()
        om = ctk.CTkOptionMenu(panel_misc, variable=vr, values=["No", "Sí"], width=100, height=30, command=toggle)
        om.grid(row=fila_misc, column=1, sticky="w", padx=6, pady=3)
        materiales_miscelaneos_items.append({"material": vm, "requerido": vr, "cantidad": vc, "unidad": vu, "especificacion": ve})

    for nombre_misc in ("Pijas", "Tornillos", "Taquetes", "Clavos", "Alambre recocido", "Abrazaderas", "Cinchos plásticos", "Silicón / sellador", "Cinta de enmascarar", "Discos de corte"):
        agregar_material_misc_obra(nombre_misc)
    ctk.CTkButton(panel_misc, text="+ Agregar otro material", width=180, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=lambda: agregar_material_misc_obra("")).grid(row=99, column=0, columnspan=2, sticky="w", padx=6, pady=(7, 4))

    def obtener_materiales_misc_obra():
        return [{
            "material": i["material"].get().strip(), "cantidad": i["cantidad"].get().strip(),
            "unidad": i["unidad"].get().strip(), "especificacion": i["especificacion"].get().strip()
        } for i in materiales_miscelaneos_items if i["requerido"].get() == "Sí" and i["material"].get().strip()]

    seccion("Evidencias", 19)
    panel_evidencias = celda(20, 0, 4)
    lbl_evidencias = ctk.CTkLabel(panel_evidencias, text="Sin evidencias agregadas", font=SMALL_FONT, text_color=TEXT_SECONDARY)
    lbl_evidencias.pack(anchor="w", pady=(0, 5))

    def agregar_evidencia():
        rutas = filedialog.askopenfilenames(title="Agregar evidencias", filetypes=[("Archivos permitidos", "*.jpg *.jpeg *.png *.pdf *.docx"), ("Todos", "*.*")])
        for ruta in rutas:
            if ruta not in evidencias:
                evidencias.append(ruta)
        lbl_evidencias.configure(text=f"{len(evidencias)} evidencia(s) agregada(s)" if evidencias else "Sin evidencias agregadas")
        validar_preview()

    ctk.CTkButton(panel_evidencias, text="+ Agregar evidencia", width=170, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_evidencia).pack(anchor="w")

    seccion("Pre-entrega", 21)
    option("Resultado de pre-entrega", var_preentrega, ["Aprobadas", "Reprobadas", "Pendiente"], 22, 0)
    txt_preentrega = textbox("Recorrido de validación / correcciones pendientes", 23, 0, 4)

    seccion("Entrega formal", 24)
    option("Entrega formal", var_entrega_formal, SI_NO, 25, 0)
    entry("Fecha de entrega", var_fecha_entrega, 25, 1, "YYYY-MM-DD", date=True, required=False)
    txt_finales = textbox("Observaciones finales", 26, 0, 4)

    seccion("Firmas", 27)
    firmas_frame = celda(28, 0, 4)
    lbl_firma_cliente = ctk.CTkLabel(firmas_frame, text="Cliente: Sin firma", font=SMALL_FONT, text_color=TEXT_SECONDARY)
    lbl_firma_cliente.grid(row=0, column=0, padx=(0, 10), sticky="w")
    ctk.CTkButton(firmas_frame, text="✍ Capturar firma cliente", width=190, height=32, fg_color=SECONDARY, hover_color=BUTTON_HOVER,
                  command=lambda: firmar_en_popup(parent, var_firma_cliente, lambda: (lbl_firma_cliente.configure(text="Cliente: Firma capturada" if var_firma_cliente.get() else "Cliente: Sin firma"), validar_preview()), "Firma del cliente")).grid(row=0, column=1, padx=(0, 18), sticky="w")
    lbl_firma_tecnico = ctk.CTkLabel(firmas_frame, text="Técnico: Sin firma", font=SMALL_FONT, text_color=TEXT_SECONDARY)
    lbl_firma_tecnico.grid(row=0, column=2, padx=(0, 10), sticky="w")
    ctk.CTkButton(firmas_frame, text="✍ Capturar firma técnico", width=190, height=32, fg_color="#1F4E79", hover_color="#173B5C",
                  command=lambda: firmar_en_popup(parent, var_firma_tecnico, lambda: (lbl_firma_tecnico.configure(text="Técnico: Firma capturada" if var_firma_tecnico.get() else "Técnico: Sin firma"), validar_preview()), "Firma del técnico")).grid(row=0, column=3, sticky="w")

    bloquear_autollenados()

    def formulario_completo():
        return all(v.get().strip() for v in campos_validables) and bool(var_firma_cliente.get().strip()) and bool(var_firma_tecnico.get().strip())

    def datos_pdf():
        datos = {
            "Folio OBC": var_folio.get(), "Fecha": var_fecha.get(), "ACO": var_aco.get(), "Cliente": var_cliente.get(), "Contacto": var_contacto.get(),
            "Sucursal": var_sucursal.get(), "Dirección": var_direccion.get(), "Responsable AXIA": var_responsable.get(), "Supervisor": var_supervisor.get(),
            "Tipo de giro": var_tipo_giro.get(), "Nombre del proyecto": var_nombre_proyecto.get(), "Superficie disponible": var_superficie.get(),
            "Superficie adecuada": var_superficie_ok.get(), "Planos arquitectónicos": var_planos_arq.get(), "Requiere maquinaria": var_maquinaria.get(),
            "Permisos disponibles": var_permisos.get(), "Resultado de pruebas": var_pruebas.get(), "Planos de acabados": var_planos_acabados.get(),
            "Generación de planos": var_generacion_planos.get(), "Etapa de acabados": var_etapa_acabados.get(), "Obra blanca": var_obra_blanca.get(),
            "Pre-entrega": var_preentrega.get(), "Entrega formal": var_entrega_formal.get(), "Fecha de entrega": var_fecha_entrega.get(),
            "Observaciones iniciales": obtener_textbox(txt_observaciones_iniciales), "Observaciones pruebas": obtener_textbox(txt_observaciones_pruebas),
            "Observaciones pre-entrega": obtener_textbox(txt_preentrega), "Observaciones finales": obtener_textbox(txt_finales),
            "Evidencias": str(len(evidencias)),
            "Materiales misceláneos": "; ".join(
                f"{m['material']}: {m['cantidad'] or 'Por definir'} {m['unidad']}" + (f" ({m['especificacion']})" if m['especificacion'] else "")
                for m in obtener_materiales_misc_obra()
            ) or "Sin materiales misceláneos",
        }
        return datos

    def seccion_ejecucion_pdf():
        return [{"Actividad": k, "Estado": v.get()} for k, v in ejecucion_vars.items()]

    def seccion_materiales_pdf():
        return [{
            "Material": m["material"], "Cantidad": m["cantidad"] or "Por definir",
            "Unidad": m["unidad"], "Especificación": m["especificacion"]
        } for m in obtener_materiales_misc_obra()]

    def preview_pdf():
        if not formulario_completo():
            messagebox.showwarning("Preview", "El preview se activa cuando los campos obligatorios y firmas estén completos.")
            return
        generar_pdf_preview("Obra Civil", datos_pdf(), [
            ("Ejecución", ["Actividad", "Estado"], seccion_ejecucion_pdf()),
            ("Materiales misceláneos", ["Material", "Cantidad", "Unidad", "Especificación"], seccion_materiales_pdf()),
        ], var_firma_cliente.get(), var_firma_tecnico.get())

    def guardar_obra():
        if not formulario_completo():
            messagebox.showwarning("Campos obligatorios", "Debes llenar los campos obligatorios y capturar ambas firmas.")
            return
        folio = var_folio.get().strip()
        if buscar_obra_civil_por_folio(folio):
            folio = generar_siguiente_folio("OBC")
            var_folio.set(folio)
        datos = {
            "id_aco": datos_aco.get("id_aco"), "id_sucursal": datos_aco.get("id_sucursal"), "id_contacto": datos_aco.get("id_contacto"), "obc_folio": folio, "obc_fecha": var_fecha.get().strip() or None, "obc_aco_numero": var_aco.get().strip(),
            "obc_cliente": var_cliente.get().strip(), "obc_contacto": var_contacto.get().strip(), "obc_sucursal": var_sucursal.get().strip(),
            "obc_direccion": var_direccion.get().strip(), "obc_responsable_axia": var_responsable.get().strip(), "obc_supervisor": var_supervisor.get().strip(),
            "obc_tipo_giro": var_tipo_giro.get().strip(), "obc_nombre_proyecto": var_nombre_proyecto.get().strip(),
            "obc_superficie_disponible": var_superficie.get(), "obc_superficie_adecuada": var_superficie_ok.get(), "obc_planos_arquitectonicos": var_planos_arq.get(),
            "obc_requiere_maquinaria": var_maquinaria.get(), "obc_permisos": var_permisos.get(), "obc_observaciones_iniciales": obtener_textbox(txt_observaciones_iniciales),
            "obc_ejecucion_json": json.dumps({
                **{k: v.get() for k, v in ejecucion_vars.items()},
                "_materiales_miscelaneos": obtener_materiales_misc_obra(),
            }, ensure_ascii=False),
            "obc_pruebas_resultado": var_pruebas.get(), "obc_pruebas_observaciones": obtener_textbox(txt_observaciones_pruebas),
            "obc_planos_acabados": var_planos_acabados.get(), "obc_generacion_planos": var_generacion_planos.get(), "obc_etapa_acabados": var_etapa_acabados.get(),
            "obc_obra_blanca": var_obra_blanca.get(), "obc_evidencias_json": json.dumps(evidencias, ensure_ascii=False),
            "obc_preentrega_resultado": var_preentrega.get(), "obc_preentrega_observaciones": obtener_textbox(txt_preentrega),
            "obc_entrega_formal": var_entrega_formal.get(), "obc_fecha_entrega": var_fecha_entrega.get().strip() or None, "obc_observaciones_finales": obtener_textbox(txt_finales),
            "obc_firma_cliente_base64": var_firma_cliente.get(), "obc_firma_tecnico_base64": var_firma_tecnico.get(), "obc_estatus": 1, "creado_por": usuario_activo.get("usuario"),
        }
        resultado = crear_obra_civil(datos)
        if resultado:
            registrar_movimiento(modulo="Obra Civil", accion="CREAR", descripcion=f"El usuario creó la obra civil {folio}", registro_afectado=folio)
            ruta_pdf = generar_pdf_archivo("Obra Civil", datos_pdf(), nombre_archivo=folio, subcarpeta="obras_civiles", secciones_tabla=[
                ("Ejecución", ["Actividad", "Estado"], seccion_ejecucion_pdf()),
                ("Materiales misceláneos", ["Material", "Cantidad", "Unidad", "Especificación"], seccion_materiales_pdf()),
            ], firma_base64=var_firma_cliente.get(), firma_tecnico_base64=var_firma_tecnico.get())
            mensaje_pdf = f"\n\nPDF guardado en:\n{ruta_pdf}" if ruta_pdf else "\n\nNo se pudo guardar el PDF local."
            messagebox.showinfo("Registro correcto", "La obra civil fue registrada correctamente." + mensaje_pdf)
            app.mostrar_vista_inicio_aco()
        else:
            messagebox.showerror("Error", "No se pudo registrar la obra civil. Revisa que exista la tabla db_obras_civiles en Supabase.")

    botones = ctk.CTkFrame(contenedor, fg_color="#F4F4F4", height=58, corner_radius=0)
    botones.grid(row=1, column=0, sticky="ew")
    barra_botones = ctk.CTkFrame(botones, fg_color="transparent")
    barra_botones.pack(anchor="center", pady=8)
    ctk.CTkButton(barra_botones, text="⬅ Atrás", width=120, height=38, corner_radius=10, fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT, command=app.volver_atras).grid(row=0, column=0, padx=8)
    ctk.CTkButton(barra_botones, text="💾 Guardar Obra Civil", width=190, height=38, corner_radius=10, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=guardar_obra).grid(row=0, column=1, padx=8)
    btn_preview = ctk.CTkButton(barra_botones, text="👁 Preview PDF", width=165, height=38, corner_radius=10, fg_color="#1F4E79", hover_color="#173B5C", font=BUTTON_FONT, command=preview_pdf, state="disabled")
    btn_preview.grid(row=0, column=2, padx=8)
    ctk.CTkButton(barra_botones, text="↩ Cancelar", width=130, height=38, corner_radius=10, fg_color="gray", font=BUTTON_FONT, command=app.mostrar_vista_inicio_aco).grid(row=0, column=3, padx=8)
    enfocar_inicio_formulario(card, foco_inicial)
    validar_preview()
