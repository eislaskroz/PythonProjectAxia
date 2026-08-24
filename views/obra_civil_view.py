from core.error_reporting import show_operation_error
"""Formulario Obra Civil / Proyecto Ejecutivo AXIA."""

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import json
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox, filedialog
from ui.native_combobox import NativeComboBox
from views.levantamientos.catalogos_canalizacion import (
    TIPOS_ABRAZADERAS, TIPOS_CABLE_DATOS_CONTROL, TIPOS_CANALIZACION,
    TIPOS_CONECTORES, TIPOS_COPLES, TIPOS_REGISTROS, TIPOS_TUBOS, TAMANOS_TUBOS,
    especificaciones_por_categoria,
)

from app_context import obtener_usuario_actual
from security.permissions import puede_generar_levantamiento
from services.aco_context_service import normalizar_datos_aco
from services.acos_service import buscar_aco_por_numero
from services.clientes_service import buscar_clientes, construir_direccion_cliente
from services.sucursales_service import obtener_sucursales_por_cliente, obtener_contactos_por_sucursal, construir_domicilio_sucursal
from services.folios_service import generar_siguiente_folio
from services.usuarios_service import (
    obtener_supervisores_formulario,
    obtener_encargados_proyecto_formulario,
    obtener_tecnicos_responsables,
)
from services.movimientos_service import registrar_movimiento
from services.materiales_catalogo_service import obtener_materiales_por_especialidad, UNIDADES_MATERIAL
from services.equipos_catalogo_service import (
    MARCAS_COMUNES, obtener_nombres_familias, obtener_subfamilias,
    obtener_sugerencia_caracteristicas
)
from services.obras_civiles_service import crear_obra_civil, buscar_obra_civil_por_folio, actualizar_evidencias_obra_civil, actualizar_archivos_obra_civil
from services.obra_conceptos_service import obtener_conceptos_obra, obtener_tipos_concepto_obra, filtrar_conceptos_por_tipo
from services.bitacora_evidencias_service import subir_evidencias_obra_civil, subir_archivos_obra_civil
from ui.colors import PRIMARY, SECONDARY, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER
from ui.date_picker import abrir_selector_fecha
from ui.fonts import BUTTON_FONT
from views.formato_helpers import ENTRY_H, OPTION_H, LABEL_FONT, SMALL_FONT, SECTION_FONT, generar_pdf_preview, generar_pdf_archivo, obtener_textbox, enfocar_inicio_formulario, anotacion_plano_popup

SI_NO = ["Sí", "No"]
ESTADOS = ["Pendiente", "En proceso", "Terminado"]
RESULTADOS = ["Aprobadas", "Reprobadas", "Pendiente"]


def mostrar_obra_civil(parent, app, aco=None, borrador=None):
    usuario_activo = obtener_usuario_actual()
    if not puede_generar_levantamiento(usuario_activo):
        messagebox.showerror("Acceso denegado", "No tienes permisos para generar registros de obra civil.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    datos_aco = normalizar_datos_aco(aco)
    supervisores_disponibles = obtener_supervisores_formulario()
    encargados_proyecto_disponibles = obtener_encargados_proyecto_formulario()
    tecnicos_disponibles = obtener_tecnicos_responsables()
    entradas_bloqueadas = []
    campos_validables = []
    evidencias = []
    archivos_adjuntos = []
    archivos_adjuntos_existentes = []
    materiales_miscelaneos_items = []
    canalizacion_materiales_items = []
    conceptos_obra_items = []
    catalogo_conceptos_obra = obtener_conceptos_obra()
    btn_preview = None
    btn_guardar = None

    var_folio = ctk.StringVar(value=generar_siguiente_folio("OBC"))
    var_fecha = ctk.StringVar()
    var_desea_anotacion_plano = ctk.StringVar(value="No")
    var_anotacion_plano_base64 = ctk.StringVar()
    var_desea_evidencias = ctk.StringVar(value="No")
    var_desea_archivos_adjuntos = ctk.StringVar(value="No")
    var_trabajo_alturas = ctk.StringVar(value="No")
    var_sistema_acceso = ctk.StringVar(value="Escalera")
    var_altura_trabajo = ctk.StringVar()
    var_riesgo_trabajo = ctk.StringVar(value="Bajo")
    var_requiere_canalizacion = ctk.StringVar(value="Sí")
    var_aco = ctk.StringVar(value=datos_aco.get("aco_numero", ""))
    var_cliente = ctk.StringVar(value=datos_aco.get("cliente", ""))
    var_cliente_selector = ctk.StringVar()
    var_contacto = ctk.StringVar(value=datos_aco.get("contacto", ""))
    var_telefono = ctk.StringVar(value=datos_aco.get("telefono", ""))
    var_correo = ctk.StringVar(value=datos_aco.get("correo", ""))
    var_sucursal = ctk.StringVar(value=datos_aco.get("sucursal", ""))
    var_encargado_sucursal = ctk.StringVar(value=datos_aco.get("contacto", ""))
    var_direccion = ctk.StringVar(value=datos_aco.get("direccion", ""))
    var_responsable = ctk.StringVar(value=datos_aco.get("responsable", ""))
    var_supervisor = ctk.StringVar(value=datos_aco.get("supervisor", ""))
    var_tecnico = ctk.StringVar()
    if supervisores_disponibles and not var_supervisor.get().strip():
        var_supervisor.set(supervisores_disponibles[0])
    if encargados_proyecto_disponibles and not var_responsable.get().strip():
        var_responsable.set(encargados_proyecto_disponibles[0])
    if tecnicos_disponibles and not var_tecnico.get().strip():
        var_tecnico.set(tecnicos_disponibles[0])
    var_tipo_giro = ctk.StringVar()
    var_nombre_proyecto = ctk.StringVar()
    var_dias_trabajo = ctk.StringVar()
    var_personas_considerar = ctk.StringVar()
    var_requiere_epp = ctk.StringVar(value="No")
    epp_items = []

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
    var_planos_acabados = ctk.StringVar(value="Sí")
    var_generacion_planos = ctk.StringVar(value="No aplica")
    var_etapa_acabados = ctk.StringVar(value="Pendiente")
    var_obra_blanca = ctk.StringVar(value="Pendiente")

    # En el flujo sin ACO, Obra Civil selecciona al cliente directamente de Supabase.
    clientes_disponibles = []
    clientes_por_nombre = {}
    try:
        clientes_disponibles = buscar_clientes("", limite=500) or []
    except Exception:
        clientes_disponibles = []

    for cliente_db in clientes_disponibles:
        nombre = str(cliente_db.get("cli_razonsocial", "") or "").strip()
        if nombre:
            clientes_por_nombre[nombre] = cliente_db

    if not aco and clientes_por_nombre:
        primer_cliente = sorted(clientes_por_nombre.keys())[0]
        var_cliente_selector.set(primer_cliente)
    elif aco:
        cliente_aco = clientes_por_nombre.get(str(var_cliente.get() or "").strip())
        if cliente_aco:
            var_direccion.set(construir_direccion_cliente(cliente_aco))

    sucursales_por_nombre = {}
    contactos_por_nombre = {}
    combo_sucursal = {"widget": None}
    combo_encargado = {"widget": None}
    seleccion_catalogo = {"id_cliente": datos_aco.get("id_cliente"), "id_sucursal": datos_aco.get("id_sucursal"), "id_contacto": datos_aco.get("id_contacto")}

    def _id_cliente(cliente):
        cliente = cliente or {}
        return cliente.get("id_cliente") or cliente.get("cli_id")

    def _id_sucursal(sucursal):
        sucursal = sucursal or {}
        return sucursal.get("suc_id") or sucursal.get("id_sucursal")

    def _id_contacto(contacto):
        contacto = contacto or {}
        return contacto.get("con_id") or contacto.get("id_contacto")

    def _nombre_sucursal(sucursal):
        return str((sucursal or {}).get("suc_nombre") or construir_domicilio_sucursal(sucursal) or "Sucursal sin nombre").strip()

    def _nombre_contacto(contacto):
        contacto = contacto or {}
        nombre = str(contacto.get("con_nombre") or "").strip()
        puesto = str(contacto.get("con_puesto") or "").strip()
        return f"{nombre} — {puesto}" if nombre and puesto else (nombre or "Contacto sin nombre")

    def cargar_encargado(nombre=None):
        contacto = contactos_por_nombre.get(str(nombre or var_encargado_sucursal.get() or "").strip())
        seleccion_catalogo["id_contacto"] = _id_contacto(contacto) if contacto else None
        if contacto:
            var_contacto.set(str(contacto.get("con_nombre") or "").strip())
            var_telefono.set(str(contacto.get("con_telefono") or "").strip())
            var_correo.set(str(contacto.get("con_correo") or "").strip())

    def cargar_contactos(nombre=None, id_contacto_preferido=None):
        sucursal = sucursales_por_nombre.get(str(nombre or var_sucursal.get() or "").strip())
        contactos_por_nombre.clear()
        seleccion_catalogo["id_sucursal"] = _id_sucursal(sucursal) if sucursal else None
        seleccion_catalogo["id_contacto"] = None
        if sucursal:
            # La dirección visible del levantamiento es la fiscal del cliente.
            for contacto in obtener_contactos_por_sucursal(_id_sucursal(sucursal)) or []:
                contactos_por_nombre[_nombre_contacto(contacto)] = contacto
        opciones = list(contactos_por_nombre) or ["Sin encargados registrados"]
        if combo_encargado["widget"] is not None:
            combo_encargado["widget"].configure(values=opciones)
        elegido = None
        if id_contacto_preferido:
            for etiqueta, contacto in contactos_por_nombre.items():
                if str(_id_contacto(contacto)) == str(id_contacto_preferido):
                    elegido = etiqueta
                    break
        if not elegido and contactos_por_nombre:
            elegido = next(iter(contactos_por_nombre))
        var_encargado_sucursal.set(elegido or opciones[0])
        if elegido:
            cargar_encargado(elegido)

    def cargar_sucursales(id_cliente, id_sucursal_preferida=None, id_contacto_preferido=None):
        seleccion_catalogo["id_cliente"] = id_cliente
        sucursales_por_nombre.clear()
        for sucursal in obtener_sucursales_por_cliente(id_cliente) or []:
            sucursales_por_nombre[_nombre_sucursal(sucursal)] = sucursal
        opciones = list(sucursales_por_nombre) or ["Sin sucursales registradas"]
        if combo_sucursal["widget"] is not None:
            combo_sucursal["widget"].configure(values=opciones)
        elegido = None
        if id_sucursal_preferida:
            for etiqueta, sucursal in sucursales_por_nombre.items():
                if str(_id_sucursal(sucursal)) == str(id_sucursal_preferida):
                    elegido = etiqueta
                    break
        if not elegido and sucursales_por_nombre:
            elegido = next(iter(sucursales_por_nombre))
        var_sucursal.set(elegido or opciones[0])
        cargar_contactos(var_sucursal.get(), id_contacto_preferido)

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=7, pady=5)
    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_rowconfigure(1, weight=0)
    contenedor.grid_columnconfigure(0, weight=1)

    card = ctk.CTkScrollableFrame(contenedor, width=1280, height=520, fg_color=WHITE, corner_radius=18)
    card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
    form = ctk.CTkFrame(card, fg_color="transparent")
    form.pack(fill="x", expand=True, padx=12, pady=(9, 4))
    for col in range(5):
        form.grid_columnconfigure(col, weight=1, uniform="cols")

    def validar_preview():
        try:
            estado = "normal" if formulario_completo() else "disabled"
            if btn_preview is not None:
                btn_preview.configure(state=estado)
            if btn_guardar is not None:
                btn_guardar.configure(state=estado)
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    def seccion(texto, fila):
        ctk.CTkLabel(form, text=texto, font=SECTION_FONT, text_color=TEXT_PRIMARY).grid(row=fila, column=0, columnspan=5, sticky="w", pady=(6, 3))

    def celda(fila, col, colspan=1):
        frame = ctk.CTkFrame(form, fg_color="transparent")
        frame.grid(row=fila, column=col, columnspan=colspan, sticky="ew", padx=2, pady=(0, 3))
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def label(parent_, texto):
        ctk.CTkLabel(parent_, text=texto, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 1))

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
        o = NativeComboBox(c, variable=var, values=opciones, height=OPTION_H, corner_radius=8, font=SMALL_FONT)
        o.pack(fill="x")
        if required:
            campos_validables.append(var)
            var.trace_add("write", lambda *_: validar_preview())
        return o

    def cliente_selector(texto, fila, col, colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        nombres = sorted(clientes_por_nombre.keys())
        o = NativeComboBox(
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

    def catalogo_selector(texto, var, fila, col, tipo="sucursal", colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        opciones = ["Sin sucursales registradas"] if tipo == "sucursal" else ["Sin encargados registrados"]
        command = cargar_contactos if tipo == "sucursal" else cargar_encargado
        o = NativeComboBox(c, variable=var, values=opciones, height=OPTION_H, corner_radius=8, font=SMALL_FONT, command=command)
        o.pack(fill="x")
        if tipo == "sucursal":
            combo_sucursal["widget"] = o
        else:
            combo_encargado["widget"] = o
        return o

    def textbox(texto, fila, col, colspan=5, height=70):
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
        var_encargado_sucursal.set(datos_aco.get("contacto", ""))
        cliente_db = clientes_por_nombre.get(str(var_cliente.get() or "").strip())
        var_direccion.set(construir_direccion_cliente(cliente_db) if cliente_db else datos_aco.get("direccion", ""))
        cargar_sucursales(datos_aco.get("id_cliente"), datos_aco.get("id_sucursal"), datos_aco.get("id_contacto"))
        bloquear_autollenados()
        validar_preview()

    def cargar_cliente(nombre=None):
        """Autollena datos generales desde db_clientes cuando el flujo no tiene ACO."""
        nombre_cliente = str(nombre or var_cliente_selector.get() or "").strip()
        cliente_db = clientes_por_nombre.get(nombre_cliente)
        if not cliente_db:
            return
        var_cliente.set(nombre_cliente)
        var_contacto.set("")
        var_encargado_sucursal.set("")
        var_direccion.set(construir_direccion_cliente(cliente_db))
        cargar_sucursales(_id_cliente(cliente_db))
        validar_preview()

    seccion("Datos generales", 0)
    entry("Folio OBC", var_folio, 1, 0, "Automático", state="disabled", required=False)

    if aco:
        entry("Cliente", var_cliente, 1, 1, "Autollenado desde ACO", lock=True)
        entry("Dirección Fiscal", var_direccion, 1, 2, "Dirección fiscal del cliente", lock=True, colspan=3)
        catalogo_selector("Sucursal", var_sucursal, 2, 0, tipo="sucursal")
        catalogo_selector("Encargado de sucursal", var_encargado_sucursal, 2, 1, tipo="contacto", colspan=2)
        entry("Teléfono", var_telefono, 2, 3, "Autollenado desde encargado", state="disabled", required=False)
        entry("Correo", var_correo, 2, 4, "Autollenado desde encargado", state="disabled", required=False)
        cargar_sucursales(datos_aco.get("id_cliente"), datos_aco.get("id_sucursal"), datos_aco.get("id_contacto"))
        foco_inicial = None
    else:
        cliente_selector("Cliente", 1, 1)
        entry("Dirección Fiscal", var_direccion, 1, 2, "Dirección fiscal del cliente", lock=True, colspan=3)
        catalogo_selector("Sucursal", var_sucursal, 2, 0, tipo="sucursal")
        catalogo_selector("Encargado de sucursal", var_encargado_sucursal, 2, 1, tipo="contacto", colspan=2)
        entry("Teléfono", var_telefono, 2, 3, "Autollenado desde encargado", state="disabled", required=False)
        entry("Correo", var_correo, 2, 4, "Autollenado desde encargado", state="disabled", required=False)
        foco_inicial = None
        if clientes_por_nombre:
            cargar_cliente(var_cliente_selector.get())

    option("Supervisor", var_supervisor, supervisores_disponibles or ["Sin usuarios tipo 2 o 3 registrados"], 3, 0, colspan=2)
    option("Encargado de Proyecto", var_responsable, encargados_proyecto_disponibles or ["Sin usuarios tipo 3 o 4 registrados"], 3, 2, colspan=2)
    option("Técnico", var_tecnico, tecnicos_disponibles or ["Sin operadores tipo 4 registrados"], 3, 4)

    seccion("Recursos proyectados", 4)
    entry("¿Cuántos días de trabajo se proyectan?", var_dias_trabajo, 5, 0, "Ej. 5", colspan=1)
    entry("¿Cuántas personas se consideran?", var_personas_considerar, 5, 1, "Ej. 4", colspan=1)

    # EPP común para Obra Civil. Se conserva dentro de obc_ejecucion_json para evitar cambios de esquema.
    CATALOGO_EPP = [
        "Casco de seguridad", "Casco dieléctrico", "Lentes de seguridad", "Careta facial",
        "Guantes de protección mecánica", "Guantes de carnaza", "Guantes dieléctricos", "Guantes de polietileno",
        "Calzado de seguridad con casquillo", "Calzado dieléctrico", "Chaleco reflejante / alta visibilidad",
        "Arnés de cuerpo completo", "Línea de vida", "Eslinga con absorbedor de impacto", "Botas de seguridad",
        "Eslinga de posicionamiento", "Barbiquejo", "Protección auditiva", "Respirador / mascarilla",
        "Ropa de protección contra arco eléctrico", "Rodilleras", "Otro / especificar"
    ]
    epp_panel = celda(6, 0, 5)
    epp_panel.grid_columnconfigure(0, weight=2)
    epp_panel.grid_columnconfigure(1, weight=0)
    epp_panel.grid_columnconfigure(2, weight=3)
    epp_panel.grid_columnconfigure(3, weight=0)
    ctk.CTkLabel(epp_panel, text="🦺 Equipo de Protección Personal (EPP)", font=SECTION_FONT).grid(row=0, column=0, columnspan=4, sticky="w", padx=3, pady=(2,3))
    ctk.CTkLabel(epp_panel, text="¿Se requiere EPP?", font=LABEL_FONT).grid(row=1, column=0, sticky="w", padx=3)
    combo_epp_req = NativeComboBox(epp_panel, variable=var_requiere_epp, values=["No", "Sí"], width=100, height=OPTION_H)
    combo_epp_req.grid(row=1, column=1, sticky="w", padx=3)
    epp_rows = ctk.CTkFrame(epp_panel, fg_color="transparent")
    epp_rows.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(3,0))
    for c,w in enumerate((2,0,3,0)): epp_rows.grid_columnconfigure(c, weight=w)
    for c,t in enumerate(("EPP requerido","Cantidad","Especificación / observaciones","Acción")):
        ctk.CTkLabel(epp_rows, text=t, font=SMALL_FONT).grid(row=0, column=c, sticky="w", padx=3)

    def agregar_epp_obra(datos=None):
        datos = dict(datos or {})
        fila_e = 1 + len(epp_items)
        ve = ctk.StringVar(value=str(datos.get("epp") or "Casco de seguridad"))
        vc = ctk.StringVar(value=str(datos.get("cantidad") or "1"))
        vo = ctk.StringVar(value=str(datos.get("observaciones") or ""))
        opciones = list(CATALOGO_EPP)
        if ve.get() not in opciones: opciones.append(ve.get())
        ce = NativeComboBox(epp_rows, variable=ve, values=opciones, width=250, height=OPTION_H)
        ce.grid(row=fila_e,column=0,sticky="ew",padx=3,pady=2)
        ec = ctk.CTkEntry(epp_rows,textvariable=vc,width=80,height=ENTRY_H,corner_radius=0)
        ec.grid(row=fila_e,column=1,sticky="w",padx=3,pady=2)
        eo = ctk.CTkEntry(epp_rows,textvariable=vo,height=ENTRY_H,corner_radius=0,placeholder_text="Talla, clase, norma o detalle especial")
        eo.grid(row=fila_e,column=2,sticky="ew",padx=3,pady=2)
        item={"epp":ve,"cantidad":vc,"observaciones":vo,"widgets":[ce,ec,eo]}
        def borrar():
            for w in item["widgets"]:
                try:w.destroy()
                except Exception:pass
            epp_items[:] = [x for x in epp_items if x is not item]
            try:
                validar_preview()
            except (NameError, UnboundLocalError):
                pass
        b=ctk.CTkButton(epp_rows,text="Eliminar",width=78,height=ENTRY_H,fg_color="#DC2626",command=borrar)
        b.grid(row=fila_e,column=3,sticky="ew",padx=3,pady=2); item["widgets"].append(b); epp_items.append(item)

    btn_epp_add=ctk.CTkButton(epp_rows,text="➕ Agregar EPP",height=30,fg_color=PRIMARY,command=lambda:agregar_epp_obra(None))
    btn_epp_add.grid(row=999,column=0,columnspan=2,sticky="w",padx=3,pady=(3,4))
    def obtener_epp_obra():
        if var_requiere_epp.get() != "Sí": return []
        return [{"epp":i["epp"].get().strip(),"cantidad":i["cantidad"].get().strip() or "1","observaciones":i["observaciones"].get().strip()} for i in epp_items if i["epp"].get().strip()]
    def vis_epp_obra(*_):
        if var_requiere_epp.get()=="Sí":
            epp_rows.grid()
            if not epp_items: agregar_epp_obra(None)
        else: epp_rows.grid_remove()
        try:
            validar_preview()
        except (NameError, UnboundLocalError):
            pass
    var_requiere_epp.trace_add("write",vis_epp_obra); vis_epp_obra()

    entry("Fecha", var_fecha, 7, 0, "YYYY-MM-DD", date=True)
    entry("Tipo de giro", var_tipo_giro, 7, 1, "Ej. Bancario, retail, oficina")
    entry("Nombre del proyecto", var_nombre_proyecto, 7, 2, "Proyecto ejecutivo", colspan=3)

    seccion("Planeación inicial", 8)
    option("¿Se cuenta con superficie?", var_superficie, SI_NO, 9, 0)
    option("¿La superficie es adecuada?", var_superficie_ok, SI_NO, 9, 1)
    option("¿Planos y diseño arquitectónico?", var_planos_arq, SI_NO, 9, 2)
    option("¿Requiere maquinaria?", var_maquinaria, SI_NO, 9, 3)
    option("¿Se cuenta con permisos?", var_permisos, SI_NO, 9, 4)
    txt_observaciones_iniciales = textbox("Observaciones iniciales", 11, 0, 5)

    seccion("Ejecución", 12)
    fila = 13
    col = 0
    for nombre, var in ejecucion_vars.items():
        option(nombre, var, ESTADOS, fila, col)
        col += 1
        if col == 4:
            col = 0
            fila += 1

    seccion("Acabados", 19)
    option("¿Planos de detalles y acabados?", var_planos_acabados, SI_NO, 20, 0)
    option("Generación de planos", var_generacion_planos, ["Sí", "No", "No aplica"], 20, 1)
    option("Etapa de acabados", var_etapa_acabados, ESTADOS, 20, 2)
    option("Obra blanca", var_obra_blanca, ESTADOS, 20, 3)

    seccion("Conceptos de obra requeridos", 21)
    panel_conceptos = celda(22, 0, 5)
    # Prioriza el concepto: ~25% más espacio que el layout anterior.
    panel_conceptos.grid_columnconfigure(0, weight=2)
    panel_conceptos.grid_columnconfigure(1, weight=8)
    panel_conceptos.grid_columnconfigure(2, weight=1, minsize=68)
    panel_conceptos.grid_columnconfigure(3, weight=1, minsize=72)
    panel_conceptos.grid_columnconfigure(4, weight=1, minsize=76)
    for col, encabezado in enumerate(("Tipo", "Partida / concepto", "Unidad", "Cantidad", "Acción")):
        ctk.CTkLabel(panel_conceptos, text=encabezado, font=("Montserrat", 12, "bold")).grid(row=0, column=col, sticky="w", padx=3)

    tipos_concepto_obra = obtener_tipos_concepto_obra(catalogo_conceptos_obra)

    def _etiqueta_concepto_obra(item):
        partida = str(item.get("obra_partida") or "").strip()
        concepto = " ".join(str(item.get("obra_concepto") or "").split())
        # No truncar: el usuario debe poder identificar el concepto completo.
        return f"{partida} — {concepto}" if concepto else partida

    def agregar_concepto_obra():
        fila_concepto = 1 + len(conceptos_obra_items)
        tipo_inicial = tipos_concepto_obra[0] if tipos_concepto_obra else "Sin catálogo"
        conceptos_tipo = filtrar_conceptos_por_tipo(tipo_inicial, catalogo_conceptos_obra)
        etiquetas = [_etiqueta_concepto_obra(item) for item in conceptos_tipo] or ["Sin conceptos disponibles"]

        vtipo = ctk.StringVar(value=tipo_inicial)
        vconcepto = ctk.StringVar(value=etiquetas[0])
        vunidad = ctk.StringVar(value=str((conceptos_tipo[0].get("obra_unidad") if conceptos_tipo else "") or ""))
        vcantidad = ctk.StringVar(value="1")
        vcantidad.trace_add("write", lambda *_: validar_preview())

        otipo = NativeComboBox(panel_conceptos, variable=vtipo, values=tipos_concepto_obra or ["Sin catálogo"], height=30)
        otipo.grid(row=fila_concepto, column=0, sticky="ew", padx=3, pady=2)
        oconcepto = NativeComboBox(panel_conceptos, variable=vconcepto, values=etiquetas, height=30)
        oconcepto.grid(row=fila_concepto, column=1, sticky="ew", padx=3, pady=2)
        eunidad = ctk.CTkEntry(panel_conceptos, textvariable=vunidad, width=68, height=30, state="disabled")
        eunidad.grid(row=fila_concepto, column=2, sticky="ew", padx=3, pady=2)
        ecantidad = ctk.CTkEntry(panel_conceptos, textvariable=vcantidad, width=72, height=30, placeholder_text="Ej. 12.5")
        ecantidad.grid(row=fila_concepto, column=3, sticky="ew", padx=3, pady=2)

        item_concepto = {
            "tipo": vtipo, "concepto_label": vconcepto, "unidad": vunidad, "cantidad": vcantidad,
            "conceptos_tipo": conceptos_tipo, "registro": conceptos_tipo[0] if conceptos_tipo else {},
            "widgets": [otipo, oconcepto, eunidad, ecantidad],
        }

        def seleccionar_concepto(_valor=None):
            etiqueta = vconcepto.get()
            registro = next((x for x in item_concepto.get("conceptos_tipo", []) if _etiqueta_concepto_obra(x) == etiqueta), {})
            item_concepto["registro"] = registro
            vunidad.set(str(registro.get("obra_unidad") or ""))
            validar_preview()

        def cambiar_tipo(valor):
            nuevos = filtrar_conceptos_por_tipo(valor, catalogo_conceptos_obra)
            item_concepto["conceptos_tipo"] = nuevos
            nuevas_etiquetas = [_etiqueta_concepto_obra(x) for x in nuevos] or ["Sin conceptos disponibles"]
            oconcepto.configure(values=nuevas_etiquetas)
            vconcepto.set(nuevas_etiquetas[0])
            seleccionar_concepto()

        otipo.configure(command=cambiar_tipo)
        oconcepto.configure(command=seleccionar_concepto)

        def eliminar_concepto():
            for widget in item_concepto.get("widgets", []):
                try:
                    widget.destroy()
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)
            conceptos_obra_items[:] = [x for x in conceptos_obra_items if x is not item_concepto]
            validar_preview()

        btn = ctk.CTkButton(panel_conceptos, text="Eliminar", width=76, height=30, fg_color="#DC2626", hover_color="#B91C1C", command=eliminar_concepto)
        btn.grid(row=fila_concepto, column=4, sticky="ew", padx=3, pady=2)
        item_concepto["widgets"].append(btn)
        conceptos_obra_items.append(item_concepto)

    def obtener_conceptos_obra_seleccionados():
        seleccion = []
        for item in conceptos_obra_items:
            registro = item.get("registro") or {}
            cantidad = item["cantidad"].get().strip()
            if not registro or not cantidad:
                continue
            seleccion.append({
                "id_obra_concepto": registro.get("id_obra_concepto"),
                "catalogo_ref": registro.get("obra_catalogo_ref"),
                "tipo": registro.get("obra_tipo"),
                "partida": registro.get("obra_partida"),
                "unidad": registro.get("obra_unidad"),
                "concepto": registro.get("obra_concepto"),
                "precio_unitario_referencia": registro.get("obra_precio_unitario"),
                "cantidad": cantidad,
            })
        return seleccion

    if catalogo_conceptos_obra:
        agregar_concepto_obra()
    else:
        ctk.CTkLabel(
            panel_conceptos,
            text="Catálogo no disponible. Ejecuta la migración db_obra_conceptos en Supabase.",
            font=SMALL_FONT, text_color="#B45309"
        ).grid(row=1, column=0, columnspan=5, sticky="w", padx=3, pady=4)

    ctk.CTkButton(
        panel_conceptos, text="+ Agregar concepto", width=180, height=30,
        fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_concepto_obra,
        state="normal" if catalogo_conceptos_obra else "disabled"
    ).grid(row=99, column=0, columnspan=2, sticky="w", padx=3, pady=(4, 2))

    seccion("Materiales misceláneos y consumibles", 23)
    panel_misc = celda(24, 0, 5)
    panel_misc.grid_columnconfigure(0, weight=2)
    panel_misc.grid_columnconfigure(1, weight=1)
    panel_misc.grid_columnconfigure(2, weight=1)
    panel_misc.grid_columnconfigure(3, weight=1)
    panel_misc.grid_columnconfigure(4, weight=3)
    panel_misc.grid_columnconfigure(5, weight=1)
    ctk.CTkLabel(panel_misc, text="Material", font=("Montserrat", 12, "bold")).grid(row=0, column=0, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="¿Se requiere?", font=("Montserrat", 12, "bold")).grid(row=0, column=1, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="Cantidad", font=("Montserrat", 12, "bold")).grid(row=0, column=2, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="Unidad", font=("Montserrat", 12, "bold")).grid(row=0, column=3, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="Especificación / medida", font=("Montserrat", 12, "bold")).grid(row=0, column=4, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="Acción", font=("Montserrat", 12, "bold")).grid(row=0, column=5, sticky="w", padx=3)

    def agregar_material_misc_obra(material_catalogo=None):
        material_catalogo = material_catalogo or {}
        if isinstance(material_catalogo, str):
            material_catalogo = {"nombre": material_catalogo}
        nombre = material_catalogo.get("nombre", "")
        categoria = material_catalogo.get("categoria", "Otro")
        unidad_default = material_catalogo.get("unidad", "Pieza(s)")
        especificacion_sugerida = material_catalogo.get("especificacion_sugerida", "")

        fila_misc = 1 + len(materiales_miscelaneos_items)
        vm = ctk.StringVar(value=nombre)
        vcat = ctk.StringVar(value=categoria)
        vr = ctk.StringVar(value="No")
        vc = ctk.StringVar()
        vu = ctk.StringVar(value=unidad_default if unidad_default in UNIDADES_MATERIAL else "Pieza(s)")
        ve = ctk.StringVar()
        em = ctk.CTkEntry(panel_misc, textvariable=vm, height=30)
        em.grid(row=fila_misc, column=0, sticky="ew", padx=3, pady=2)
        if nombre:
            em.configure(state="readonly")
        ec = ctk.CTkEntry(panel_misc, textvariable=vc, width=90, height=30, placeholder_text="Ej. 20", state="disabled")
        ec.grid(row=fila_misc, column=2, sticky="w", padx=3, pady=2)
        ou = NativeComboBox(panel_misc, variable=vu, values=UNIDADES_MATERIAL, width=120, height=30, state="disabled")
        ou.grid(row=fila_misc, column=3, sticky="w", padx=3, pady=2)
        ee = ctk.CTkEntry(
            panel_misc, textvariable=ve, height=30,
            placeholder_text=especificacion_sugerida or "Medida, material, color o presentación",
            state="disabled"
        )
        ee.grid(row=fila_misc, column=4, sticky="ew", padx=3, pady=2)
        def toggle(_=None):
            estado = "normal" if vr.get() == "Sí" else "disabled"
            ec.configure(state=estado); ou.configure(state=estado); ee.configure(state=estado)
            if estado == "disabled":
                vc.set(""); ve.set("")
            validar_preview()
        om = NativeComboBox(panel_misc, variable=vr, values=["No", "Sí"], width=100, height=30, command=toggle)
        om.grid(row=fila_misc, column=1, sticky="w", padx=3, pady=2)
        item_material={
            "material": vm, "categoria": vcat, "requerido": vr,
            "cantidad": vc, "unidad": vu, "especificacion": ve,
            "widgets":[em,ec,ou,ee,om]
        }
        def eliminar_material():
            for widget in item_material.get("widgets", []):
                try: widget.destroy()
                except Exception:
                    logger.debug("Excepción recuperable controlada.", exc_info=True)
            materiales_miscelaneos_items[:] = [x for x in materiales_miscelaneos_items if x is not item_material]
        btn=ctk.CTkButton(panel_misc,text="Eliminar",width=82,height=30,fg_color="#DC2626",hover_color="#B91C1C",command=eliminar_material)
        btn.grid(row=fila_misc,column=5,sticky="ew",padx=3,pady=2)
        item_material["widgets"].append(btn)
        materiales_miscelaneos_items.append(item_material)

    # Una sola fila inicial; el usuario agrega o elimina las necesarias.
    agregar_material_misc_obra(None)

    ctk.CTkButton(panel_misc, text="+ Agregar otro material", width=180, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=lambda: agregar_material_misc_obra(None)).grid(row=99, column=0, columnspan=2, sticky="w", padx=3, pady=(4, 2))

    def obtener_materiales_misc_obra():
        return [{
            "material": i["material"].get().strip(),
            "categoria": i.get("categoria").get().strip() if i.get("categoria") else "Otro",
            "cantidad": i["cantidad"].get().strip(),
            "unidad": i["unidad"].get().strip(), "especificacion": i["especificacion"].get().strip()
        } for i in materiales_miscelaneos_items if i["requerido"].get() == "Sí" and i["material"].get().strip()]

    # Canalización, cableado y materiales. Se persiste dentro de obc_ejecucion_json
    # para conservar compatibilidad con el esquema actual de Supabase.
    seccion("Canalización, cableado y materiales", 25)
    panel_canalizacion = celda(26, 0, 5)
    for col, peso in enumerate((2, 4, 3, 2, 2, 1)):
        panel_canalizacion.grid_columnconfigure(col, weight=peso)
    ctk.CTkLabel(
        panel_canalizacion,
        text="Agrega todas las partidas necesarias. Puedes registrar varios tipos, medidas y cantidades.",
        font=SMALL_FONT, text_color=TEXT_SECONDARY,
    ).grid(row=0, column=0, columnspan=6, sticky="w", padx=3, pady=(0, 6))
    ctk.CTkLabel(panel_canalizacion, text="¿Se requiere?", font=("Montserrat", 11, "bold")).grid(row=1, column=0, sticky="w", padx=3)
    combo_requiere_canalizacion = NativeComboBox(panel_canalizacion, variable=var_requiere_canalizacion, values=["Sí", "No"], width=120, height=31)
    combo_requiere_canalizacion.grid(row=2, column=0, sticky="w", padx=3, pady=(0, 5))
    for col, encabezado in enumerate(("Categoría", "Tipo", "Tamaño / calibre / especificación", "Cantidad", "Unidad", "Acción")):
        ctk.CTkLabel(panel_canalizacion, text=encabezado, font=("Montserrat", 11, "bold"), text_color=TEXT_PRIMARY).grid(row=3, column=col, sticky="w", padx=3, pady=(0, 2))

    categorias_canalizacion = ["Tubo", "Cople", "Registro", "Conectores", "Abrazadera", "Tapas", "Codos", "Canaleta", "Cable"]

    def catalogo_tipos_canalizacion(categoria):
        if categoria == "Tubo": return list(TIPOS_TUBOS)
        if categoria == "Cople": return list(TIPOS_COPLES)
        if categoria == "Registro": return list(TIPOS_REGISTROS)
        if categoria == "Conector": return list(TIPOS_CONECTORES)
        if categoria == "Abrazadera": return list(TIPOS_ABRAZADERAS)
        if categoria in ("Conector", "Conectores"): return list(TIPOS_CONECTORES)
        if categoria == "Codos": return ["45°", "90°", "Interior", "Exterior", "Plano"]
        if categoria == "Tapas": return ["Ciega", "Final", "Unión", "Para contacto", "Para datos"]
        if categoria in ("Canalización", "Canaleta"): return list(TIPOS_CANALIZACION)
        if categoria == "Cable": return list(TIPOS_CABLE_DATOS_CONTROL)
        return ["Otro"]

    def catalogo_especificacion_canalizacion(categoria, tipo=""):
        return especificaciones_por_categoria(categoria, tipo)

    def obtener_canalizacion_materiales_obra():
        if var_requiere_canalizacion.get() == "No":
            return []
        filas = []
        for item in canalizacion_materiales_items:
            categoria = item["categoria"].get().strip()
            tipo = item["tipo"].get().strip()
            cantidad = item["cantidad"].get().strip()
            if not (categoria or tipo or cantidad):
                continue
            filas.append({
                "categoria": categoria,
                "tipo": tipo,
                "tamano_calibre_especificacion": item["especificacion"].get().strip(),
                "cantidad": cantidad,
                "unidad": item["unidad"].get().strip(),
            })
        return filas

    def canalizacion_obra_completa():
        if var_requiere_canalizacion.get() == "No":
            return True
        filas = obtener_canalizacion_materiales_obra()
        if not filas:
            return False
        for fila in filas:
            if not (fila.get("categoria") and fila.get("tipo") and fila.get("cantidad") and fila.get("unidad")):
                return False
            if fila.get("categoria") == "Tubo" and not fila.get("tamano_calibre_especificacion"):
                return False
            cantidad = str(fila.get("cantidad") or "").replace(",", ".")
            try:
                if float(cantidad) <= 0:
                    return False
            except (TypeError, ValueError):
                return False
        return True

    def agregar_partida_canalizacion_obra(categoria_inicial="Tubo"):
        fila = 4 + len(canalizacion_materiales_items)
        vcategoria = ctk.StringVar(value=categoria_inicial)
        vtipo = ctk.StringVar()
        vespecificacion = ctk.StringVar()
        vcantidad = ctk.StringVar()
        vunidad = ctk.StringVar(value="Metro(s)" if categoria_inicial in ("Tubo", "Canalización", "Canaleta", "Cable") else "Pieza(s)")
        ocategoria = NativeComboBox(panel_canalizacion, variable=vcategoria, values=categorias_canalizacion, width=155, height=31)
        otipo = NativeComboBox(panel_canalizacion, variable=vtipo, values=[], width=300, height=31)
        oespecificacion = NativeComboBox(panel_canalizacion, variable=vespecificacion, values=[], width=225, height=31)
        ecantidad = ctk.CTkEntry(panel_canalizacion, textvariable=vcantidad, width=120, height=31, placeholder_text="Ej. 20")
        ounidad = NativeComboBox(panel_canalizacion, variable=vunidad, values=["Metro(s)", "Pieza(s)", "Caja(s)", "Rollo(s)", "Juego(s)"], width=125, height=31)
        widgets = [ocategoria, otipo, oespecificacion, ecantidad, ounidad]
        for col, widget in enumerate(widgets):
            widget.grid(row=fila, column=col, sticky="ew", padx=3, pady=2)
        item = {"categoria": vcategoria, "tipo": vtipo, "especificacion": vespecificacion, "cantidad": vcantidad, "unidad": vunidad, "widgets": widgets}

        def actualizar_catalogos(_=None):
            categoria = vcategoria.get().strip()
            tipos = catalogo_tipos_canalizacion(categoria)
            especificaciones = catalogo_especificacion_canalizacion(categoria, vtipo.get())
            otipo.configure(values=tipos)
            oespecificacion.configure(values=especificaciones)
            if vtipo.get() not in tipos:
                vtipo.set(tipos[0] if tipos else "")
            if vespecificacion.get() not in especificaciones:
                vespecificacion.set(especificaciones[0] if especificaciones else "")
            if categoria in ("Tubo", "Canalización", "Canaleta", "Cable") and not vunidad.get():
                vunidad.set("Metro(s)")
            elif categoria not in ("Tubo", "Canalización", "Canaleta", "Cable") and vunidad.get() == "Metro(s)":
                vunidad.set("Pieza(s)")
            validar_preview()

        ocategoria.configure(command=actualizar_catalogos)
        vtipo.trace_add("write", lambda *_: actualizar_catalogos())
        actualizar_catalogos()
        vcantidad.trace_add("write", lambda *_: validar_preview())

        def eliminar_partida():
            for widget in item.get("widgets", []):
                try: widget.destroy()
                except Exception: logger.debug("Excepción recuperable controlada.", exc_info=True)
            try: btn_eliminar.destroy()
            except Exception: logger.debug("Excepción recuperable controlada.", exc_info=True)
            canalizacion_materiales_items[:] = [x for x in canalizacion_materiales_items if x is not item]
            validar_preview()

        btn_eliminar = ctk.CTkButton(panel_canalizacion, text="Eliminar", width=78, height=31, fg_color="#DC2626", hover_color="#B91C1C", command=eliminar_partida)
        btn_eliminar.grid(row=fila, column=5, sticky="ew", padx=3, pady=2)
        item["widgets"].append(btn_eliminar)
        canalizacion_materiales_items.append(item)
        validar_preview()

    def actualizar_requiere_canalizacion_obra(*_):
        habilitado = var_requiere_canalizacion.get() == "Sí"
        estado = "normal" if habilitado else "disabled"
        for item in canalizacion_materiales_items:
            for widget in item.get("widgets", []):
                try: widget.configure(state=estado)
                except Exception: pass
        validar_preview()

    var_requiere_canalizacion.trace_add("write", actualizar_requiere_canalizacion_obra)
    ctk.CTkButton(panel_canalizacion, text="➕ Agregar partida", height=32, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_partida_canalizacion_obra).grid(row=1000, column=0, columnspan=2, sticky="w", padx=3, pady=(4, 2))
    agregar_partida_canalizacion_obra("Tubo")

    seccion("Acceso, alturas y riesgos", 27)
    panel_alturas = celda(28, 0, 5)
    panel_alturas.grid_columnconfigure((0, 1, 2, 3), weight=1)
    campos_alturas = [
        ("¿Se trabajará en Alturas?", var_trabajo_alturas, ["Sí", "No"]),
        ("Tipo de Sistema de Acceso Temporal", var_sistema_acceso, ["Escalera", "Andamio", "Plataforma"]),
        ("Altura", var_altura_trabajo, None),
        ("Riesgo", var_riesgo_trabajo, ["Bajo", "Medio", "Alto", "Crítico"]),
    ]
    widgets_alturas = []
    for idx, (texto_alt, variable_alt, opciones_alt) in enumerate(campos_alturas):
        caja_alt = ctk.CTkFrame(panel_alturas, fg_color="transparent")
        caja_alt.grid(row=0, column=idx, sticky="ew", padx=4)
        ctk.CTkLabel(caja_alt, text=texto_alt, font=LABEL_FONT, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        if opciones_alt is None:
            w_alt = ctk.CTkEntry(caja_alt, textvariable=variable_alt, height=30, corner_radius=0, font=SMALL_FONT, placeholder_text="Ej. 4 metros")
        else:
            w_alt = NativeComboBox(caja_alt, variable=variable_alt, values=opciones_alt, height=30, font=SMALL_FONT)
        w_alt.pack(fill="x")
        widgets_alturas.append(w_alt)
    def actualizar_alturas_obra(*_):
        activo = var_trabajo_alturas.get() == "Sí"
        for w_alt in widgets_alturas[1:]:
            try: w_alt.configure(state="normal" if activo else "disabled")
            except Exception: pass
        if not activo:
            var_sistema_acceso.set("Escalera"); var_altura_trabajo.set(""); var_riesgo_trabajo.set("Bajo")
        validar_preview()
    var_trabajo_alturas.trace_add("write", actualizar_alturas_obra)
    actualizar_alturas_obra()

    seccion("Evidencia fotográfica", 29)
    panel_evidencias = celda(30, 0, 5)
    fila_evidencias = ctk.CTkFrame(panel_evidencias, fg_color="#F8FAFC", corner_radius=10)
    fila_evidencias.pack(fill="x")
    ctk.CTkLabel(fila_evidencias, text="¿Deseas agregar evidencia fotográfica?", font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(side="left", padx=8, pady=7)
    cmb_evidencias = NativeComboBox(fila_evidencias, variable=var_desea_evidencias, values=["No", "Sí"], width=110, height=30)
    cmb_evidencias.pack(side="left", padx=5, pady=7)
    lbl_evidencias = ctk.CTkLabel(fila_evidencias, text="No se requieren fotografías", font=SMALL_FONT, text_color=TEXT_SECONDARY)
    lbl_evidencias.pack(side="right", padx=8)

    def actualizar_evidencias(*_):
        desea = var_desea_evidencias.get() == "Sí"
        btn_agregar_evidencia.configure(state="normal" if desea else "disabled")
        btn_eliminar_evidencia.configure(state="normal" if desea and evidencias else "disabled")
        if not desea:
            evidencias.clear()
            lbl_evidencias.configure(text="No se requieren fotografías")
        else:
            lbl_evidencias.configure(text=f"{len(evidencias)} fotografía(s) seleccionada(s)" if evidencias else "Pendiente de cargar fotografías")
        validar_preview()

    def agregar_evidencia():
        rutas = filedialog.askopenfilenames(
            title="Agregar evidencia fotográfica",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp"), ("Todos", "*.*")],
        )
        for ruta in rutas:
            if ruta and ruta not in evidencias:
                evidencias.append(ruta)
        actualizar_evidencias()

    def eliminar_ultima_evidencia():
        if evidencias:
            evidencias.pop()
        actualizar_evidencias()

    btn_agregar_evidencia = ctk.CTkButton(fila_evidencias, text="+ Agregar fotos", width=145, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_evidencia, state="disabled")
    btn_agregar_evidencia.pack(side="left", padx=5, pady=7)
    btn_eliminar_evidencia = ctk.CTkButton(fila_evidencias, text="Eliminar última", width=135, height=30, fg_color="#DC2626", hover_color="#B91C1C", command=eliminar_ultima_evidencia, state="disabled")
    btn_eliminar_evidencia.pack(side="left", padx=5, pady=7)
    var_desea_evidencias.trace_add("write", actualizar_evidencias)

    seccion("Anotaciones tipo plano", 31)
    panel_anotacion = celda(32, 0, 5)
    fila_anotacion = ctk.CTkFrame(panel_anotacion, fg_color="#F8FAFC", corner_radius=10)
    fila_anotacion.pack(fill="x")
    ctk.CTkLabel(fila_anotacion, text="¿Deseas realizar anotaciones tipo plano?", font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(side="left", padx=8, pady=7)
    cmb_anotacion = NativeComboBox(fila_anotacion, variable=var_desea_anotacion_plano, values=["No", "Sí"], width=110, height=30)
    cmb_anotacion.pack(side="left", padx=5, pady=7)
    lbl_estado_anotacion = ctk.CTkLabel(fila_anotacion, text="No se requiere anotación", font=SMALL_FONT, text_color=TEXT_SECONDARY)
    lbl_estado_anotacion.pack(side="left", padx=8)

    def abrir_editor_anotacion():
        anotacion_plano_popup(card, var_anotacion_plano_base64, on_change=actualizar_anotacion, titulo="Anotaciones tipo plano - Obra Civil")

    btn_anotacion = ctk.CTkButton(fila_anotacion, text="✎ Abrir editor", width=145, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=abrir_editor_anotacion, state="disabled")
    btn_anotacion.pack(side="left", padx=5, pady=7)

    def actualizar_anotacion(*_):
        desea = var_desea_anotacion_plano.get() == "Sí"
        btn_anotacion.configure(state="normal" if desea else "disabled")
        if not desea:
            var_anotacion_plano_base64.set("")
            lbl_estado_anotacion.configure(text="No se requiere anotación")
        else:
            lbl_estado_anotacion.configure(text="Anotación capturada" if var_anotacion_plano_base64.get().strip() else "Pendiente de capturar")
        validar_preview()
    var_desea_anotacion_plano.trace_add("write", actualizar_anotacion)

    seccion("Archivos PDF o planos", 33)
    panel_archivos = celda(34, 0, 5)
    fila_archivos = ctk.CTkFrame(panel_archivos, fg_color="#F8FAFC", corner_radius=10)
    fila_archivos.pack(fill="x")
    ctk.CTkLabel(fila_archivos, text="¿Deseas agregar archivos PDF o planos?", font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(side="left", padx=8, pady=7)
    cmb_archivos = NativeComboBox(fila_archivos, variable=var_desea_archivos_adjuntos, values=["No", "Sí"], width=110, height=30)
    cmb_archivos.pack(side="left", padx=5, pady=7)
    lbl_archivos = ctk.CTkLabel(fila_archivos, text="No se requieren archivos", font=SMALL_FONT, text_color=TEXT_SECONDARY)
    lbl_archivos.pack(side="right", padx=8)

    def total_archivos_obra():
        return len(archivos_adjuntos) + len(archivos_adjuntos_existentes)

    def actualizar_archivos(*_):
        desea = var_desea_archivos_adjuntos.get() == "Sí"
        btn_agregar_archivo.configure(state="normal" if desea else "disabled")
        btn_eliminar_archivo.configure(state="normal" if desea and archivos_adjuntos else "disabled")
        if not desea:
            archivos_adjuntos.clear(); archivos_adjuntos_existentes.clear()
            lbl_archivos.configure(text="No se requieren archivos")
        else:
            lbl_archivos.configure(text=f"{total_archivos_obra()} archivo(s) adjunto(s)" if total_archivos_obra() else "Pendiente de cargar PDF o planos")
        validar_preview()

    def agregar_archivo_obra():
        rutas = filedialog.askopenfilenames(
            title="Agregar PDF o planos",
            filetypes=[("PDF y planos", "*.pdf *.dwg *.dxf *.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")],
        )
        for ruta in rutas:
            if ruta and ruta not in archivos_adjuntos:
                archivos_adjuntos.append(ruta)
        actualizar_archivos()

    def eliminar_ultimo_archivo_obra():
        if archivos_adjuntos: archivos_adjuntos.pop()
        actualizar_archivos()

    btn_agregar_archivo = ctk.CTkButton(fila_archivos, text="+ Agregar archivos", width=155, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_archivo_obra, state="disabled")
    btn_agregar_archivo.pack(side="left", padx=5, pady=7)
    btn_eliminar_archivo = ctk.CTkButton(fila_archivos, text="Eliminar último", width=135, height=30, fg_color="#DC2626", hover_color="#B91C1C", command=eliminar_ultimo_archivo_obra, state="disabled")
    btn_eliminar_archivo.pack(side="left", padx=5, pady=7)
    var_desea_archivos_adjuntos.trace_add("write", actualizar_archivos)

    seccion("Observaciones finales", 35)
    txt_finales = textbox("Observaciones finales", 36, 0, 5, height=90)

    def _restaurar_borrador_obra():
        if not isinstance(borrador, dict):
            return
        estado = borrador.get("__obra_civil_borrador") if isinstance(borrador.get("__obra_civil_borrador"), dict) else {}
        if not estado:
            return
        mapa = {
            "folio": var_folio, "fecha": var_fecha, "aco": var_aco, "cliente": var_cliente,
            "contacto": var_contacto, "telefono": var_telefono, "correo": var_correo,
            "sucursal": var_sucursal, "encargado_sucursal": var_encargado_sucursal,
            "direccion": var_direccion, "responsable": var_responsable, "supervisor": var_supervisor,
            "tecnico": var_tecnico, "tipo_giro": var_tipo_giro, "nombre_proyecto": var_nombre_proyecto,
            "dias_trabajo": var_dias_trabajo, "personas": var_personas_considerar,
            "requiere_epp": var_requiere_epp, "superficie": var_superficie, "superficie_ok": var_superficie_ok,
            "planos_arq": var_planos_arq, "maquinaria": var_maquinaria, "permisos": var_permisos,
            "desea_anotacion": var_desea_anotacion_plano, "anotacion_base64": var_anotacion_plano_base64,
            "desea_evidencias": var_desea_evidencias, "desea_archivos": var_desea_archivos_adjuntos,
            "trabajo_alturas": var_trabajo_alturas, "sistema_acceso": var_sistema_acceso,
            "altura_trabajo": var_altura_trabajo, "riesgo": var_riesgo_trabajo,
            "requiere_canalizacion": var_requiere_canalizacion,
            "planos_acabados": var_planos_acabados, "generacion_planos": var_generacion_planos,
            "etapa_acabados": var_etapa_acabados, "obra_blanca": var_obra_blanca,
        }
        for clave, variable in mapa.items():
            if clave in estado:
                variable.set(str(estado.get(clave) or ""))
        for clave, variable in ejecucion_vars.items():
            if clave in (estado.get("ejecucion") or {}):
                variable.set(str(estado["ejecucion"].get(clave) or ""))
        try:
            txt_observaciones_iniciales.delete("1.0", "end"); txt_observaciones_iniciales.insert("1.0", str(estado.get("observaciones_iniciales") or ""))
            txt_finales.delete("1.0", "end"); txt_finales.insert("1.0", str(estado.get("observaciones_finales") or ""))
        except Exception:
            pass
        for ruta in estado.get("evidencias_locales", []) if isinstance(estado.get("evidencias_locales"), list) else []:
            if ruta and ruta not in evidencias: evidencias.append(ruta)
        for ruta in estado.get("archivos_locales", []) if isinstance(estado.get("archivos_locales"), list) else []:
            if ruta and ruta not in archivos_adjuntos: archivos_adjuntos.append(ruta)
        try:
            actualizar_alturas_obra(); actualizar_evidencias(); actualizar_anotacion(); actualizar_archivos()
        except Exception:
            pass

    _restaurar_borrador_obra()
    bloquear_autollenados()

    def formulario_completo():
        if not all(v.get().strip() for v in campos_validables):
            return False
        if var_desea_anotacion_plano.get() == "Sí" and not var_anotacion_plano_base64.get().strip():
            return False
        if var_desea_evidencias.get() == "Sí" and not evidencias:
            return False
        if var_desea_archivos_adjuntos.get() == "Sí" and total_archivos_obra() == 0:
            return False
        if var_trabajo_alturas.get() == "Sí" and not (var_sistema_acceso.get().strip() and var_altura_trabajo.get().strip() and var_riesgo_trabajo.get().strip()):
            return False
        if not canalizacion_obra_completa():
            return False
        try:
            if int(var_dias_trabajo.get().strip()) <= 0 or int(var_personas_considerar.get().strip()) <= 0:
                return False
            if var_requiere_epp.get() == "Sí":
                partidas_epp = obtener_epp_obra()
                if not partidas_epp:
                    return False
                for item_epp in partidas_epp:
                    if float(str(item_epp.get("cantidad") or "0").replace(",", ".")) <= 0:
                        return False
        except (TypeError, ValueError):
            return False
        # Si el catálogo está disponible, cada concepto visible debe ser válido y tener cantidad > 0.
        if catalogo_conceptos_obra:
            if not conceptos_obra_items:
                return False
            for item in conceptos_obra_items:
                if not (item.get("registro") or {}):
                    return False
                cantidad = item["cantidad"].get().strip().replace(",", ".")
                try:
                    if float(cantidad) <= 0:
                        return False
                except (TypeError, ValueError):
                    return False
        return True

    def datos_pdf():
        datos = {
            "Folio OBC": var_folio.get(), "Fecha": var_fecha.get(), "ACO": var_aco.get(), "Cliente": var_cliente.get(), "Contacto": var_contacto.get(),
            "Sucursal": var_sucursal.get(), "Encargado de sucursal": var_encargado_sucursal.get(), "Dirección Fiscal": var_direccion.get(), "Teléfono": var_telefono.get(), "Correo": var_correo.get(), "Encargado de Proyecto": var_responsable.get(), "Supervisor": var_supervisor.get(), "Técnico": var_tecnico.get(),
            "Días de trabajo": var_dias_trabajo.get(), "Personas a considerar": var_personas_considerar.get(),
            "Tipo de giro": var_tipo_giro.get(), "Nombre del proyecto": var_nombre_proyecto.get(), "Superficie disponible": var_superficie.get(),
            "Superficie adecuada": var_superficie_ok.get(), "Planos arquitectónicos": var_planos_arq.get(), "Requiere maquinaria": var_maquinaria.get(),
            "Permisos disponibles": var_permisos.get(), "Planos de acabados": var_planos_acabados.get(),
            "Generación de planos": var_generacion_planos.get(), "Etapa de acabados": var_etapa_acabados.get(), "Obra blanca": var_obra_blanca.get(),
            "Observaciones iniciales": obtener_textbox(txt_observaciones_iniciales), "Observaciones finales": obtener_textbox(txt_finales),
            "Evidencia fotográfica": "Sí" if var_desea_evidencias.get() == "Sí" else "No",
            "¿Requiere EPP?": var_requiere_epp.get(),
            "Equipo de Protección Personal": "; ".join(f"{x['cantidad']} x {x['epp']}" + (f" ({x['observaciones']})" if x.get('observaciones') else "") for x in obtener_epp_obra()) if var_requiere_epp.get() == "Sí" else "No requerido",
            "__evidencias_fotograficas": list(evidencias) if var_desea_evidencias.get() == "Sí" else [],
            "Conceptos de obra": str(len(obtener_conceptos_obra_seleccionados())),
            "Canalización requerida": var_requiere_canalizacion.get(),
            "Partidas de canalización": str(len(obtener_canalizacion_materiales_obra())),
            "Anotación tipo plano": "Sí" if var_desea_anotacion_plano.get() == "Sí" else "No",
            "¿Se trabajará en Alturas?": var_trabajo_alturas.get(),
            "Sistema de acceso temporal": var_sistema_acceso.get() if var_trabajo_alturas.get() == "Sí" else "No aplica",
            "Altura": var_altura_trabajo.get() if var_trabajo_alturas.get() == "Sí" else "No aplica",
            "Riesgo": var_riesgo_trabajo.get() if var_trabajo_alturas.get() == "Sí" else "No aplica",
            "Archivos PDF / planos": "; ".join([Path(x).name for x in archivos_adjuntos] + [str(x.get("nombre") or x.get("storage_path") or "Archivo") for x in archivos_adjuntos_existentes]) or "No",
            "__anotacion_plano_base64": var_anotacion_plano_base64.get().strip() if var_desea_anotacion_plano.get() == "Sí" else "",
            "Materiales misceláneos": "; ".join(
                f"{m['material']}: {m['cantidad'] or 'Por definir'} {m['unidad']}" + (f" ({m['especificacion']})" if m['especificacion'] else "")
                for m in obtener_materiales_misc_obra()
            ) or "Sin materiales misceláneos",
        }
        return datos

    def seccion_ejecucion_pdf():
        return [{"Actividad": k, "Estado": v.get()} for k, v in ejecucion_vars.items()]

    def seccion_conceptos_obra_pdf():
        return [{
            "Tipo": c.get("tipo") or "", "Partida": c.get("partida") or "",
            "Unidad": c.get("unidad") or "", "Cantidad": c.get("cantidad") or "",
            "Concepto": c.get("concepto") or ""
        } for c in obtener_conceptos_obra_seleccionados()]

    def seccion_materiales_pdf():
        return [{
            "Material": m["material"], "Cantidad": m["cantidad"] or "Por definir",
            "Unidad": m["unidad"], "Especificación": m["especificacion"]
        } for m in obtener_materiales_misc_obra()]

    def seccion_canalizacion_pdf():
        return [{
            "Categoría": m.get("categoria", ""), "Tipo": m.get("tipo", ""),
            "Especificación": m.get("tamano_calibre_especificacion", ""),
            "Cantidad": m.get("cantidad", ""), "Unidad": m.get("unidad", ""),
        } for m in obtener_canalizacion_materiales_obra()]

    def preview_pdf():
        if not formulario_completo():
            messagebox.showwarning("Preview", "El preview se activa cuando los campos obligatorios estén completos.")
            return
        generar_pdf_preview("Obra Civil", datos_pdf(), [
            ("Ejecución", ["Actividad", "Estado"], seccion_ejecucion_pdf()),
            ("Conceptos de obra", ["Tipo", "Partida", "Unidad", "Cantidad", "Concepto"], seccion_conceptos_obra_pdf()),
            ("Materiales misceláneos", ["Material", "Cantidad", "Unidad", "Especificación"], seccion_materiales_pdf()),
            ("Canalización, cableado y materiales", ["Categoría", "Tipo", "Especificación", "Cantidad", "Unidad"], seccion_canalizacion_pdf()),
        ])

    def guardar_obra():
        if not formulario_completo():
            messagebox.showwarning("Campos obligatorios", "Debes llenar los campos obligatorios.")
            return
        if var_desea_evidencias.get() == "Sí" and not evidencias:
            messagebox.showwarning("Evidencia fotográfica", "Seleccionaste Sí. Agrega al menos una fotografía antes de guardar.")
            return
        if var_desea_archivos_adjuntos.get() == "Sí" and total_archivos_obra() == 0:
            messagebox.showwarning("Archivos adjuntos", "Seleccionaste Sí. Agrega al menos un PDF o plano antes de guardar.")
            return
        folio = var_folio.get().strip()
        if buscar_obra_civil_por_folio(folio):
            folio = generar_siguiente_folio("OBC")
            var_folio.set(folio)
        datos = {
            "id_aco": datos_aco.get("id_aco"), "id_sucursal": seleccion_catalogo.get("id_sucursal") or datos_aco.get("id_sucursal"), "id_contacto": seleccion_catalogo.get("id_contacto") or datos_aco.get("id_contacto"), "obc_folio": folio, "obc_fecha": var_fecha.get().strip() or None, "obc_aco_numero": var_aco.get().strip(),
            "obc_cliente": var_cliente.get().strip(), "obc_contacto": var_contacto.get().strip(), "obc_sucursal": var_sucursal.get().strip(),
            "obc_direccion": var_direccion.get().strip(), "obc_responsable_axia": var_responsable.get().strip(), "obc_supervisor": var_supervisor.get().strip(),
            "obc_dias_trabajo": int(var_dias_trabajo.get().strip()), "obc_personas_considerar": int(var_personas_considerar.get().strip()),
            "obc_tipo_giro": var_tipo_giro.get().strip(), "obc_nombre_proyecto": var_nombre_proyecto.get().strip(),
            "obc_superficie_disponible": var_superficie.get(), "obc_superficie_adecuada": var_superficie_ok.get(), "obc_planos_arquitectonicos": var_planos_arq.get(),
            "obc_requiere_maquinaria": var_maquinaria.get(), "obc_permisos": var_permisos.get(), "obc_observaciones_iniciales": obtener_textbox(txt_observaciones_iniciales),
            "obc_ejecucion_json": json.dumps({
                **{k: v.get() for k, v in ejecucion_vars.items()},
                "_datos_generales_axia": {
                    "supervisor": var_supervisor.get().strip(),
                    "encargado_proyecto": var_responsable.get().strip(),
                    "tecnico": var_tecnico.get().strip(),
                    "telefono_encargado_sucursal": var_telefono.get().strip(),
                    "correo_encargado_sucursal": var_correo.get().strip(),
                    "dias_trabajo": var_dias_trabajo.get().strip(),
                    "personas_considerar": var_personas_considerar.get().strip(),
                },
                "_conceptos_obra": obtener_conceptos_obra_seleccionados(),
                "_epp": {"requiere": var_requiere_epp.get(), "partidas": obtener_epp_obra()},
                "_acceso_alturas_riesgos": {
                    "trabajo_alturas": var_trabajo_alturas.get(),
                    "sistema_acceso_temporal": var_sistema_acceso.get() if var_trabajo_alturas.get() == "Sí" else "",
                    "altura": var_altura_trabajo.get() if var_trabajo_alturas.get() == "Sí" else "",
                    "riesgo": var_riesgo_trabajo.get() if var_trabajo_alturas.get() == "Sí" else "",
                },
                "_materiales_miscelaneos": obtener_materiales_misc_obra(),
                "_canalizacion_materiales": {
                    "requiere": var_requiere_canalizacion.get(),
                    "partidas": obtener_canalizacion_materiales_obra(),
                },
            }, ensure_ascii=False),
            "obc_planos_acabados": var_planos_acabados.get(), "obc_generacion_planos": var_generacion_planos.get(), "obc_etapa_acabados": var_etapa_acabados.get(),
            "obc_obra_blanca": var_obra_blanca.get(), "obc_evidencias_json": "[]", "obc_archivos_adjuntos_json": "[]",
            "obc_anotacion_plano_json": json.dumps({"habilitado": var_desea_anotacion_plano.get() == "Sí", "imagen_base64": var_anotacion_plano_base64.get().strip() if var_desea_anotacion_plano.get() == "Sí" else ""}, ensure_ascii=False),
            "obc_observaciones_finales": obtener_textbox(txt_finales),
            "obc_estatus": 1, "creado_por": usuario_activo.get("usuario"),
        }
        resultado = crear_obra_civil(datos)
        if resultado:
            registro_creado = resultado[0] if isinstance(resultado, list) and resultado else {}
            evidencias_subidas = []
            if var_desea_evidencias.get() == "Sí":
                try:
                    evidencias_subidas = subir_evidencias_obra_civil(folio, evidencias)
                    if not evidencias_subidas:
                        raise RuntimeError("Supabase no confirmó la carga de las fotografías.")
                    id_obra_civil = registro_creado.get("id_obra_civil")
                    if not id_obra_civil or actualizar_evidencias_obra_civil(id_obra_civil, evidencias_subidas) is None:
                        raise RuntimeError("No fue posible asociar las fotografías a la obra civil.")
                except Exception as error:
                    show_operation_error("Error al guardar evidencias", "Subir evidencia fotográfica de Obra Civil", error)
                    return
            archivos_subidos = []
            if var_desea_archivos_adjuntos.get() == "Sí" and archivos_adjuntos:
                try:
                    archivos_subidos = subir_archivos_obra_civil(folio, archivos_adjuntos)
                    if not archivos_subidos:
                        raise RuntimeError("Supabase no confirmó la carga de los PDF/planos.")
                    id_obra_civil = registro_creado.get("id_obra_civil")
                    if not id_obra_civil or actualizar_archivos_obra_civil(id_obra_civil, archivos_subidos) is None:
                        raise RuntimeError("No fue posible asociar los archivos a la obra civil.")
                except Exception as error:
                    show_operation_error("Error al guardar archivos", "Subir PDF/planos de Obra Civil", error)
                    return
            registrar_movimiento(modulo="Obra Civil", accion="CREAR", descripcion=f"El usuario creó la obra civil {folio}", registro_afectado=folio)
            datos_pdf_final = datos_pdf()
            datos_pdf_final["__evidencias_fotograficas"] = evidencias_subidas or list(evidencias)
            datos_pdf_final["Archivos PDF / planos"] = "; ".join(str(x.get("nombre") or "Archivo") for x in archivos_subidos) or datos_pdf_final.get("Archivos PDF / planos", "No")
            ruta_pdf = generar_pdf_archivo("Obra Civil", datos_pdf_final, nombre_archivo=folio, subcarpeta="obras_civiles", secciones_tabla=[
                ("Ejecución", ["Actividad", "Estado"], seccion_ejecucion_pdf()),
                ("Conceptos de obra", ["Tipo", "Partida", "Unidad", "Cantidad", "Concepto"], seccion_conceptos_obra_pdf()),
                ("Materiales misceláneos", ["Material", "Cantidad", "Unidad", "Especificación"], seccion_materiales_pdf()),
                ("Canalización, cableado y materiales", ["Categoría", "Tipo", "Especificación", "Cantidad", "Unidad"], seccion_canalizacion_pdf()),
            ])
            mensaje_pdf = f"\n\nPDF guardado en:\n{ruta_pdf}" if ruta_pdf else "\n\nNo se pudo guardar el PDF local."
            try:
                from services.levantamiento_borradores_service import eliminar_borrador
                eliminar_borrador(usuario_activo)
            except Exception:
                logger.debug("No fue posible eliminar el borrador de Obra Civil ya guardado.", exc_info=True)
            messagebox.showinfo("Registro correcto", "La obra civil fue registrada correctamente." + mensaje_pdf)
            app.mostrar_vista_inicio_aco()
        else:
            show_operation_error("Error al guardar", "Registrar obra civil")

    def _snapshot_borrador_obra():
        estado = {
            "folio": var_folio.get(), "fecha": var_fecha.get(), "aco": var_aco.get(), "cliente": var_cliente.get(),
            "contacto": var_contacto.get(), "telefono": var_telefono.get(), "correo": var_correo.get(),
            "sucursal": var_sucursal.get(), "encargado_sucursal": var_encargado_sucursal.get(),
            "direccion": var_direccion.get(), "responsable": var_responsable.get(), "supervisor": var_supervisor.get(),
            "tecnico": var_tecnico.get(), "tipo_giro": var_tipo_giro.get(), "nombre_proyecto": var_nombre_proyecto.get(),
            "dias_trabajo": var_dias_trabajo.get(), "personas": var_personas_considerar.get(),
            "requiere_epp": var_requiere_epp.get(), "superficie": var_superficie.get(), "superficie_ok": var_superficie_ok.get(),
            "planos_arq": var_planos_arq.get(), "maquinaria": var_maquinaria.get(), "permisos": var_permisos.get(),
            "desea_anotacion": var_desea_anotacion_plano.get(), "anotacion_base64": var_anotacion_plano_base64.get(),
            "desea_evidencias": var_desea_evidencias.get(), "evidencias_locales": list(evidencias),
            "desea_archivos": var_desea_archivos_adjuntos.get(), "archivos_locales": list(archivos_adjuntos),
            "trabajo_alturas": var_trabajo_alturas.get(), "sistema_acceso": var_sistema_acceso.get(),
            "altura_trabajo": var_altura_trabajo.get(), "riesgo": var_riesgo_trabajo.get(),
            "requiere_canalizacion": var_requiere_canalizacion.get(),
            "planos_acabados": var_planos_acabados.get(), "generacion_planos": var_generacion_planos.get(),
            "etapa_acabados": var_etapa_acabados.get(), "obra_blanca": var_obra_blanca.get(),
            "observaciones_iniciales": obtener_textbox(txt_observaciones_iniciales),
            "observaciones_finales": obtener_textbox(txt_finales),
            "ejecucion": {k: v.get() for k, v in ejecucion_vars.items()},
        }
        return {
            "lev_cliente": var_cliente.get().strip(),
            "lev_contacto": var_contacto.get().strip(),
            "lev_observaciones": obtener_textbox(txt_finales),
            "lev_descripcion": var_nombre_proyecto.get().strip(),
            "lev_detalle_tecnico_json": json.dumps({"obra_civil": estado}, ensure_ascii=False),
            "__obra_civil_borrador": estado,
        }

    try:
        if hasattr(app, "registrar_proveedor_borrador_levantamiento"):
            app.registrar_proveedor_borrador_levantamiento("Obra Civil", _snapshot_borrador_obra)
    except Exception:
        logger.debug("No fue posible registrar autoguardado de Obra Civil.", exc_info=True)

    botones = ctk.CTkFrame(contenedor, fg_color="#F4F4F4", height=58, corner_radius=0)
    botones.grid(row=1, column=0, sticky="ew")
    barra_botones = ctk.CTkFrame(botones, fg_color="transparent")
    barra_botones.pack(anchor="center", pady=4)
    ctk.CTkButton(barra_botones, text="⬅ Atrás", width=120, height=38, corner_radius=10, fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT, command=app.volver_atras).grid(row=0, column=0, padx=4)
    btn_guardar = ctk.CTkButton(barra_botones, text="💾 Guardar Obra Civil", width=190, height=38, corner_radius=10, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=guardar_obra, state="disabled")
    btn_guardar.grid(row=0, column=1, padx=4)
    btn_preview = ctk.CTkButton(barra_botones, text="👁 Preview PDF", width=165, height=38, corner_radius=10, fg_color="#1F4E79", hover_color="#173B5C", font=BUTTON_FONT, command=preview_pdf, state="disabled")
    btn_preview.grid(row=0, column=2, padx=4)
    ctk.CTkButton(barra_botones, text="↩ Cancelar", width=130, height=38, corner_radius=10, fg_color="gray", font=BUTTON_FONT, command=app.mostrar_vista_inicio_aco).grid(row=0, column=3, padx=4)
    enfocar_inicio_formulario(card, foco_inicial)
    validar_preview()
