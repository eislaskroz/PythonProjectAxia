from uuid import uuid4
from core.error_reporting import show_operation_error
"""Formulario Obra Civil / Proyecto Ejecutivo AXIA."""

from core.logger import configurar_logger

logger = configurar_logger(__name__)

import json
from pathlib import Path
import customtkinter as ctk
from ui.form_fields import AxiaEntry, AxiaTextbox
from tkinter import messagebox, filedialog
from ui.native_combobox import NativeComboBox
from views.levantamientos.catalogos_canalizacion import (
    TIPOS_ABRAZADERAS, TIPOS_CABLE_DATOS_CONTROL, TIPOS_CANALIZACION,
    TIPOS_CONECTORES, TIPOS_COPLES, TIPOS_REGISTROS, TIPOS_TUBOS, TAMANOS_TUBOS,
    especificaciones_por_categoria, TIPOS_CANALETA, normalizar_opciones_canalizacion,
)
from views.levantamientos.canalizacion_aproximado import (
    texto_aproximado_canalizacion,
    unidad_fija_canalizacion,
    unidad_forzada_canalizacion,
)

from app_context import obtener_usuario_actual
from security.permissions import puede_generar_levantamiento
from services.aco_context_service import normalizar_datos_aco
from services.acos_service import buscar_aco_por_numero
from services.clientes_service import buscar_clientes, construir_direccion_cliente
from services.sucursales_service import obtener_sucursales_por_cliente, obtener_contactos_por_sucursal, construir_domicilio_sucursal
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
from services.obras_civiles_service import crear_obra_civil, actualizar_evidencias_obra_civil, actualizar_archivos_obra_civil
from services.obra_conceptos_service import obtener_conceptos_obra, obtener_tipos_concepto_obra, filtrar_conceptos_por_tipo
from services.bitacora_evidencias_service import subir_evidencias_obra_civil, subir_archivos_obra_civil
from ui.colors import PRIMARY, SECONDARY, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER
from ui.date_picker import abrir_selector_fecha
from ui.fonts import BUTTON_FONT
from ui.numeric_masks import aplicar_mascara_numerica, NUMBER, INTEGER
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
    nombres_validables = {}
    evidencias = []
    archivos_adjuntos = []
    archivos_adjuntos_existentes = []
    materiales_miscelaneos_items = []
    canalizacion_materiales_items = []
    conceptos_obra_items = []
    catalogo_conceptos_obra = obtener_conceptos_obra()
    btn_preview = None
    btn_guardar = None
    lbl_faltantes = None

    # El folio definitivo se asigna al registrar en Supabase (trigger atómico).
    var_folio = ctk.StringVar(value="Pendiente de asignación")
    guardado_servidor = {
        "id": None, "folio": "", "fotos": None, "archivos": None,
        "solicitud": str(uuid4()),
    }
    var_fecha = ctk.StringVar()
    var_desea_notas_cliente = ctk.StringVar(value="No")
    var_notas_cliente = ctk.StringVar()
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
    OPCION_CLIENTE_OTROS = "Otros"
    modo_manual_cliente = {"activo": False}
    controles_cliente = {"manual_cliente": None, "direccion": None, "telefono": None, "correo": None}
    controles_manual_catalogo = {}
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
    var_requiere_epp = ctk.StringVar(value="Sí" if not borrador else "No")
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
        opciones_reales = [nombre for nombre in sorted(clientes_por_nombre) if nombre.casefold() != "otros"]
        var_cliente_selector.set(opciones_reales[0] if opciones_reales else OPCION_CLIENTE_OTROS)
    elif not aco:
        var_cliente_selector.set(OPCION_CLIENTE_OTROS)
    elif aco:
        var_cliente_selector.set(str(var_cliente.get() or "").strip() or OPCION_CLIENTE_OTROS)
        cliente_aco = clientes_por_nombre.get(str(var_cliente.get() or "").strip())
        if cliente_aco:
            var_direccion.set(construir_direccion_cliente(cliente_aco))

    sucursales_por_nombre = {}
    contactos_por_nombre = {}
    OPCION_PRINCIPAL = "PRINCIPAL / DATOS DEL CLIENTE"
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
        if modo_manual_cliente["activo"]:
            var_contacto.set(var_encargado_sucursal.get().strip())
            return
        contacto = contactos_por_nombre.get(str(nombre or var_encargado_sucursal.get() or "").strip())
        seleccion_catalogo["id_contacto"] = _id_contacto(contacto) if contacto else None
        if contacto:
            var_contacto.set(str(contacto.get("con_nombre") or "").strip())
            var_telefono.set(str(contacto.get("con_telefono") or "").strip())
            var_correo.set(str(contacto.get("con_correo") or "").strip())

    def _restaurar_datos_cliente_principal():
        if modo_manual_cliente["activo"]:
            return
        cliente_db = clientes_por_nombre.get(str(var_cliente.get() or var_cliente_selector.get() or "").strip())
        if not cliente_db:
            return
        seleccion_catalogo["id_sucursal"] = None
        seleccion_catalogo["id_contacto"] = None
        var_contacto.set(str(cliente_db.get("cli_contacto") or "").strip())
        var_telefono.set(str(cliente_db.get("cli_telefono") or "").strip())
        var_correo.set(str(cliente_db.get("cli_correo") or "").strip())
        var_direccion.set(construir_direccion_cliente(cliente_db))
        var_encargado_sucursal.set("Contacto principal del cliente")
        if combo_encargado["widget"] is not None:
            combo_encargado["widget"].configure(values=["Contacto principal del cliente"])

    def cargar_contactos(nombre=None, id_contacto_preferido=None):
        if modo_manual_cliente["activo"]:
            var_contacto.set(var_encargado_sucursal.get().strip())
            return
        etiqueta = str(nombre or var_sucursal.get() or "").strip()
        if etiqueta == OPCION_PRINCIPAL or etiqueta == "Sin sucursales registradas":
            contactos_por_nombre.clear()
            _restaurar_datos_cliente_principal()
            return
        sucursal = sucursales_por_nombre.get(etiqueta)
        contactos_por_nombre.clear()
        seleccion_catalogo["id_sucursal"] = _id_sucursal(sucursal) if sucursal else None
        seleccion_catalogo["id_contacto"] = None
        if sucursal:
            # La sucursal fue elegida explícitamente: sus datos tienen prioridad.
            var_contacto.set("")
            var_telefono.set(str(sucursal.get("suc_telefono") or "").strip())
            var_correo.set(str(sucursal.get("suc_correo") or "").strip())
            domicilio_sucursal = construir_domicilio_sucursal(sucursal)
            if domicilio_sucursal:
                var_direccion.set(domicilio_sucursal)
            for contacto in obtener_contactos_por_sucursal(_id_sucursal(sucursal)) or []:
                contactos_por_nombre[_nombre_contacto(contacto)] = contacto
        else:
            _restaurar_datos_cliente_principal()
            return
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
        if modo_manual_cliente["activo"]:
            return
        seleccion_catalogo["id_cliente"] = id_cliente
        sucursales_por_nombre.clear()
        for sucursal in obtener_sucursales_por_cliente(id_cliente) or []:
            sucursales_por_nombre[_nombre_sucursal(sucursal)] = sucursal
        opciones = [OPCION_PRINCIPAL] + list(sucursales_por_nombre)
        if combo_sucursal["widget"] is not None:
            combo_sucursal["widget"].configure(values=opciones)
        elegido = None
        if id_sucursal_preferida:
            for etiqueta, sucursal in sucursales_por_nombre.items():
                if str(_id_sucursal(sucursal)) == str(id_sucursal_preferida):
                    elegido = etiqueta
                    break
        elegido = elegido or OPCION_PRINCIPAL
        var_sucursal.set(elegido)
        cargar_contactos(elegido, id_contacto_preferido)

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=7, pady=5)
    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_rowconfigure(1, weight=0)
    contenedor.grid_columnconfigure(0, weight=1)

    card = ctk.CTkScrollableFrame(contenedor, height=520, fg_color=WHITE, corner_radius=18)
    card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
    form = ctk.CTkFrame(card, fg_color="transparent")
    form.pack(fill="x", expand=True, padx=12, pady=(9, 4))
    for col in range(5):
        form.grid_columnconfigure(col, weight=1, uniform="cols")

    _validar_preview_after_id = None

    def validar_preview():
        try:
            completo = formulario_completo()
            estado = "normal" if completo else "disabled"
            if btn_preview is not None:
                btn_preview.configure(state=estado)
            if btn_guardar is not None:
                btn_guardar.configure(state=estado)
            if lbl_faltantes is not None:
                pendientes = campos_faltantes_obra() if not completo else []
                if completo:
                    lbl_faltantes.configure(text="✓ Formulario completo. Ya puedes guardar o generar el Preview PDF.", text_color="#15803D")
                else:
                    resumen = ", ".join(pendientes[:10])
                    if len(pendientes) > 10:
                        resumen += f" … (+{len(pendientes)-10})"
                    lbl_faltantes.configure(text=f"⚠ Faltan {len(pendientes)} requisito(s): {resumen}" if pendientes else "⚠ Aún existen campos obligatorios pendientes.", text_color="#B45309")
        except Exception:
            logger.debug("Excepción recuperable controlada.", exc_info=True)

    def programar_validacion_preview(delay_ms=110):
        """Evita recalcular todo el formulario de Obra Civil en cada pulsación."""
        nonlocal _validar_preview_after_id
        try:
            if _validar_preview_after_id is not None:
                form.after_cancel(_validar_preview_after_id)
        except Exception:
            pass
        try:
            _validar_preview_after_id = form.after(delay_ms, validar_preview)
        except Exception:
            validar_preview()

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
        e = AxiaEntry(c, textvariable=var, placeholder_text=placeholder, height=ENTRY_H, corner_radius=8, font=SMALL_FONT, state=state)
        e.pack(fill="x")
        if texto in {"¿Cuántos días de trabajo se proyectan?", "¿Cuántas personas se consideran?"}:
            aplicar_mascara_numerica(e, var, INTEGER)
        if date and state != "disabled":
            e.bind("<Button-1>", lambda _event, v=var: (abrir_selector_fecha(c, v), validar_preview()))
        if lock:
            entradas_bloqueadas.append(e)
        if required and state != "disabled":
            campos_validables.append(var)
            nombres_validables[id(var)] = texto
            var.trace_add("write", lambda *_: programar_validacion_preview())
        return e

    def option(texto, var, opciones, fila, col, required=True, colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        o = NativeComboBox(c, variable=var, values=opciones, height=OPTION_H, corner_radius=8, font=SMALL_FONT)
        o.pack(fill="x")
        if required:
            campos_validables.append(var)
            nombres_validables[id(var)] = texto
            var.trace_add("write", lambda *_: programar_validacion_preview())
        return o

    def _mostrar_entrada_manual_catalogo(tipo, activar):
        conjunto = controles_manual_catalogo.get(tipo) or {}
        selector = conjunto.get("selector")
        entrada = conjunto.get("entrada")
        if selector is None or entrada is None:
            return
        if activar:
            selector.pack_forget()
            entrada.pack(fill="x")
        else:
            entrada.pack_forget()
            selector.pack(fill="x")

    def activar_captura_manual(conservar_datos=False):
        """Habilita datos generales independientes de db_clientes, sin tocar el folio."""
        if modo_manual_cliente["activo"] and not conservar_datos:
            return
        modo_manual_cliente["activo"] = True
        seleccion_catalogo.update(id_cliente=None, id_sucursal=None, id_contacto=None)
        if not conservar_datos:
            for variable in (var_cliente, var_contacto, var_sucursal, var_encargado_sucursal,
                             var_direccion, var_telefono, var_correo):
                variable.set("")
        if controles_cliente["manual_cliente"] is not None:
            controles_cliente["manual_cliente"].pack(fill="x", pady=(4, 0))
        for tipo in ("sucursal", "contacto"):
            _mostrar_entrada_manual_catalogo(tipo, True)
        for nombre in ("direccion", "telefono", "correo"):
            widget = controles_cliente.get(nombre)
            if widget is not None:
                widget.configure(state="normal")
        programar_validacion_preview()

    def desactivar_captura_manual():
        modo_manual_cliente["activo"] = False
        if controles_cliente["manual_cliente"] is not None:
            controles_cliente["manual_cliente"].pack_forget()
        for tipo in ("sucursal", "contacto"):
            _mostrar_entrada_manual_catalogo(tipo, False)
        for nombre in ("direccion", "telefono", "correo"):
            widget = controles_cliente.get(nombre)
            if widget is not None:
                widget.configure(state="disabled")
        programar_validacion_preview()

    def cliente_selector(texto, fila, col, colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        if aco:
            nombre_aco = str(datos_aco.get("cliente") or "").strip()
            nombres = [nombre_aco] if nombre_aco else []
        else:
            nombres = [nombre for nombre in sorted(clientes_por_nombre) if nombre.casefold() != "otros"]
        o = NativeComboBox(
            c, variable=var_cliente_selector,
            values=nombres + [OPCION_CLIENTE_OTROS],
            height=OPTION_H, corner_radius=8, font=SMALL_FONT,
            command=lambda nombre: cargar_cliente(nombre),
        )
        o.pack(fill="x")
        e_manual = AxiaEntry(c, textvariable=var_cliente, height=ENTRY_H,
                             placeholder_text="Escribe el nombre del cliente", font=SMALL_FONT)
        controles_cliente["manual_cliente"] = e_manual
        campos_validables.append(var_cliente)
        nombres_validables[id(var_cliente)] = texto
        var_cliente.trace_add("write", lambda *_: programar_validacion_preview())
        return o

    def catalogo_selector(texto, var, fila, col, tipo="sucursal", colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        opciones = ["Sin sucursales registradas"] if tipo == "sucursal" else ["Sin encargados registrados"]
        command = cargar_contactos if tipo == "sucursal" else cargar_encargado
        o = NativeComboBox(c, variable=var, values=opciones, height=OPTION_H,
                           corner_radius=8, font=SMALL_FONT, command=command)
        o.pack(fill="x")
        e = AxiaEntry(c, textvariable=var, height=ENTRY_H, font=SMALL_FONT,
                      placeholder_text="Captura manual")
        controles_manual_catalogo[tipo] = {"selector": o, "entrada": e}
        if tipo == "sucursal":
            combo_sucursal["widget"] = o
        else:
            combo_encargado["widget"] = o
        return o

    var_encargado_sucursal.trace_add(
        "write", lambda *_: (var_contacto.set(var_encargado_sucursal.get().strip())
                               if modo_manual_cliente["activo"] else None)
    )

    def textbox(texto, fila, col, colspan=5, height=70):
        c = celda(fila, col, colspan)
        label(c, texto)
        box = AxiaTextbox(c, height=height, corner_radius=8, font=SMALL_FONT)
        box.pack(fill="x")
        return box

    def bloquear_autollenados():
        if not modo_manual_cliente["activo"]:
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
        """Selecciona cliente del catálogo o permite capturar todos sus datos en Otros."""
        nombre_cliente = str(nombre or var_cliente_selector.get() or "").strip()
        if nombre_cliente.casefold() == OPCION_CLIENTE_OTROS.casefold():
            activar_captura_manual()
            return
        desactivar_captura_manual()
        if aco and nombre_cliente == str(datos_aco.get("cliente") or "").strip():
            var_cliente.set(nombre_cliente)
            var_contacto.set(str(datos_aco.get("contacto") or ""))
            var_telefono.set(str(datos_aco.get("telefono") or ""))
            var_correo.set(str(datos_aco.get("correo") or ""))
            var_direccion.set(str(datos_aco.get("direccion") or ""))
            cargar_sucursales(datos_aco.get("id_cliente"), datos_aco.get("id_sucursal"),
                               datos_aco.get("id_contacto"))
            validar_preview()
            return
        cliente_db = clientes_por_nombre.get(nombre_cliente)
        if not cliente_db:
            return
        var_cliente.set(nombre_cliente)
        var_contacto.set(str(cliente_db.get("cli_contacto") or "").strip())
        var_telefono.set(str(cliente_db.get("cli_telefono") or "").strip())
        var_correo.set(str(cliente_db.get("cli_correo") or "").strip())
        var_encargado_sucursal.set("Contacto principal del cliente")
        var_direccion.set(construir_direccion_cliente(cliente_db))
        cargar_sucursales(_id_cliente(cliente_db))
        validar_preview()

    seccion("Datos generales", 0)
    entry("Folio OBC", var_folio, 1, 0, "Automático", state="disabled", required=False)

    cliente_selector("Cliente", 1, 1)
    controles_cliente["direccion"] = entry("Dirección Fiscal", var_direccion, 1, 2,
        "Dirección fiscal del cliente", lock=True, colspan=3)
    catalogo_selector("Sucursal", var_sucursal, 2, 0, tipo="sucursal")
    catalogo_selector("Encargado de sucursal", var_encargado_sucursal, 2, 1,
                      tipo="contacto", colspan=2)
    controles_cliente["telefono"] = entry("Teléfono", var_telefono, 2, 3,
        "Autollenado desde encargado", state="disabled", required=False)
    controles_cliente["correo"] = entry("Correo", var_correo, 2, 4,
        "Autollenado desde encargado", state="disabled", required=False)
    foco_inicial = None
    if aco:
        cargar_cliente(var_cliente_selector.get())
    elif var_cliente_selector.get().casefold() == OPCION_CLIENTE_OTROS.casefold():
        activar_captura_manual()
    else:
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
        ec = AxiaEntry(epp_rows,textvariable=vc,width=80,height=ENTRY_H,corner_radius=0)
        aplicar_mascara_numerica(ec, vc, NUMBER)
        ec.grid(row=fila_e,column=1,sticky="w",padx=3,pady=2)
        eo = AxiaEntry(epp_rows,textvariable=vo,height=ENTRY_H,corner_radius=0,placeholder_text="Talla, clase, norma o detalle especial")
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
            if not epp_items:
                agregar_epp_obra({"epp":"Casco de seguridad","cantidad":"1"})
                agregar_epp_obra({"epp":"Botas de seguridad","cantidad":"1"})
                agregar_epp_obra({"epp":"Chaleco reflejante / alta visibilidad","cantidad":"1"})
        else: epp_rows.grid_remove()
        try:
            validar_preview()
        except (NameError, UnboundLocalError):
            pass
    var_requiere_epp.trace_add("write",vis_epp_obra); vis_epp_obra()

    entry("Fecha", var_fecha, 7, 0, "YYYY-MM-DD", date=True)
    option("¿Deseas agregar notas sobre el cliente?", var_desea_notas_cliente, SI_NO, 7, 1, required=False)
    entry_notas_cliente = entry("Notas", var_notas_cliente, 7, 2, "Notas breves sobre el cliente", state="disabled", required=False, colspan=3)

    def actualizar_notas_cliente_obra(*_):
        habilitado = var_desea_notas_cliente.get() == "Sí"
        entry_notas_cliente.configure(state="normal" if habilitado else "disabled")
        if not habilitado:
            var_notas_cliente.set("")
        validar_preview()
    var_desea_notas_cliente.trace_add("write", actualizar_notas_cliente_obra)
    var_notas_cliente.trace_add("write", lambda *_: programar_validacion_preview())
    actualizar_notas_cliente_obra()

    entry("Tipo de giro", var_tipo_giro, 8, 0, "Ej. Bancario, retail, oficina")
    entry("Nombre del proyecto", var_nombre_proyecto, 8, 1, "Proyecto ejecutivo", colspan=4)

    seccion("Planeación inicial", 9)
    option("¿Se cuenta con superficie?", var_superficie, SI_NO, 10, 0)
    option("¿La superficie es adecuada?", var_superficie_ok, SI_NO, 10, 1)
    option("¿Planos y diseño arquitectónico?", var_planos_arq, SI_NO, 10, 2)
    option("¿Requiere maquinaria?", var_maquinaria, SI_NO, 10, 3)
    option("¿Se cuenta con permisos?", var_permisos, SI_NO, 10, 4)
    txt_observaciones_iniciales = textbox("Observaciones iniciales", 12, 0, 5)

    seccion("Ejecución", 13)
    fila = 14
    col = 0
    for nombre, var in ejecucion_vars.items():
        option(nombre, var, ESTADOS, fila, col)
        col += 1
        if col == 4:
            col = 0
            fila += 1

    seccion("Acabados", 20)
    option("¿Planos de detalles y acabados?", var_planos_acabados, SI_NO, 21, 0)
    option("Generación de planos", var_generacion_planos, ["Sí", "No", "No aplica"], 21, 1)
    option("Etapa de acabados", var_etapa_acabados, ESTADOS, 21, 2)
    option("Obra blanca", var_obra_blanca, ESTADOS, 21, 3)

    seccion("Conceptos de obra requeridos", 22)
    panel_conceptos = celda(23, 0, 5)
    # Prioriza el concepto: ~25% más espacio que el layout anterior.
    panel_conceptos.grid_columnconfigure(0, weight=2)
    panel_conceptos.grid_columnconfigure(1, weight=8)
    panel_conceptos.grid_columnconfigure(2, weight=1, minsize=68)
    panel_conceptos.grid_columnconfigure(3, weight=1, minsize=72)
    panel_conceptos.grid_columnconfigure(4, weight=1, minsize=76)
    for col, encabezado in enumerate(("Tipo", "Partida / concepto", "Unidad", "Cantidad", "Acción")):
        ctk.CTkLabel(panel_conceptos, text=encabezado, font=("Montserrat", 12)).grid(row=0, column=col, sticky="w", padx=3)

    TIPO_CONCEPTO_OTROS = "OTROS"
    tipos_concepto_obra = [t for t in obtener_tipos_concepto_obra(catalogo_conceptos_obra)
                           if t.casefold() != TIPO_CONCEPTO_OTROS.casefold()] + [TIPO_CONCEPTO_OTROS]

    def _etiqueta_concepto_obra(item):
        partida = str(item.get("obra_partida") or "").strip()
        concepto = " ".join(str(item.get("obra_concepto") or "").split())
        # No truncar: el usuario debe poder identificar el concepto completo.
        return f"{partida} — {concepto}" if concepto else partida

    def agregar_concepto_obra():
        # El identificador de fila se incrementa para evitar solapamientos tras eliminar.
        fila_concepto = 1 + max((x["fila"] for x in conceptos_obra_items), default=0)
        tipo_inicial = next((tipo for tipo in tipos_concepto_obra if tipo != TIPO_CONCEPTO_OTROS), TIPO_CONCEPTO_OTROS)
        conceptos_tipo = filtrar_conceptos_por_tipo(tipo_inicial, catalogo_conceptos_obra) if tipo_inicial != TIPO_CONCEPTO_OTROS else []
        etiquetas = [_etiqueta_concepto_obra(item) for item in conceptos_tipo] or ["Sin conceptos disponibles"]

        vtipo = ctk.StringVar(value=tipo_inicial)
        vconcepto = ctk.StringVar(value=etiquetas[0] if conceptos_tipo else "")
        vunidad = ctk.StringVar(value=str((conceptos_tipo[0].get("obra_unidad") if conceptos_tipo else "") or ""))
        vcantidad = ctk.StringVar(value="1")
        for variable in (vtipo, vconcepto, vunidad, vcantidad):
            variable.trace_add("write", lambda *_: programar_validacion_preview())

        otipo = NativeComboBox(panel_conceptos, variable=vtipo, values=tipos_concepto_obra, height=30)
        otipo.grid(row=fila_concepto, column=0, sticky="ew", padx=3, pady=2)
        # El Combobox nativo solo muestra una línea y recorta las partidas largas.
        # Se conserva para elegir conceptos del catálogo, con una vista multilínea
        # desplazable dentro de la misma celda (tres renglones visibles).
        cont_concepto = ctk.CTkFrame(panel_conceptos, fg_color="transparent")
        cont_concepto.grid(row=fila_concepto, column=1, sticky="ew", padx=3, pady=3)
        cont_concepto.grid_columnconfigure(0, weight=1)
        oconcepto = NativeComboBox(cont_concepto, variable=vconcepto, values=etiquetas, height=30)
        oconcepto.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        concepto_vista = AxiaTextbox(cont_concepto, height=66, wrap="word", state="disabled")
        concepto_vista.grid(row=1, column=0, sticky="ew")
        # OTROS: tres renglones editables y desplazamiento cuando el texto es mayor.
        econcepto = AxiaTextbox(cont_concepto, height=99, wrap="word")

        def _sincronizar_vista_concepto(*_):
            texto = vconcepto.get()
            concepto_vista.configure(state="normal")
            concepto_vista.delete("1.0", "end")
            concepto_vista.insert("1.0", texto)
            concepto_vista.configure(state="disabled")
            actual = econcepto.get("1.0", "end-1c")
            if actual != texto:
                econcepto.delete("1.0", "end")
                econcepto.insert("1.0", texto)

        def _capturar_concepto_manual(_evento=None):
            if vtipo.get() == TIPO_CONCEPTO_OTROS:
                texto = econcepto.get("1.0", "end-1c")
                if texto != vconcepto.get():
                    vconcepto.set(texto)

        vconcepto.trace_add("write", _sincronizar_vista_concepto)
        econcepto.bind("<KeyRelease>", _capturar_concepto_manual)
        econcepto.bind("<FocusOut>", _capturar_concepto_manual)
        _sincronizar_vista_concepto()
        econcepto.grid_remove()
        eunidad = AxiaEntry(panel_conceptos, textvariable=vunidad, width=68, height=30, state="disabled",
                            placeholder_text="Unidad")
        eunidad.grid(row=fila_concepto, column=2, sticky="ew", padx=3, pady=2)
        ecantidad = AxiaEntry(panel_conceptos, textvariable=vcantidad, width=72, height=30, placeholder_text="Ej. 12.5")
        aplicar_mascara_numerica(ecantidad, vcantidad, NUMBER)
        ecantidad.grid(row=fila_concepto, column=3, sticky="ew", padx=3, pady=2)

        item_concepto = {
            "fila": fila_concepto, "tipo": vtipo, "concepto_label": vconcepto,
            "unidad": vunidad, "cantidad": vcantidad,
            "conceptos_tipo": conceptos_tipo, "registro": conceptos_tipo[0] if conceptos_tipo else {},
            "widgets": [otipo, oconcepto, econcepto, eunidad, ecantidad,
                        concepto_vista, cont_concepto],
        }

        def seleccionar_concepto(_valor=None):
            if vtipo.get() == TIPO_CONCEPTO_OTROS:
                return
            registro = next((x for x in item_concepto["conceptos_tipo"]
                             if _etiqueta_concepto_obra(x) == vconcepto.get()), {})
            item_concepto["registro"] = registro
            vunidad.set(str(registro.get("obra_unidad") or ""))
            validar_preview()

        def cambiar_tipo(valor, *, restaurar=False):
            if valor == TIPO_CONCEPTO_OTROS:
                item_concepto["registro"] = {}
                oconcepto.grid_remove()
                concepto_vista.grid_remove()
                econcepto.grid(row=0, column=0, sticky="ew")
                eunidad.configure(state="normal")
                if not restaurar:
                    vconcepto.set("")
                    vunidad.set("")
            else:
                nuevos = filtrar_conceptos_por_tipo(valor, catalogo_conceptos_obra)
                item_concepto["conceptos_tipo"] = nuevos
                nuevas_etiquetas = [_etiqueta_concepto_obra(x) for x in nuevos] or ["Sin conceptos disponibles"]
                oconcepto.configure(values=nuevas_etiquetas)
                econcepto.grid_remove()
                oconcepto.grid(row=0, column=0, sticky="ew", pady=(0, 3))
                concepto_vista.grid(row=1, column=0, sticky="ew")
                eunidad.configure(state="disabled")
                vconcepto.set(nuevas_etiquetas[0] if nuevos else "")
                seleccionar_concepto()
            programar_validacion_preview()

        otipo.configure(command=cambiar_tipo)
        oconcepto.configure(command=seleccionar_concepto)

        def eliminar_concepto():
            for widget in item_concepto["widgets"]:
                widget.destroy()
            conceptos_obra_items[:] = [x for x in conceptos_obra_items if x is not item_concepto]
            programar_validacion_preview()

        btn = ctk.CTkButton(panel_conceptos, text="Eliminar", width=76, height=30,
                            fg_color="#DC2626", hover_color="#B91C1C", command=eliminar_concepto)
        btn.grid(row=fila_concepto, column=4, sticky="ew", padx=3, pady=2)
        item_concepto["widgets"].append(btn)
        item_concepto["cambiar_tipo"] = cambiar_tipo
        conceptos_obra_items.append(item_concepto)
        if tipo_inicial == TIPO_CONCEPTO_OTROS:
            cambiar_tipo(TIPO_CONCEPTO_OTROS)

    def obtener_conceptos_obra_seleccionados():
        seleccion = []
        for item in conceptos_obra_items:
            cantidad = item["cantidad"].get().strip()
            if item["tipo"].get() == TIPO_CONCEPTO_OTROS:
                texto = item["concepto_label"].get().strip()
                unidad = item["unidad"].get().strip()
                if texto and unidad and cantidad:
                    seleccion.append({
                        "id_obra_concepto": None, "catalogo_ref": None,
                        "tipo": TIPO_CONCEPTO_OTROS, "partida": "OTROS",
                        "unidad": unidad, "concepto": texto,
                        "precio_unitario_referencia": None, "cantidad": cantidad,
                    })
                continue
            registro = item.get("registro") or {}
            if not registro or not cantidad:
                continue
            seleccion.append({
                "id_obra_concepto": registro.get("id_obra_concepto"),
                "catalogo_ref": registro.get("obra_catalogo_ref"),
                "tipo": registro.get("obra_tipo"), "partida": registro.get("obra_partida"),
                "unidad": registro.get("obra_unidad"), "concepto": registro.get("obra_concepto"),
                "precio_unitario_referencia": registro.get("obra_precio_unitario"), "cantidad": cantidad,
            })
        return seleccion

    if catalogo_conceptos_obra:
        agregar_concepto_obra()
    else:
        ctk.CTkLabel(panel_conceptos,
                     text="Catálogo no disponible. Puedes agregar conceptos manuales con OTROS.",
                     font=SMALL_FONT, text_color="#B45309").grid(row=1, column=0, columnspan=5,
                                                                 sticky="w", padx=3, pady=4)

    ctk.CTkButton(panel_conceptos, text="+ Agregar concepto", width=180, height=30,
                  fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_concepto_obra
                  ).grid(row=99, column=0, columnspan=2, sticky="w", padx=3, pady=(4, 2))

    seccion("Materiales misceláneos y consumibles", 24)
    panel_misc = celda(25, 0, 5)
    panel_misc.grid_columnconfigure(0, weight=2)
    panel_misc.grid_columnconfigure(1, weight=1)
    panel_misc.grid_columnconfigure(2, weight=1)
    panel_misc.grid_columnconfigure(3, weight=1)
    panel_misc.grid_columnconfigure(4, weight=3)
    panel_misc.grid_columnconfigure(5, weight=1)
    ctk.CTkLabel(panel_misc, text="Material", font=("Montserrat", 12)).grid(row=0, column=0, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="¿Se requiere?", font=("Montserrat", 12)).grid(row=0, column=1, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="Cantidad", font=("Montserrat", 12)).grid(row=0, column=2, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="Unidad", font=("Montserrat", 12)).grid(row=0, column=3, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="Especificación / medida", font=("Montserrat", 12)).grid(row=0, column=4, sticky="w", padx=3)
    ctk.CTkLabel(panel_misc, text="Acción", font=("Montserrat", 12)).grid(row=0, column=5, sticky="w", padx=3)

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
        em = AxiaEntry(panel_misc, textvariable=vm, height=30)
        em.grid(row=fila_misc, column=0, sticky="ew", padx=3, pady=2)
        if nombre:
            em.configure(state="readonly")
        ec = AxiaEntry(panel_misc, textvariable=vc, width=90, height=30, placeholder_text="Ej. 20", state="disabled")
        aplicar_mascara_numerica(ec, vc, NUMBER)
        ec.grid(row=fila_misc, column=2, sticky="w", padx=3, pady=2)
        ou = NativeComboBox(panel_misc, variable=vu, values=UNIDADES_MATERIAL, width=120, height=30, state="disabled")
        ou.grid(row=fila_misc, column=3, sticky="w", padx=3, pady=2)
        ee = AxiaEntry(
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
    seccion("Canalización, cableado y materiales", 26)
    panel_canalizacion = celda(27, 0, 5)
    for col, peso in enumerate((2, 4, 3, 2, 2, 2, 1)):
        panel_canalizacion.grid_columnconfigure(col, weight=peso)
    ctk.CTkLabel(
        panel_canalizacion,
        text="Agrega todas las partidas necesarias. Puedes registrar varios tipos, medidas y cantidades.",
        font=SMALL_FONT, text_color=TEXT_SECONDARY,
    ).grid(row=0, column=0, columnspan=7, sticky="w", padx=3, pady=(0, 6))
    ctk.CTkLabel(panel_canalizacion, text="¿Se requiere?", font=("Montserrat", 11)).grid(row=1, column=0, sticky="w", padx=3)
    combo_requiere_canalizacion = NativeComboBox(panel_canalizacion, variable=var_requiere_canalizacion, values=["Sí", "No"], width=120, height=31)
    combo_requiere_canalizacion.grid(row=2, column=0, sticky="w", padx=3, pady=(0, 5))
    for col, encabezado in enumerate(("Categoría", "Tipo", "Tamaño / calibre / especificación", "Cantidad", "Unidad", "Aproximado", "Acción")):
        ctk.CTkLabel(panel_canalizacion, text=encabezado, font=("Montserrat", 11), text_color=TEXT_PRIMARY).grid(row=3, column=col, sticky="w", padx=3, pady=(0, 2))

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
        if categoria == "Canaleta": return list(TIPOS_CANALETA)
        if categoria == "Canalización": return list(TIPOS_CANALIZACION)
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
                "unidad": unidad_forzada_canalizacion(categoria, item["unidad"].get()),
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
        vunidad = ctk.StringVar(value="Pieza(s)" if unidad_fija_canalizacion(categoria_inicial) else ("Metro(s)" if categoria_inicial in ("Canalización", "Cable") else "Pieza(s)"))
        ocategoria = NativeComboBox(panel_canalizacion, variable=vcategoria, values=categorias_canalizacion, width=155, height=31)
        otipo = NativeComboBox(panel_canalizacion, variable=vtipo, values=[], width=300, height=31)
        oespecificacion = NativeComboBox(panel_canalizacion, variable=vespecificacion, values=[], width=225, height=31)
        ecantidad = AxiaEntry(panel_canalizacion, textvariable=vcantidad, width=120, height=31, placeholder_text="Ej. 20")
        aplicar_mascara_numerica(ecantidad, vcantidad, NUMBER)
        ounidad = NativeComboBox(panel_canalizacion, variable=vunidad, values=["Metro(s)", "Pieza(s)", "Caja(s)", "Rollo(s)", "Juego(s)"], width=125, height=31)
        laproximado = ctk.CTkLabel(panel_canalizacion, text="—", font=SMALL_FONT, text_color="#15803D", anchor="w")
        widgets = [ocategoria, otipo, oespecificacion, ecantidad, ounidad]
        for col, widget in enumerate(widgets):
            widget.grid(row=fila, column=col, sticky="ew", padx=3, pady=2)
        laproximado.grid(row=fila, column=5, sticky="ew", padx=3, pady=2)
        item = {"categoria": vcategoria, "tipo": vtipo, "especificacion": vespecificacion, "cantidad": vcantidad, "unidad": vunidad, "widgets": widgets,
                "unidad_widget": ounidad, "aproximado_widget": laproximado}

        def actualizar_aproximado(*_):
            if unidad_fija_canalizacion(vcategoria.get()) and vunidad.get() != "Pieza(s)":
                vunidad.set("Pieza(s)")
                return
            laproximado.configure(text=texto_aproximado_canalizacion(
                vcategoria.get(), vcantidad.get(), vunidad.get()
            ))

        actualizando_catalogos = False

        def actualizar_catalogos(*_):
            nonlocal actualizando_catalogos
            if actualizando_catalogos:
                return
            actualizando_catalogos = True
            try:
                categoria = vcategoria.get().strip()
                tipos = catalogo_tipos_canalizacion(categoria)
                tipo, especificacion, especificaciones = normalizar_opciones_canalizacion(
                    categoria, vtipo.get(), vespecificacion.get(), tipos
                )
                otipo.configure(values=tipos)
                if vtipo.get() != tipo:
                    vtipo.set(tipo)
                oespecificacion.configure(values=especificaciones)
                if vespecificacion.get() != especificacion:
                    vespecificacion.set(especificacion)
                vunidad.set(unidad_forzada_canalizacion(categoria, vunidad.get()))
                if categoria in ("Canalización", "Cable") and not vunidad.get():
                    vunidad.set("Metro(s)")
                elif categoria not in ("Tubo", "Canalización", "Canaleta", "Cable") and vunidad.get() == "Metro(s)":
                    vunidad.set("Pieza(s)")
                ounidad.configure(state="disabled" if unidad_fija_canalizacion(categoria) else "normal")
                actualizar_aproximado()
                validar_preview()
            finally:
                actualizando_catalogos = False

        vcategoria.trace_add("write", actualizar_catalogos)
        vtipo.trace_add("write", actualizar_catalogos)
        vcantidad.trace_add("write", actualizar_aproximado)
        vunidad.trace_add("write", actualizar_aproximado)
        actualizar_catalogos()
        vcantidad.trace_add("write", lambda *_: programar_validacion_preview())

        def eliminar_partida():
            for widget in item.get("widgets", []):
                try: widget.destroy()
                except Exception: logger.debug("Excepción recuperable controlada.", exc_info=True)
            try: btn_eliminar.destroy()
            except Exception: logger.debug("Excepción recuperable controlada.", exc_info=True)
            try: laproximado.destroy()
            except Exception: logger.debug("Excepción recuperable controlada.", exc_info=True)
            canalizacion_materiales_items[:] = [x for x in canalizacion_materiales_items if x is not item]
            validar_preview()

        btn_eliminar = ctk.CTkButton(panel_canalizacion, text="Eliminar", width=78, height=31, fg_color="#DC2626", hover_color="#B91C1C", command=eliminar_partida)
        btn_eliminar.grid(row=fila, column=6, sticky="ew", padx=3, pady=2)
        item["widgets"].append(btn_eliminar)
        canalizacion_materiales_items.append(item)
        validar_preview()

    def actualizar_requiere_canalizacion_obra(*_):
        habilitado = var_requiere_canalizacion.get() == "Sí"
        estado = "normal" if habilitado else "disabled"
        for item in canalizacion_materiales_items:
            for widget in item.get("widgets", []):
                estado_widget = estado
                if widget is item.get("unidad_widget") and unidad_fija_canalizacion(item["categoria"].get()):
                    estado_widget = "disabled"
                try: widget.configure(state=estado_widget)
                except Exception: pass
        validar_preview()

    var_requiere_canalizacion.trace_add("write", actualizar_requiere_canalizacion_obra)
    ctk.CTkButton(panel_canalizacion, text="➕ Agregar partida", height=32, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_partida_canalizacion_obra).grid(row=1000, column=0, columnspan=2, sticky="w", padx=3, pady=(4, 2))
    agregar_partida_canalizacion_obra("Tubo")

    seccion("Acceso, alturas y riesgos", 28)
    panel_alturas = celda(29, 0, 5)
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
            w_alt = AxiaEntry(caja_alt, textvariable=variable_alt, height=30, corner_radius=0, font=SMALL_FONT, placeholder_text="Ej. 4 metros")
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

    seccion("Evidencia fotográfica", 30)
    panel_evidencias = celda(31, 0, 5)
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

    seccion("Anotaciones tipo plano", 32)
    panel_anotacion = celda(33, 0, 5)
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

    seccion("Archivos PDF o planos", 34)
    panel_archivos = celda(35, 0, 5)
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

    seccion("Observaciones finales", 36)
    txt_finales = textbox("Observaciones finales", 37, 0, 5, height=90)

    def _restaurar_borrador_obra():
        if not isinstance(borrador, dict):
            return
        estado = borrador.get("__obra_civil_borrador") if isinstance(borrador.get("__obra_civil_borrador"), dict) else {}
        if not estado:
            return
        registrado = estado.get("obra_guardada") or {}
        if isinstance(registrado, dict):
            # El token se mantiene también si la red falló antes de confirmar.
            from uuid import UUID
            try:
                guardado_servidor["solicitud"] = str(UUID(str(registrado.get("solicitud"))))
            except (TypeError, ValueError, AttributeError):
                pass  # borrador creado con una versión anterior
            guardado_servidor["fotos"] = registrado.get("fotos")
            guardado_servidor["archivos"] = registrado.get("archivos")
            if registrado.get("id") and registrado.get("folio"):
                guardado_servidor["id"] = registrado["id"]
                guardado_servidor["folio"] = registrado["folio"]
        mapa = {
            "folio": var_folio, "fecha": var_fecha, "desea_notas_cliente": var_desea_notas_cliente, "notas_cliente": var_notas_cliente, "aco": var_aco, "cliente": var_cliente,
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
                if clave == "folio" and not guardado_servidor["id"]:
                    continue  # Ignorar antiguos OBC provisionales de borradores.
                variable.set(str(estado.get(clave) or ""))
        if estado.get("cliente_manual") or (estado.get("cliente") and
                str(estado.get("cliente") or "").strip() not in clientes_por_nombre and not aco):
            var_cliente_selector.set(OPCION_CLIENTE_OTROS)
            activar_captura_manual(conservar_datos=True)
        else:
            var_cliente_selector.set(str(estado.get("cliente_selector") or var_cliente_selector.get()))
        for clave, variable in ejecucion_vars.items():
            if clave in (estado.get("ejecucion") or {}):
                variable.set(str(estado["ejecucion"].get(clave) or ""))
        try:
            txt_observaciones_iniciales.delete("1.0", "end"); txt_observaciones_iniciales.insert("1.0", str(estado.get("observaciones_iniciales") or ""))
            txt_finales.delete("1.0", "end"); txt_finales.insert("1.0", str(estado.get("observaciones_finales") or ""))
        except Exception:
            pass
        # Recuperar las filas dinámicas SIN crear nuevos registros en Supabase.
        conceptos_guardados = estado.get("conceptos_obra")
        if isinstance(conceptos_guardados, list) and conceptos_guardados:
            while len(conceptos_obra_items) < len(conceptos_guardados):
                agregar_concepto_obra()
            for item, fila in zip(conceptos_obra_items, conceptos_guardados):
                if not isinstance(fila, dict):
                    continue
                if str(fila.get("tipo") or "").upper() == TIPO_CONCEPTO_OTROS:
                    item["tipo"].set(TIPO_CONCEPTO_OTROS)
                    item["cambiar_tipo"](TIPO_CONCEPTO_OTROS, restaurar=True)
                    item["concepto_label"].set(str(fila.get("concepto") or ""))
                    item["unidad"].set(str(fila.get("unidad") or ""))
                    item["cantidad"].set(str(fila.get("cantidad") or "1"))
                    continue
                registro = next((r for r in catalogo_conceptos_obra
                    if str(r.get("id_obra_concepto")) == str(fila.get("id_obra_concepto"))
                    or (str(r.get("obra_partida") or "") == str(fila.get("partida") or "")
                        and str(r.get("obra_concepto") or "") == str(fila.get("concepto") or ""))), None)
                if registro:
                    tipo = str(registro.get("obra_tipo") or "")
                    seleccion = filtrar_conceptos_por_tipo(tipo, catalogo_conceptos_obra)
                    item["tipo"].set(tipo)
                    item["conceptos_tipo"] = seleccion
                    item["widgets"][1].configure(values=[_etiqueta_concepto_obra(r) for r in seleccion])
                    item["cambiar_tipo"](tipo, restaurar=True)
                    item["concepto_label"].set(_etiqueta_concepto_obra(registro))
                    item["registro"] = registro
                    item["unidad"].set(str(registro.get("obra_unidad") or ""))
                item["cantidad"].set(str(fila.get("cantidad") or "1"))
        epp_guardados = estado.get("epp_partidas")
        if isinstance(epp_guardados, list) and epp_guardados:
            for item in epp_items:
                for widget in item.get("widgets", []):
                    widget.destroy()
            epp_items.clear()
            for fila in epp_guardados:
                if isinstance(fila, dict):
                    agregar_epp_obra(fila)
        misc_guardados = estado.get("materiales_miscelaneos")
        if isinstance(misc_guardados, list) and misc_guardados:
            while len(materiales_miscelaneos_items) < len(misc_guardados):
                agregar_material_misc_obra()
            for item, fila in zip(materiales_miscelaneos_items, misc_guardados):
                if not isinstance(fila, dict):
                    continue
                item["material"].set(str(fila.get("material") or ""))
                item["categoria"].set(str(fila.get("categoria") or "Otro"))
                item["requerido"].set(str(fila.get("requerido") or "No"))
                if item["requerido"].get() == "Sí":
                    for widget in item["widgets"][1:4]:
                        try: widget.configure(state="normal")
                        except Exception: pass
                item["cantidad"].set(str(fila.get("cantidad") or ""))
                item["unidad"].set(str(fila.get("unidad") or "Pieza(s)"))
                item["especificacion"].set(str(fila.get("especificacion") or ""))
        canal_guardados = estado.get("canalizacion_partidas")
        if isinstance(canal_guardados, list) and canal_guardados:
            while len(canalizacion_materiales_items) < len(canal_guardados):
                categoria = canal_guardados[len(canalizacion_materiales_items)].get("categoria") or "Tubo"
                agregar_partida_canalizacion_obra(categoria)
            for item, fila in zip(canalizacion_materiales_items, canal_guardados):
                if not isinstance(fila, dict):
                    continue
                item["categoria"].set(str(fila.get("categoria") or "Tubo"))
                item["tipo"].set(str(fila.get("tipo") or ""))
                item["especificacion"].set(str(fila.get("especificacion") or ""))
                item["cantidad"].set(str(fila.get("cantidad") or ""))
                item["unidad"].set(unidad_forzada_canalizacion(item["categoria"].get(), fila.get("unidad")))
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
        if var_desea_notas_cliente.get() == "Sí" and not var_notas_cliente.get().strip():
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
        if modo_manual_cliente["activo"]:
            if not all(v.get().strip() for v in (
                var_cliente, var_direccion, var_sucursal, var_encargado_sucursal,
                var_telefono, var_correo,
            )):
                return False
        # Cada concepto visible requiere datos completos, sea de catálogo o manual.
        if catalogo_conceptos_obra and not conceptos_obra_items:
            return False
        for item in conceptos_obra_items:
            if item["tipo"].get() == TIPO_CONCEPTO_OTROS:
                if not item["concepto_label"].get().strip() or not item["unidad"].get().strip():
                    return False
            elif not (item.get("registro") or {}):
                return False
            try:
                if float(item["cantidad"].get().strip().replace(",", ".")) <= 0:
                    return False
            except (TypeError, ValueError):
                return False
        return True

    def campos_faltantes_obra():
        faltan = []
        def agregar(nombre):
            if nombre and nombre not in faltan:
                faltan.append(nombre)
        for variable in campos_validables:
            if not variable.get().strip():
                agregar(nombres_validables.get(id(variable), "Campo obligatorio"))
        if var_desea_notas_cliente.get() == "Sí" and not var_notas_cliente.get().strip(): agregar("Notas sobre el cliente")
        if var_desea_anotacion_plano.get() == "Sí" and not var_anotacion_plano_base64.get().strip(): agregar("Anotación tipo plano")
        if var_desea_evidencias.get() == "Sí" and not evidencias: agregar("Evidencia fotográfica")
        if var_desea_archivos_adjuntos.get() == "Sí" and total_archivos_obra() == 0: agregar("PDF / planos adjuntos")
        if var_trabajo_alturas.get() == "Sí":
            if not var_sistema_acceso.get().strip(): agregar("Sistema de acceso temporal")
            if not var_altura_trabajo.get().strip(): agregar("Altura")
            if not var_riesgo_trabajo.get().strip(): agregar("Riesgo")
        if not canalizacion_obra_completa(): agregar("Canalización / materiales")
        try:
            if int(var_dias_trabajo.get().strip()) <= 0: agregar("Días de trabajo")
        except (TypeError, ValueError): agregar("Días de trabajo")
        try:
            if int(var_personas_considerar.get().strip()) <= 0: agregar("Personas a considerar")
        except (TypeError, ValueError): agregar("Personas a considerar")
        if var_requiere_epp.get() == "Sí":
            partidas = obtener_epp_obra()
            if not partidas: agregar("Equipo de protección personal")
            for item in partidas:
                try:
                    if float(str(item.get("cantidad") or "0").replace(",", ".")) <= 0: agregar("Cantidad de EPP"); break
                except (TypeError, ValueError): agregar("Cantidad de EPP"); break
        if modo_manual_cliente["activo"]:
            for nombre, variable in (("Cliente", var_cliente), ("Dirección Fiscal", var_direccion),
                ("Sucursal", var_sucursal), ("Encargado de sucursal", var_encargado_sucursal),
                ("Teléfono", var_telefono), ("Correo", var_correo)):
                if not variable.get().strip():
                    agregar(nombre)
        if catalogo_conceptos_obra and not conceptos_obra_items:
            agregar("Conceptos de obra")
        for item in conceptos_obra_items:
            if item["tipo"].get() == TIPO_CONCEPTO_OTROS:
                if not item["concepto_label"].get().strip(): agregar("Partida / concepto manual")
                if not item["unidad"].get().strip(): agregar("Unidad del concepto manual")
            elif not (item.get("registro") or {}):
                agregar("Concepto de obra válido")
            try:
                if float(item["cantidad"].get().strip().replace(",", ".") or 0) <= 0:
                    agregar("Cantidad de concepto de obra")
            except (TypeError, ValueError):
                agregar("Cantidad de concepto de obra")
        return faltan

    def datos_pdf():
        datos = {
            "Folio OBC": var_folio.get(), "Fecha": var_fecha.get(), "¿Deseas agregar notas sobre el cliente?": var_desea_notas_cliente.get(), "Notas sobre el cliente": var_notas_cliente.get().strip() if var_desea_notas_cliente.get() == "Sí" else "No aplica", "ACO": var_aco.get(), "Cliente": var_cliente.get(), "Contacto": var_contacto.get(),
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
        if var_desea_evidencias.get() == "Sí" and not (evidencias or guardado_servidor["fotos"]):
            messagebox.showwarning("Evidencia fotográfica", "Seleccionaste Sí. Agrega al menos una fotografía antes de guardar.")
            return
        if var_desea_archivos_adjuntos.get() == "Sí" and total_archivos_obra() == 0 and not guardado_servidor["archivos"]:
            messagebox.showwarning("Archivos adjuntos", "Seleccionaste Sí. Agrega al menos un PDF o plano antes de guardar.")
            return
        # Guardar un checkpoint cifrado ANTES de cualquier operación de red.
        # Evita perder la captura si falla el INSERT, Storage o la conexión.
        def proteger_captura():
            try:
                from services.levantamiento_borradores_service import guardar_borrador
                guardar_borrador(usuario_activo, "Obra Civil", _snapshot_borrador_obra())
                return True
            except Exception:
                logger.exception("No fue posible respaldar el borrador de Obra Civil.")
                return False

        if not proteger_captura():
            messagebox.showerror(
                "No se pudo respaldar la captura",
                "No se intentó guardar en Supabase porque falló la protección local "
                "del formulario. Conserva esta ventana abierta y contacta a soporte."
            )
            return
        datos = {
            "id_aco": datos_aco.get("id_aco"),
            "id_sucursal": (None if modo_manual_cliente["activo"] else
                            seleccion_catalogo.get("id_sucursal") or datos_aco.get("id_sucursal")),
            "id_contacto": (None if modo_manual_cliente["activo"] else
                            seleccion_catalogo.get("id_contacto") or datos_aco.get("id_contacto")),
            "obc_fecha": var_fecha.get().strip() or None,
            "obc_aco_numero": var_aco.get().strip(),
            "obc_cliente": var_cliente.get().strip(), "obc_contacto": var_contacto.get().strip(), "obc_sucursal": var_sucursal.get().strip(),
            "obc_direccion": var_direccion.get().strip(), "obc_responsable_axia": var_responsable.get().strip(), "obc_supervisor": var_supervisor.get().strip(),
            "obc_dias_trabajo": int(var_dias_trabajo.get().strip()), "obc_personas_considerar": int(var_personas_considerar.get().strip()),
            "obc_tipo_giro": var_tipo_giro.get().strip(), "obc_nombre_proyecto": var_nombre_proyecto.get().strip(),
            "obc_superficie_disponible": var_superficie.get(), "obc_superficie_adecuada": var_superficie_ok.get(), "obc_planos_arquitectonicos": var_planos_arq.get(),
            "obc_requiere_maquinaria": var_maquinaria.get(), "obc_permisos": var_permisos.get(), "obc_observaciones_iniciales": obtener_textbox(txt_observaciones_iniciales),
            "obc_ejecucion_json": json.dumps({
                **{k: v.get() for k, v in ejecucion_vars.items()},
                "_notas_cliente": {"desea_agregar": var_desea_notas_cliente.get(), "notas": var_notas_cliente.get().strip() if var_desea_notas_cliente.get() == "Sí" else ""},
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
        # Subir evidencias ANTES del INSERT evita necesitar un UPDATE en una
        # tabla cuya RLS todavía está pendiente de migración a autenticación
        # de usuarios con tokens del servidor. También preserva los archivos
        # ya subidos entre reintentos y no duplica registros.
        if not guardado_servidor["id"]:
            try:
                from pathlib import Path
                token = guardado_servidor["solicitud"]
                carpeta_carga = "SOLICITUD-" + token
                if var_desea_evidencias.get() == "Sí" and guardado_servidor["fotos"] is None:
                    faltantes = [ruta for ruta in evidencias if not Path(ruta).is_file()]
                    if faltantes:
                        raise FileNotFoundError("No se encontraron estas fotografías: " + ", ".join(faltantes))
                    fotos_subidas = subir_evidencias_obra_civil(carpeta_carga, evidencias)
                    if len(fotos_subidas) != len(evidencias):
                        raise RuntimeError("La subida de fotografías quedó incompleta.")
                    guardado_servidor["fotos"] = fotos_subidas
                    if not proteger_captura():
                        raise RuntimeError("No fue posible respaldar el estado de las fotografías.")
                if var_desea_archivos_adjuntos.get() == "Sí" and archivos_adjuntos and guardado_servidor["archivos"] is None:
                    faltantes = [ruta for ruta in archivos_adjuntos if not Path(ruta).is_file()]
                    if faltantes:
                        raise FileNotFoundError("No se encontraron estos planos/PDF: " + ", ".join(faltantes))
                    archivos_subidos = subir_archivos_obra_civil(carpeta_carga, archivos_adjuntos)
                    if len(archivos_subidos) != len(archivos_adjuntos):
                        raise RuntimeError("La subida de archivos quedó incompleta.")
                    guardado_servidor["archivos"] = archivos_subidos
                    if not proteger_captura():
                        raise RuntimeError("No fue posible respaldar el estado de los archivos.")
            except Exception as error:
                show_operation_error("Captura conservada", "Subir anexos de Obra Civil", error)
                messagebox.showwarning(
                    "Obra Civil no registrada",
                    "El registro NO se ha enviado. La captura se conserva localmente; "
                    "revisa los archivos y la conexión antes de continuar."
                )
                return
            datos["obc_evidencias_json"] = json.dumps(guardado_servidor["fotos"] or [], ensure_ascii=False)
            datos["obc_archivos_adjuntos_json"] = json.dumps(guardado_servidor["archivos"] or [], ensure_ascii=False)
            datos["obc_request_id"] = guardado_servidor["solicitud"]
            resultado = crear_obra_civil(datos)
            if not resultado:
                messagebox.showwarning(
                    "Registro pendiente de verificar",
                    "No pudimos confirmar la operación con Supabase. Los datos y "
                    "el identificador de esta solicitud quedaron en el borrador local. "
                    "Puedes volver a intentar desde ESTE borrador: AXIA verificará "
                    "primero si el registro ya existe para no duplicarlo."
                )
                return
            registro_creado = resultado[0]
            guardado_servidor["id"] = registro_creado["obc_id"]
            guardado_servidor["folio"] = registro_creado["obc_folio"]
            var_folio.set(guardado_servidor["folio"])
            if not proteger_captura():
                messagebox.showwarning(
                    "Obra registrada",
                    "El registro fue creado con folio " + guardado_servidor["folio"] +
                    ". Falló el respaldo de su confirmación en este equipo: "
                    "NO vuelvas a enviar esta obra hasta verificar el registro."
                )
                return

        folio = guardado_servidor["folio"]
        evidencias_subidas = guardado_servidor["fotos"] or []
        archivos_subidos = guardado_servidor["archivos"] or []

        # El PDF se genera DESPUÉS de confirmar el folio entregado por la BD.
        try:
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
        except Exception as error:
            logger.exception("La obra %s se registró, pero el PDF local falló.", folio)
            messagebox.showwarning(
                "Obra registrada; PDF pendiente",
                f"La obra {folio} YA ESTÁ REGISTRADA en Supabase, pero el PDF falló: {error}. "
                "Se conserva el borrador para volver a intentar sin duplicar."
            )
            proteger_captura()
            return
        try:
            from services.levantamiento_borradores_service import eliminar_borrador
            eliminar_borrador(usuario_activo)
        except Exception:
            logger.debug("No fue posible eliminar el borrador de Obra Civil ya guardado.", exc_info=True)
        messagebox.showinfo("Registro correcto", "La obra civil fue registrada correctamente como " + folio + "." + mensaje_pdf)
        # Desregistrar el proveedor de autosave: de lo contrario el ciclo de
        # 45 segundos podría recrear el borrador después de haberlo eliminado.
        try:
            if hasattr(app, "limpiar_proveedor_borrador_levantamiento"):
                app.limpiar_proveedor_borrador_levantamiento()
        except Exception:
            logger.debug("No se pudo desconectar el autoguardado de Obra Civil.", exc_info=True)
        app.mostrar_vista_inicio_aco()

    def _snapshot_borrador_obra():
        estado = {
            "obra_guardada": dict(guardado_servidor),
            "folio": var_folio.get(), "fecha": var_fecha.get(), "desea_notas_cliente": var_desea_notas_cliente.get(), "notas_cliente": var_notas_cliente.get(), "aco": var_aco.get(), "cliente": var_cliente.get(),
            "cliente_manual": modo_manual_cliente["activo"], "cliente_selector": var_cliente_selector.get(),
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
            # Borrador completo: las filas dinámicas no se guardaban anteriormente.
            "conceptos_obra": obtener_conceptos_obra_seleccionados(),
            "epp_partidas": obtener_epp_obra(),
            "materiales_miscelaneos": [
                {"material": fila["material"].get(),
                 "categoria": fila["categoria"].get(),
                 "requerido": fila["requerido"].get(),
                 "cantidad": fila["cantidad"].get(),
                 "unidad": fila["unidad"].get(),
                 "especificacion": fila["especificacion"].get()}
                for fila in materiales_miscelaneos_items
            ],
            "canalizacion_partidas": [
                {"categoria": fila["categoria"].get(),
                 "tipo": fila["tipo"].get(),
                 "especificacion": fila["especificacion"].get(),
                 "cantidad": fila["cantidad"].get(),
                 "unidad": fila["unidad"].get()}
                for fila in canalizacion_materiales_items
            ],
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

    botones = ctk.CTkFrame(contenedor, fg_color="#F4F4F4", height=78, corner_radius=0)
    botones.grid(row=1, column=0, sticky="ew")
    lbl_faltantes = ctk.CTkLabel(botones, text="", font=SMALL_FONT, text_color="#B45309", anchor="center", justify="center", wraplength=1050)
    lbl_faltantes.pack(fill="x", padx=12, pady=(3, 0))
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
