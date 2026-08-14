from core.error_reporting import show_operation_error
"""
Formulario Orden de Servicio AXIA.
Actualizado: campos compactos, renglones dinámicos, firma del cliente y preview PDF.
"""

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import json
from datetime import datetime
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox, filedialog
from ui.native_combobox import NativeComboBox

from ui.colors import SECONDARY, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER
from ui.date_picker import abrir_selector_fecha
from ui.fonts import TEXT_SM, BUTTON_FONT
from app_context import obtener_usuario_actual
from services.movimientos_service import registrar_movimiento
from services.aco_context_service import normalizar_datos_aco
from services.acos_service import buscar_aco_por_numero
from services.folios_service import generar_siguiente_folio
from services.usuarios_service import obtener_supervisores_formulario, obtener_nombres_usuarios_por_tipos
from services.ordenes_servicio_service import (
    crear_orden_servicio, buscar_orden_por_folio, actualizar_orden_servicio,
    obtener_contextos_aco_disponibles_cierre,
)
from services.bitacora_evidencias_service import subir_evidencias_orden_servicio
from security.permissions import puede_generar_orden_servicio
from views.formato_helpers import ENTRY_H, OPTION_H, LABEL_FONT, SMALL_FONT, SECTION_FONT, obtener_textbox, enfocar_inicio_formulario, firmar_en_popup, generar_pdf_preview, generar_pdf_archivo

TIPOS_SERVICIO = ["Urgente", "Correctivo", "Capacitación", "Póliza", "Reubicación", "Ordinario", "Preventivo", "Desmantelamiento", "Siniestro", "Otro"]
EVALUACIONES = ["Excelente", "Bueno", "Regular", "Malo", "No aplica"]
MOVIMIENTOS_EQUIPO = ["Instalación", "Reparación", "Garantía"]


def mostrar_orden_servicio(parent, app, aco=None):
    usuario_activo = obtener_usuario_actual()
    if not puede_generar_orden_servicio(usuario_activo):
        messagebox.showerror("Acceso denegado", "No tienes permisos para generar órdenes de servicio.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=7, pady=5)

    datos_aco = normalizar_datos_aco(aco)
    supervisores_disponibles = obtener_supervisores_formulario()
    entradas_bloqueadas = []
    campos_validables = []
    textboxes_validables = []
    btn_preview = None

    var_folio = ctk.StringVar(value=generar_siguiente_folio("OS"))
    var_fecha = ctk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
    var_cliente = ctk.StringVar(value=datos_aco.get("cliente", ""))
    var_sucursal = ctk.StringVar(value=datos_aco.get("sucursal", ""))
    var_domicilio = ctk.StringVar(value=datos_aco.get("direccion", ""))
    var_encargado_general = ctk.StringVar(value=datos_aco.get("contacto", ""))
    var_solicitante = ctk.StringVar(value=datos_aco.get("contacto", ""))
    var_correo = ctk.StringVar(value=datos_aco.get("correo", ""))
    var_celular = ctk.StringVar(value=datos_aco.get("telefono", ""))
    var_hora_llegada = ctk.StringVar()
    var_hora_salida = ctk.StringVar()
    var_aco = ctk.StringVar(value=datos_aco.get("aco_numero", ""))
    var_supervisor = ctk.StringVar(value=datos_aco.get("supervisor", ""))
    if supervisores_disponibles and not var_supervisor.get().strip():
        var_supervisor.set(supervisores_disponibles[0])
    var_encargado_servicio = ctk.StringVar()
    var_tecnico_selector = ctk.StringVar()
    var_tecnicos = ctk.StringVar()
    tecnicos_seleccionados = []
    evidencias_locales: list[str] = []
    os_existente = {}
    contexto_cierre = {}
    var_eval_trato = ctk.StringVar(value="Bueno")
    var_eval_habilidades = ctk.StringVar(value="Bueno")
    var_eval_velocidad = ctk.StringVar(value="Bueno")
    var_eval_otro = ctk.StringVar(value="No aplica")
    var_firma_cliente = ctk.StringVar()
    var_estado_firma = ctk.StringVar(value="Sin firma")

    var_tipo_servicio = ctk.StringVar(value=datos_aco.get("tipo_servicio", ""))
    encargados_disponibles = obtener_nombres_usuarios_por_tipos([2, 3, 4])
    tecnicos_disponibles = obtener_nombres_usuarios_por_tipos([4])
    contextos_cierre = obtener_contextos_aco_disponibles_cierre()
    contexto_por_aco = {x["aco_numero"]: x for x in contextos_cierre}
    acos_disponibles = list(contexto_por_aco)
    if var_aco.get() and var_aco.get() not in acos_disponibles:
        acos_disponibles.insert(0, var_aco.get())

    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_rowconfigure(1, weight=0)
    contenedor.grid_columnconfigure(0, weight=1)

    card = ctk.CTkScrollableFrame(contenedor, width=1280, fg_color=WHITE, corner_radius=18)
    card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
    form = ctk.CTkFrame(card, fg_color="transparent")
    form.pack(fill="x", expand=True, padx=12, pady=(9, 4))
    # Cinco columnas permiten una distribución más compacta de los datos generales.
    for col in range(5):
        form.grid_columnconfigure(col, weight=1, uniform="cols")

    def seccion(texto, fila):
        ctk.CTkLabel(form, text=texto, font=SECTION_FONT, text_color=TEXT_PRIMARY).grid(row=fila, column=0, columnspan=5, sticky="w", pady=(6, 3))

    def label(parent_, texto):
        ctk.CTkLabel(parent_, text=texto, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 1))

    def celda(fila, col, colspan=1):
        frame = ctk.CTkFrame(form, fg_color="transparent")
        frame.grid(row=fila, column=col, columnspan=colspan, sticky="ew", padx=2, pady=(0, 3))
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def entry(texto, var, placeholder="", fila=0, col=0, state="normal", lock=False, date=False, required=True, width=None):
        c = celda(fila, col)
        label(c, texto)
        e = ctk.CTkEntry(c, textvariable=var, placeholder_text=placeholder, height=ENTRY_H, corner_radius=8, font=SMALL_FONT, state=state, width=width or 240)
        if width:
            e.pack(anchor="w")
        else:
            e.pack(fill="x")
        if date and state != "disabled":
            e.bind("<Button-1>", lambda _event, v=var: (abrir_selector_fecha(c, v), validar_preview()))
        if lock:
            entradas_bloqueadas.append(e)
        if required and state != "disabled":
            campos_validables.append(var)
            var.trace_add("write", lambda *_: validar_preview())
        return e

    def option(texto, var, values, fila=0, col=0, required=True, command=None, state="normal", width=None, colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        cb = NativeComboBox(c, variable=var, values=values, height=OPTION_H, font=SMALL_FONT, command=command, state=state, width=width)
        cb.pack(fill="x")
        if required:
            campos_validables.append(var)
            var.trace_add("write", lambda *_: validar_preview())
        return cb

    def texto_largo(texto, fila, alto=70, required=True):
        c = celda(fila, 0, 5)
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

    def _cargar_tecnicos_desde_texto(texto):
        tecnicos_seleccionados.clear()
        for nombre in str(texto or "").replace(",", "|").split("|"):
            nombre = nombre.strip()
            if nombre and nombre not in tecnicos_seleccionados:
                tecnicos_seleccionados.append(nombre)
        var_tecnicos.set(" | ".join(tecnicos_seleccionados))

    def cargar_aco(numero=None):
        nonlocal datos_aco, os_existente, contexto_cierre
        numero = str(numero or var_aco.get() or "").strip().upper()
        if not numero or numero == "Sin ACOs disponibles":
            return
        registro = buscar_aco_por_numero(numero)
        if not registro:
            messagebox.showwarning("ACO no encontrado", "No se encontró información para el ACO seleccionado.")
            return
        datos_aco = normalizar_datos_aco(registro)
        contexto_cierre = dict(contexto_por_aco.get(numero, {}) or {})
        os_existente = dict(contexto_cierre.get("os") or {})
        ot = dict(contexto_cierre.get("ot") or {})
        var_aco.set(numero)
        var_cliente.set(datos_aco.get("cliente", "") or ot.get("ot_cliente", ""))
        var_sucursal.set(datos_aco.get("sucursal", "") or ot.get("ot_sucursal", ""))
        var_domicilio.set(datos_aco.get("direccion", "") or ot.get("ot_sucursal", ""))
        contacto = datos_aco.get("contacto", "") or ot.get("ot_contacto", "")
        var_encargado_general.set(contacto)
        var_solicitante.set(contacto)
        var_correo.set(datos_aco.get("correo", ""))
        var_celular.set(datos_aco.get("telefono", ""))
        if os_existente:
            var_folio.set(str(os_existente.get("os_folio") or var_folio.get()))
            var_tipo_servicio.set(str(os_existente.get("os_tipo_servicio") or datos_aco.get("tipo_servicio", "")))
            var_supervisor.set(str(os_existente.get("os_supervisor") or datos_aco.get("supervisor", "")))
            var_encargado_servicio.set(str(os_existente.get("os_encargado_servicio") or ""))
            _cargar_tecnicos_desde_texto(os_existente.get("os_tecnicos") or os_existente.get("os_tecnico"))
        else:
            tipo = datos_aco.get("tipo_servicio", "")
            if tipo in TIPOS_SERVICIO:
                var_tipo_servicio.set(tipo)
            if datos_aco.get("supervisor"):
                var_supervisor.set(datos_aco.get("supervisor"))
        bloquear_autollenados()
        validar_preview()

    def validar_preview():
        try:
            if btn_preview is not None:
                btn_preview.configure(state="normal" if formulario_completo() else "disabled")
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    seccion("Información General", 0)
    # Fila 1: exactamente cinco bloques, como el diseño operativo de referencia.
    entry("Folio OS", var_folio, "Automático", 1, 0, state="disabled", required=False, width=115)
    entry("Fecha", var_fecha, "DD/MM/AAAA", 1, 1, state="disabled", required=False, width=210)
    option("ACO", var_aco, acos_disponibles or ["Sin ACOs disponibles"], 1, 2, command=cargar_aco, state="normal" if acos_disponibles else "disabled", width=365)
    entry("Cliente", var_cliente, "Autollenado", 1, 3, lock=True, width=355)
    entry("Sucursal", var_sucursal, "Autollenado", 1, 4, lock=True, width=275)

    # Fila 2: domicilio y datos de contacto.
    entry("Domicilio", var_domicilio, "Autollenado", 2, 0, lock=True, width=370)
    entry("Encargado", var_encargado_general, "Autollenado", 2, 1, lock=True, width=300)
    entry("Solicitante", var_solicitante, "Autollenado", 2, 2, lock=True, width=175)
    entry("Correo", var_correo, "Autollenado", 2, 3, lock=True, width=190)
    entry("Celular", var_celular, "Autollenado", 2, 4, lock=True, width=220)

    # Fila 3: horarios y tipo de servicio, compactos y alineados a la izquierda.
    entry("Hora de Llegada", var_hora_llegada, "HH:MM", 3, 0, width=200)
    entry("Hora de Salida", var_hora_salida, "HH:MM", 3, 1, width=200)
    option("Tipo de Servicio", var_tipo_servicio, TIPOS_SERVICIO, 3, 2, width=365)

    seccion("Asignación del Servicio", 4)
    option("Supervisor", var_supervisor, supervisores_disponibles or ["Sin usuarios tipo 2 o 3 registrados"], 5, 0)
    option("Encargado AXIA", var_encargado_servicio, encargados_disponibles or ["Sin usuarios tipo 2, 3 o 4 registrados"], 5, 1)

    c_tecnicos = celda(6, 0, 5)
    label(c_tecnicos, "Técnicos en sitio")
    fila_tecnicos = ctk.CTkFrame(c_tecnicos, fg_color="transparent")
    fila_tecnicos.pack(fill="x")
    combo_tecnico = NativeComboBox(fila_tecnicos, variable=var_tecnico_selector, values=tecnicos_disponibles or ["Sin técnicos tipo 4 registrados"], height=OPTION_H, font=SMALL_FONT, state="normal" if tecnicos_disponibles else "disabled")
    combo_tecnico.pack(side="left", fill="x", expand=True, padx=(0, 5))
    lbl_tecnicos = ctk.CTkLabel(c_tecnicos, textvariable=var_tecnicos, font=SMALL_FONT, text_color=TEXT_SECONDARY, anchor="w", justify="left")
    lbl_tecnicos.pack(fill="x", pady=(3,0))

    def agregar_tecnico():
        nombre = var_tecnico_selector.get().strip()
        if nombre and nombre in tecnicos_disponibles and nombre not in tecnicos_seleccionados:
            tecnicos_seleccionados.append(nombre)
            var_tecnicos.set(" | ".join(tecnicos_seleccionados))
            validar_preview()

    def quitar_ultimo_tecnico():
        if tecnicos_seleccionados:
            tecnicos_seleccionados.pop()
            var_tecnicos.set(" | ".join(tecnicos_seleccionados))
            validar_preview()

    ctk.CTkButton(fila_tecnicos, text="+ Agregar", width=100, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_tecnico).pack(side="left", padx=3)
    ctk.CTkButton(fila_tecnicos, text="Quitar último", width=115, height=30, fg_color="#DC2626", hover_color="#B91C1C", command=quitar_ultimo_tecnico).pack(side="left", padx=3)
    campos_validables.append(var_tecnicos)
    var_tecnicos.trace_add("write", lambda *_: validar_preview())

    txt_descripcion = texto_largo("Descripción del servicio y/o instalación", 7, 70)

    c_evid = celda(8, 0, 5)
    label(c_evid, "Evidencias fotográficas")
    lbl_evidencias = ctk.CTkLabel(c_evid, text="Sin fotografías agregadas", font=SMALL_FONT, text_color=TEXT_SECONDARY, anchor="w", justify="left")
    lbl_evidencias.pack(fill="x", pady=(0,4))
    def refrescar_evidencias():
        nombres = [Path(x).name for x in evidencias_locales]
        texto = "Sin fotografías agregadas" if not nombres else f"{len(nombres)} fotografía(s): " + ", ".join(nombres[:4]) + (f" y {len(nombres)-4} más" if len(nombres)>4 else "")
        lbl_evidencias.configure(text=texto)
        validar_preview()
    def agregar_fotos():
        rutas = filedialog.askopenfilenames(title="Agregar evidencias de Orden de Servicio", filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp"), ("Todos", "*.*")])
        for ruta in rutas:
            if ruta not in evidencias_locales:
                evidencias_locales.append(ruta)
        refrescar_evidencias()
    def quitar_ultima_foto():
        if evidencias_locales:
            evidencias_locales.pop()
        refrescar_evidencias()
    acc_evid = ctk.CTkFrame(c_evid, fg_color="transparent"); acc_evid.pack(anchor="w")
    ctk.CTkButton(acc_evid, text="+ Agregar fotos", width=150, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_fotos).pack(side="left", padx=(0,5))
    ctk.CTkButton(acc_evid, text="Eliminar última", width=135, height=30, fg_color="#DC2626", hover_color="#B91C1C", command=quitar_ultima_foto).pack(side="left")

    seccion("Entrada/Salida de Equipos", 9)
    equipos = []
    acciones_equipos = celda(10, 0, 5)
    equipos_frame = celda(11, 0, 5)
    # Un CTkFrame vacío conserva altura propia; ocultarlo evita el gran espacio en blanco
    # entre Entrada/Salida de Equipos y Evaluación del Servicio.
    equipos_frame.grid_remove()
    headers = ["Equipo", "Número de Serie", "Movimiento", "Diagnóstico de la Falla"]

    def agregar_equipo():
        equipos_frame.grid()
        row_vars = {"Equipo": ctk.StringVar(), "Número de Serie": ctk.StringVar(), "Movimiento": ctk.StringVar(value="Instalación"), "Diagnóstico de la Falla": ctk.StringVar()}
        fila = ctk.CTkFrame(equipos_frame, fg_color="transparent")
        fila.pack(fill="x", pady=1)
        row_vars["_frame"] = fila
        equipos.append(row_vars)
        for j, h in enumerate(headers):
            sub = ctk.CTkFrame(fila, fg_color="transparent")
            sub.grid(row=0, column=j, sticky="ew", padx=2)
            fila.grid_columnconfigure(j, weight=1)
            ctk.CTkLabel(sub, text=h, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w")
            if h == "Movimiento":
                NativeComboBox(sub, variable=row_vars[h], values=MOVIMIENTOS_EQUIPO, height=OPTION_H, font=SMALL_FONT, command=lambda _v=None: validar_preview()).pack(fill="x")
            else:
                ctk.CTkEntry(sub, textvariable=row_vars[h], height=ENTRY_H, corner_radius=9, font=SMALL_FONT).pack(fill="x")
                row_vars[h].trace_add("write", lambda *_: validar_preview())
        def eliminar_equipo():
            fila.destroy()
            equipos[:] = [x for x in equipos if x is not row_vars]
            if not equipos:
                equipos_frame.grid_remove()
            validar_preview()
        ctk.CTkButton(fila,text="Eliminar",width=82,height=30,fg_color="#DC2626",hover_color="#B91C1C",command=eliminar_equipo).grid(row=0,column=len(headers),sticky="s",padx=2)
        validar_preview()

    ctk.CTkButton(acciones_equipos, text="+ Nuevo equipo", width=150, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_equipo).pack(anchor="w")
    # Sección opcional: no se crea ningún renglón hasta que el usuario pulse "+ Nuevo equipo".

    seccion("Evaluación del Servicio", 12)
    eval_frame = celda(13, 0, 5)
    eval_grid = ctk.CTkFrame(eval_frame, fg_color="transparent")
    eval_grid.pack(anchor="w")
    def eval_compacta(texto, var, col):
        c = ctk.CTkFrame(eval_grid, fg_color="transparent", width=165)
        c.grid(row=0, column=col, sticky="w", padx=(0,8))
        c.grid_propagate(False)
        c.configure(height=52)
        label(c, texto)
        NativeComboBox(c, variable=var, values=EVALUACIONES, height=OPTION_H, font=SMALL_FONT, width=145).pack(fill="x")
        campos_validables.append(var); var.trace_add("write", lambda *_: validar_preview())
    eval_compacta("Trato y actitud", var_eval_trato, 0)
    eval_compacta("Habilidades", var_eval_habilidades, 1)
    eval_compacta("Velocidad y calidad", var_eval_velocidad, 2)
    eval_compacta("Otro", var_eval_otro, 3)

    seccion("Firma del Cliente", 14)
    c_firma = celda(15, 0, 5)
    ctk.CTkLabel(c_firma, textvariable=var_estado_firma, font=SMALL_FONT, text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 5))
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
        if not var_firma_cliente.get().strip():
            return False
        return True

    def secciones_equipos_pdf():
        filas = equipos_limpios()
        return [("Entrada/Salida de Equipos", headers, filas)] if filas else []

    def datos_pdf():
        return {
            "Folio OS": var_folio.get(), "Fecha": var_fecha.get(), "ACO": var_aco.get(), "Cliente": var_cliente.get(), "Sucursal": var_sucursal.get(),
            "Domicilio": var_domicilio.get(), "Encargado": var_encargado_general.get(), "Solicitante": var_solicitante.get(), "Correo": var_correo.get(),
            "Celular": var_celular.get(), "Hora de Llegada": var_hora_llegada.get(), "Hora de Salida": var_hora_salida.get(),
            "Tipo de Servicio": var_tipo_servicio.get(), "Supervisor": var_supervisor.get(), "Encargado Servicio": var_encargado_servicio.get(),
            "Técnicos": var_tecnicos.get(), "Descripción": obtener_textbox(txt_descripcion), "Observaciones": "", "Evidencia Fotográfica": list(evidencias_locales),
            "Trato y actitud": var_eval_trato.get(), "Habilidades y conocimientos": var_eval_habilidades.get(), "Velocidad y calidad": var_eval_velocidad.get(), "Otro": var_eval_otro.get()
        }

    def preview_pdf():
        if not formulario_completo():
            messagebox.showwarning("Preview", "El preview se activa cuando todos los campos obligatorios estén completos, incluyendo firma y técnicos.")
            return
        generar_pdf_preview("Orden de Servicio", datos_pdf(), secciones_equipos_pdf(), firma_base64=var_firma_cliente.get())

    def guardar_orden():
        if not formulario_completo():
            messagebox.showwarning("Campos obligatorios", "Debes llenar todos los campos obligatorios, seleccionar tipo de servicio, asignar técnicos y agregar firma del cliente.")
            return
        folio = var_folio.get().strip()
        if not os_existente and buscar_orden_por_folio(folio):
            folio = generar_siguiente_folio("OS")
            var_folio.set(folio)
        equipos_db = [{"equipo": e["Equipo"], "numero_serie": e["Número de Serie"], "movimiento": e["Movimiento"], "diagnostico_falla": e["Diagnóstico de la Falla"]} for e in equipos_limpios()]
        datos = {
            "id_aco": datos_aco.get("id_aco"), "id_sucursal": datos_aco.get("id_sucursal"), "id_contacto": datos_aco.get("id_contacto"),
            "ot_id": contexto_cierre.get("ot_id"), "os_folio_ot": contexto_cierre.get("ot_folio"), "os_folio_levantamiento": contexto_cierre.get("ot_folio_levantamiento"),
            "os_folio": folio, "os_fecha": var_fecha.get().strip() or None, "os_aco_numero": var_aco.get().strip(),
            "os_cliente": var_cliente.get().strip(), "os_sucursal": var_sucursal.get().strip(), "os_domicilio": var_domicilio.get().strip(),
            "os_encargado": var_encargado_general.get().strip(), "os_solicitante": var_solicitante.get().strip(), "os_correo": var_correo.get().strip(), "os_celular": var_celular.get().strip(),
            "os_hora_llegada": var_hora_llegada.get().strip(), "os_hora_salida": var_hora_salida.get().strip(), "os_tipos_servicio_json": json.dumps([var_tipo_servicio.get().strip()], ensure_ascii=False),
            "os_tipo_servicio": var_tipo_servicio.get().strip(), "os_supervisor": var_supervisor.get().strip(), "os_encargado_servicio": var_encargado_servicio.get().strip(),
            "os_tecnicos": var_tecnicos.get().strip(), "os_tecnico": var_tecnicos.get().strip(), "os_descripcion": obtener_textbox(txt_descripcion), "os_observaciones": "", "os_fotos": [],
            "os_equipos_json": json.dumps(equipos_db, ensure_ascii=False), "os_eval_trato": var_eval_trato.get(), "os_eval_habilidades": var_eval_habilidades.get(),
            "os_eval_velocidad": var_eval_velocidad.get(), "os_eval_otro": var_eval_otro.get(), "os_firma_cliente": var_firma_cliente.get(), "os_estatus": 1, "os_prioridad": 2,
            "creado_por": usuario_activo.get("usuario")
        }
        id_os_existente = os_existente.get("id_orden") if os_existente else None
        resultado = actualizar_orden_servicio(id_os_existente, datos) if id_os_existente else crear_orden_servicio(datos)
        if resultado:
            fotos_subidas = []
            aviso_fotos = ""
            if evidencias_locales:
                try:
                    fotos_subidas = subir_evidencias_orden_servicio(folio, evidencias_locales)
                    registro_resultado = resultado[0] if isinstance(resultado, list) and resultado else {}
                    id_orden = id_os_existente or registro_resultado.get("id_orden") or (buscar_orden_por_folio(folio) or {}).get("id_orden")
                    if id_orden and fotos_subidas:
                        actualizar_orden_servicio(id_orden, {"os_fotos": fotos_subidas})
                except Exception as error:
                    logger.exception("La OS se guardó, pero falló la carga de fotografías.")
                    aviso_fotos = f"\n\nLa orden se guardó, pero no se pudieron subir todas las fotografías:\n{error}"
            accion = "ACTUALIZAR" if id_os_existente else "CREAR"
            registrar_movimiento(modulo="Órdenes de Servicio", accion=accion, descripcion=f"El usuario guardó la orden {folio}", registro_afectado=folio)
            datos_pdf_final = datos_pdf()
            datos_pdf_final["Evidencia Fotográfica"] = fotos_subidas if fotos_subidas else list(evidencias_locales)
            ruta_pdf = generar_pdf_archivo("Orden de Servicio", datos_pdf_final, nombre_archivo=folio, subcarpeta="ordenes_servicio", secciones_tabla=secciones_equipos_pdf(), firma_base64=var_firma_cliente.get())
            mensaje_pdf = f"\n\nPDF guardado en:\n{ruta_pdf}" if ruta_pdf else "\n\nNo se pudo guardar el PDF local."
            messagebox.showinfo("Registro correcto", "La orden de servicio fue guardada correctamente." + mensaje_pdf + aviso_fotos)
            app.mostrar_vista_inicio_aco()
        else:
            show_operation_error("Error al guardar", "Registrar orden de servicio")


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
    barra_botones.pack(anchor="center", pady=4)
    btn_guardar = ctk.CTkButton(barra_botones, text="💾 Guardar Orden", width=185, height=38, corner_radius=10, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=guardar_orden)
    btn_preview = ctk.CTkButton(barra_botones, text="👁 Preview PDF", width=165, height=38, corner_radius=10, fg_color="#1F4E79", hover_color="#173B5C", font=BUTTON_FONT, command=preview_pdf, state="disabled")
    ctk.CTkButton(barra_botones, text="⬅ Atrás", width=120, height=38, corner_radius=10, fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT, command=volver_a_selector_aco).grid(row=0, column=0, padx=4)
    btn_guardar.grid(row=0, column=1, padx=4)
    btn_preview.grid(row=0, column=2, padx=4)
    ctk.CTkButton(barra_botones, text="↩ Cancelar", width=130, height=38, corner_radius=10, fg_color="gray", font=BUTTON_FONT, command=app.mostrar_vista_inicio_aco).grid(row=0, column=3, padx=4)

    enfocar_inicio_formulario(card)
    validar_preview()

    if var_aco.get():
        cargar_aco(var_aco.get())
    elif aco:
        bloquear_autollenados()
    validar_preview()
