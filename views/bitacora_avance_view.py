from core.error_reporting import show_operation_error
"""Formulario operativo para Bitácoras de Avance."""
from datetime import datetime
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox, filedialog

from core.logger import configurar_logger
from ui.native_combobox import NativeComboBox
from ui.colors import SECONDARY, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, BUTTON_HOVER
from ui.fonts import TEXT_SM, BUTTON_FONT
from app_context import obtener_usuario_actual
from services.movimientos_service import registrar_movimiento
from services.aco_context_service import normalizar_datos_aco
from services.acos_service import buscar_aco_por_numero
from services.folios_service import generar_siguiente_folio
from services.bitacoras_service import (
    crear_bitacora, buscar_bitacora_por_folio, actualizar_bitacora,
    obtener_contextos_aco_disponibles_bitacora,
)
from services.usuarios_service import obtener_nombres_usuarios_por_tipos
from services.sucursales_service import obtener_sucursales_por_cliente, construir_domicilio_sucursal
from services.bitacora_evidencias_service import subir_evidencias_bitacora
from security.permissions import puede_generar_bitacora
from views.formato_helpers import (
    ENTRY_H, OPTION_H, LABEL_FONT, SMALL_FONT, SECTION_FONT,
    obtener_textbox, enfocar_inicio_formulario, generar_pdf_preview,
    generar_pdf_archivo,
)

logger = configurar_logger(__name__)


def mostrar_bitacora_avance(parent, app, aco=None):
    usuario_activo = obtener_usuario_actual()
    if not puede_generar_bitacora(usuario_activo):
        messagebox.showerror("Acceso denegado", "No tienes permisos para generar bitácoras.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=7, pady=5)
    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_rowconfigure(1, weight=0)
    contenedor.grid_columnconfigure(0, weight=1)

    datos_aco = normalizar_datos_aco(aco)
    contexto_ot = {}
    evidencias_locales: list[str] = []

    var_folio = ctk.StringVar(value=generar_siguiente_folio("BIT"))
    var_fecha = ctk.StringVar(value=datetime.now().strftime("%d-%m-%Y"))
    var_aco = ctk.StringVar(value=datos_aco.get("aco_numero", ""))
    var_sucursal = ctk.StringVar()
    var_direccion = ctk.StringVar(value=datos_aco.get("direccion", ""))
    var_cliente = ctk.StringVar(value=datos_aco.get("cliente", ""))
    var_encargado = ctk.StringVar(value=datos_aco.get("jefe_operacion", "") or datos_aco.get("responsable", ""))
    var_hora_llegada = ctk.StringVar()
    var_hora_salida = ctk.StringVar()
    var_tecnico = ctk.StringVar()
    var_tecnico_selector = ctk.StringVar()
    tecnicos_seleccionados = []
    var_estatus = ctk.StringVar(value="En proceso")
    var_porcentaje = ctk.StringVar(value="0")

    contextos = obtener_contextos_aco_disponibles_bitacora()
    contexto_por_aco = {x["aco_numero"]: x for x in contextos}
    sucursales_por_etiqueta = {}
    acos_disponibles = list(contexto_por_aco)
    if var_aco.get() and var_aco.get() not in acos_disponibles:
        acos_disponibles.insert(0, var_aco.get())
    tecnicos = obtener_nombres_usuarios_por_tipos([4])

    card = ctk.CTkScrollableFrame(contenedor, width=1280, fg_color=WHITE, corner_radius=18)
    card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
    form = ctk.CTkFrame(card, fg_color="transparent")
    form.pack(fill="x", expand=True, padx=12, pady=(9, 4))
    # Retícula de 6 columnas para aprovechar todo el ancho de la pantalla.
    # Permite ordenar los campos en una sola línea como el formato operativo.
    for col in range(6):
        form.grid_columnconfigure(col, weight=1, uniform="form_cols")

    def seccion(texto, fila):
        ctk.CTkLabel(form, text=texto, font=SECTION_FONT, text_color=TEXT_PRIMARY).grid(
            row=fila, column=0, columnspan=6, sticky="w", pady=(6, 3))

    def label(frame, texto):
        ctk.CTkLabel(frame, text=texto, font=LABEL_FONT, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 1))

    def celda(fila, col, colspan=1):
        frame = ctk.CTkFrame(form, fg_color="transparent")
        left = 0 if col == 0 else 5
        right = 0 if col + colspan >= 6 else 5
        frame.grid(row=fila, column=col, columnspan=colspan, sticky="ew",
                   padx=(left, right), pady=(0, 3))
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def entry(texto, var, placeholder="", fila=0, col=0, state="normal", colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        e = ctk.CTkEntry(c, textvariable=var, placeholder_text=placeholder,
                         height=ENTRY_H, corner_radius=8, font=SMALL_FONT, state=state)
        e.pack(fill="x")
        return e

    def option(texto, var, values, fila=0, col=0, command=None, state="normal", colspan=1):
        c = celda(fila, col, colspan)
        label(c, texto)
        cb = NativeComboBox(c, variable=var, values=values or ["Sin registros disponibles"],
                            height=OPTION_H, font=SMALL_FONT, command=command, state=state)
        cb.pack(fill="x")
        return cb

    def texto_largo(texto, fila, alto=100):
        c = celda(fila, 0, 6)
        label(c, texto)
        box = ctk.CTkTextbox(c, height=alto, corner_radius=8, font=SMALL_FONT)
        box.pack(fill="x")
        return box

    def _etiqueta_sucursal(sucursal):
        nombre = str(sucursal.get("suc_nombre") or "Sucursal").strip()
        domicilio = construir_domicilio_sucursal(sucursal)
        return f"{nombre} — {domicilio}" if domicilio else nombre

    def cargar_sucursal(etiqueta=None):
        etiqueta = str(etiqueta or var_sucursal.get() or "").strip()
        sucursal = sucursales_por_etiqueta.get(etiqueta)
        if not sucursal:
            var_direccion.set("")
            validar_preview()
            return
        var_sucursal.set(etiqueta)
        var_direccion.set(construir_domicilio_sucursal(sucursal))
        validar_preview()

    def refrescar_sucursales_cliente():
        sucursales_por_etiqueta.clear()
        id_cliente = datos_aco.get("id_cliente")
        sucursales = obtener_sucursales_por_cliente(id_cliente) if id_cliente else []
        for sucursal in sucursales:
            etiqueta = _etiqueta_sucursal(sucursal)
            # Evita colisiones visuales si dos sucursales tienen el mismo nombre.
            if etiqueta in sucursales_por_etiqueta:
                sid = sucursal.get("suc_id") or sucursal.get("id_sucursal")
                etiqueta = f"{etiqueta} [{sid}]"
            sucursales_por_etiqueta[etiqueta] = sucursal

        valores = list(sucursales_por_etiqueta)
        combo_sucursal.configure(values=valores or ["Sin sucursales registradas"], state="normal" if valores else "disabled")
        id_sucursal_aco = datos_aco.get("id_sucursal")
        seleccion = ""
        if id_sucursal_aco:
            for etiqueta, sucursal in sucursales_por_etiqueta.items():
                sid = sucursal.get("suc_id") or sucursal.get("id_sucursal")
                if str(sid) == str(id_sucursal_aco):
                    seleccion = etiqueta
                    break
        if not seleccion and len(valores) == 1:
            seleccion = valores[0]
        if seleccion:
            var_sucursal.set(seleccion)
            cargar_sucursal(seleccion)
        else:
            var_sucursal.set(valores[0] if len(valores) == 1 else ("Selecciona sucursal" if valores else "Sin sucursales registradas"))
            if len(valores) != 1:
                var_direccion.set("")

    def cargar_aco(numero=None):
        nonlocal datos_aco, contexto_ot
        numero = str(numero or var_aco.get() or "").strip().upper()
        if not numero or numero == "Sin ACOs disponibles":
            return
        registro = buscar_aco_por_numero(numero)
        if not registro:
            messagebox.showwarning("ACO no encontrado", "No se encontró información para el ACO seleccionado.")
            return
        datos_aco = normalizar_datos_aco(registro)
        contexto_ot = contexto_por_aco.get(numero, {})
        var_aco.set(numero)
        var_cliente.set(datos_aco.get("cliente", ""))
        var_encargado.set(datos_aco.get("jefe_operacion", "") or datos_aco.get("responsable", ""))
        refrescar_sucursales_cliente()
        validar_preview()

    seccion("Bitácora de Avance", 0)
    # Primera línea: todos los datos de identificación, como en la maqueta aprobada.
    entry("Folio de bitácora", var_folio, "Automático", 1, 0, state="disabled")
    entry("Fecha", var_fecha, "DD-MM-AAAA", 1, 1, state="disabled")
    option("Número de ACO", var_aco, acos_disponibles, 1, 2, command=cargar_aco,
           state="normal" if acos_disponibles else "disabled")
    entry("Nombre del Cliente", var_cliente, "Autollenado por ACO", 1, 3, state="disabled")
    combo_sucursal = option("Sucursal operativa", var_sucursal, ["Selecciona un ACO primero"], 1, 4,
                            command=cargar_sucursal, state="disabled")
    entry("Nombre del encargado del proyecto", var_encargado, "Autollenado por ACO", 1, 5, state="disabled")

    # Segunda línea: dirección amplia y horarios.
    entry("Dirección de la sucursal", var_direccion, "Autollenado por sucursal", 2, 0, state="disabled", colspan=3)
    entry("Hora de Llegada", var_hora_llegada, "HH:MM", 2, 3)
    entry("Hora de Salida", var_hora_salida, "HH:MM", 2, 4)

    # Tercera línea: operación y avance. Se mantiene compacta y alineada a la izquierda
    # para dejar libre el resto de la pantalla, como en la maqueta operativa.
    fila_operativa = ctk.CTkFrame(form, fg_color="transparent")
    fila_operativa.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(0, 3))
    fila_operativa.grid_columnconfigure(0, weight=3)  # Técnico: el más ancho de los tres
    fila_operativa.grid_columnconfigure(1, weight=1)  # Estatus: compacto
    fila_operativa.grid_columnconfigure(2, weight=1)  # Porcentaje: compacto
    fila_operativa.grid_columnconfigure(3, weight=5)  # Espacio libre a la derecha

    def campo_operativo(texto, columna):
        c = ctk.CTkFrame(fila_operativa, fg_color="transparent")
        c.grid(row=0, column=columna, sticky="ew", padx=(0 if columna == 0 else 5, 5))
        c.grid_columnconfigure(0, weight=1)
        label(c, texto)
        return c

    c_tecnico = campo_operativo("Técnico en sitio", 0)
    tecnico_linea = ctk.CTkFrame(c_tecnico, fg_color="transparent")
    tecnico_linea.pack(fill="x")
    combo_tecnico = NativeComboBox(
        tecnico_linea, variable=var_tecnico_selector, values=tecnicos or ["Sin técnicos tipo 4 registrados"],
        height=OPTION_H, font=SMALL_FONT, state="normal" if tecnicos else "disabled"
    )
    combo_tecnico.pack(side="left", fill="x", expand=True, padx=(0,4))
    def agregar_tecnico():
        nombre = var_tecnico_selector.get().strip()
        if nombre and nombre in tecnicos and nombre not in tecnicos_seleccionados:
            tecnicos_seleccionados.append(nombre)
            var_tecnico.set(" | ".join(tecnicos_seleccionados))
            validar_preview()
    def quitar_ultimo_tecnico():
        if tecnicos_seleccionados:
            tecnicos_seleccionados.pop()
            var_tecnico.set(" | ".join(tecnicos_seleccionados))
            validar_preview()
    ctk.CTkButton(tecnico_linea, text="+", width=34, height=30, fg_color=SECONDARY, hover_color=BUTTON_HOVER, command=agregar_tecnico).pack(side="left", padx=2)
    ctk.CTkButton(tecnico_linea, text="−", width=34, height=30, fg_color="#DC2626", hover_color="#B91C1C", command=quitar_ultimo_tecnico).pack(side="left", padx=2)
    ctk.CTkLabel(c_tecnico, textvariable=var_tecnico, font=SMALL_FONT, text_color=TEXT_SECONDARY, anchor="w", justify="left").pack(fill="x", pady=(2,0))

    c_estatus = campo_operativo("Estatus", 1)
    combo_estatus = NativeComboBox(
        c_estatus, variable=var_estatus, values=["Pendiente", "En proceso", "Finalizada"],
        height=OPTION_H, font=SMALL_FONT
    )
    combo_estatus.pack(fill="x")

    c_porcentaje = campo_operativo("Porcentaje de avance", 2)
    entry_porcentaje = ctk.CTkEntry(
        c_porcentaje, textvariable=var_porcentaje, placeholder_text="0 - 100",
        height=ENTRY_H, corner_radius=8, font=SMALL_FONT
    )
    entry_porcentaje.pack(fill="x")
    lbl_avance = ctk.CTkLabel(form, text="0% de avance", font=SMALL_FONT, text_color=TEXT_SECONDARY)

    # Evidencias fotográficas reemplazan al antiguo campo Observaciones.
    c_evid = celda(4, 0, 6)
    label(c_evid, "Evidencias fotográficas")
    lbl_evidencias = ctk.CTkLabel(c_evid, text="Sin fotografías agregadas", font=SMALL_FONT,
                                  text_color=TEXT_SECONDARY, anchor="w", justify="left")
    lbl_evidencias.pack(fill="x", pady=(0, 4))

    def refrescar_evidencias():
        if not evidencias_locales:
            texto = "Sin fotografías agregadas"
        else:
            nombres = [Path(x).name for x in evidencias_locales]
            muestra = ", ".join(nombres[:4])
            if len(nombres) > 4:
                muestra += f" y {len(nombres)-4} más"
            texto = f"{len(nombres)} fotografía(s): {muestra}"
        lbl_evidencias.configure(text=texto)
        validar_preview()

    def agregar_fotos():
        rutas = filedialog.askopenfilenames(
            title="Agregar fotografías a la bitácora",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp"), ("Todos", "*.*")],
        )
        for ruta in rutas:
            if ruta not in evidencias_locales:
                evidencias_locales.append(ruta)
        refrescar_evidencias()

    def quitar_ultima_foto():
        if evidencias_locales:
            evidencias_locales.pop()
        refrescar_evidencias()

    acciones = ctk.CTkFrame(c_evid, fg_color="transparent")
    acciones.pack(anchor="w")
    ctk.CTkButton(acciones, text="+ Agregar fotos", width=150, height=30, fg_color=SECONDARY,
                  hover_color=BUTTON_HOVER, command=agregar_fotos).pack(side="left", padx=(0, 5))
    ctk.CTkButton(acciones, text="Eliminar última", width=135, height=30, fg_color="#DC2626",
                  hover_color="#B91C1C", command=quitar_ultima_foto).pack(side="left")

    txt_descripcion = texto_largo("Descripción", 5, 110)

    def porcentaje_valido(mostrar=False):
        raw = var_porcentaje.get().strip()
        try:
            valor = int(raw)
        except ValueError:
            if mostrar:
                messagebox.showwarning("Porcentaje", "El porcentaje de avance debe ser un número entero entre 0 y 100.")
            return None
        if not 0 <= valor <= 100:
            if mostrar:
                messagebox.showwarning("Porcentaje", "El porcentaje de avance debe estar entre 0 y 100.")
            return None
        return valor

    def al_cambiar_porcentaje(*_):
        pct = porcentaje_valido(False)
        lbl_avance.configure(text=f"{pct}% de avance" if pct is not None else "Porcentaje inválido")
        if pct == 100:
            var_estatus.set("Finalizada")
        elif pct is not None and pct > 0 and var_estatus.get() == "Pendiente":
            var_estatus.set("En proceso")
        validar_preview()

    var_porcentaje.trace_add("write", al_cambiar_porcentaje)

    def convertir_estatus(texto):
        return {"Pendiente": 1, "En proceso": 2, "Finalizada": 3}.get(texto, 2)

    def formulario_completo():
        pct = porcentaje_valido(False)
        return bool(
            var_folio.get().strip() and var_fecha.get().strip() and var_aco.get().strip()
            and var_sucursal.get().strip() in sucursales_por_etiqueta
            and var_direccion.get().strip() and var_cliente.get().strip() and var_encargado.get().strip()
            and var_hora_llegada.get().strip() and var_hora_salida.get().strip() and var_tecnico.get().strip()
            and pct is not None and obtener_textbox(txt_descripcion)
        )

    def datos_pdf(evidencias=None):
        pct = porcentaje_valido(False)
        fotos_pdf = evidencias if evidencias is not None else list(evidencias_locales)
        return {
            "Folio Bitácora": var_folio.get(),
            "Fecha": var_fecha.get(),
            "Número de ACO": var_aco.get(),
            "Levantamiento": contexto_ot.get("ot_folio_levantamiento") or "",
            "OT": contexto_ot.get("ot_folio") or "",
            "Cliente": var_cliente.get(),
            "Dirección de Servicio": var_direccion.get(),
            "Nombre del Encargado": var_encargado.get(),
            "Hora de Llegada": var_hora_llegada.get(),
            "Hora de Salida": var_hora_salida.get(),
            "Técnico(s)": var_tecnico.get(),
            "Porcentaje de Avance": f"{pct}%" if pct is not None else "",
            "Descripción del Servicio": obtener_textbox(txt_descripcion),
            "Evidencia Fotográfica": fotos_pdf,
        }

    def preview_pdf():
        if not formulario_completo():
            messagebox.showwarning("Preview", "Completa los campos obligatorios y captura un porcentaje válido.")
            return
        generar_pdf_preview("Bitácora de Avance", datos_pdf())

    def validar_preview():
        try:
            btn_preview.configure(state="normal" if formulario_completo() else "disabled")
        except Exception:
            logger.debug("Validación de preview antes de construir botón.", exc_info=True)

    for v in [var_folio, var_fecha, var_aco, var_sucursal, var_direccion, var_cliente, var_encargado,
              var_hora_llegada, var_hora_salida, var_tecnico, var_estatus]:
        v.trace_add("write", lambda *_: validar_preview())
    txt_descripcion.bind("<KeyRelease>", lambda _event: validar_preview())

    def guardar_bitacora():
        nonlocal contexto_ot
        folio = var_folio.get().strip()
        pct = porcentaje_valido(True)
        if pct is None or not formulario_completo():
            messagebox.showwarning("Campos obligatorios", "Completa todos los campos obligatorios de la bitácora.")
            return
        if buscar_bitacora_por_folio(folio):
            folio = generar_siguiente_folio("BIT")
            var_folio.set(folio)
        contexto_ot = contexto_ot or contexto_por_aco.get(var_aco.get().strip().upper(), {})
        sucursal_seleccionada = sucursales_por_etiqueta.get(var_sucursal.get().strip()) or {}
        id_sucursal_seleccionada = sucursal_seleccionada.get("suc_id") or sucursal_seleccionada.get("id_sucursal")
        datos = {
            "id_aco": datos_aco.get("id_aco"),
            "id_sucursal": id_sucursal_seleccionada,
            "id_contacto": datos_aco.get("id_contacto"),
            "ot_id": contexto_ot.get("ot_id"),
            "bit_ot_folio": contexto_ot.get("ot_folio"),
            "bit_folio": folio,
            "bit_fecha": var_fecha.get().strip(),
            "bit_aco_numero": var_aco.get().strip().upper(),
            "bit_direccion_sucursal": var_direccion.get().strip(),
            "bit_cliente": var_cliente.get().strip(),
            "bit_encargado_proyecto_axia": var_encargado.get().strip(),
            "bit_hora_llegada": var_hora_llegada.get().strip(),
            "bit_hora_salida": var_hora_salida.get().strip(),
            "bit_observaciones": "",
            "bit_tecnico": var_tecnico.get().strip(),
            "bit_tecnico_sitio": var_tecnico.get().strip(),
            "bit_descripcion": obtener_textbox(txt_descripcion),
            "bit_estatus": convertir_estatus(var_estatus.get()),
            "bit_porcentaje_avance": pct,
            "bit_fotos": [],
            "creado_por": usuario_activo.get("usuario"),
        }
        resultado = crear_bitacora(datos)
        if not resultado:
            show_operation_error("Error al guardar", "Registrar bitácora operativa")
            return

        registro = resultado[0] if isinstance(resultado, list) and resultado else {}
        id_bitacora = registro.get("id_bitacora") or (buscar_bitacora_por_folio(folio) or {}).get("id_bitacora")
        fotos_subidas = []
        aviso_fotos = ""
        if evidencias_locales:
            try:
                fotos_subidas = subir_evidencias_bitacora(folio, evidencias_locales)
                if id_bitacora and fotos_subidas:
                    actualizar_bitacora(id_bitacora, {"bit_fotos": fotos_subidas})
            except Exception as error:
                logger.exception("La bitácora se guardó, pero falló la carga de fotografías.")
                aviso_fotos = f"\n\nLa bitácora fue guardada, pero no se pudieron subir todas las fotografías:\n{error}"

        registrar_movimiento(modulo="Bitácoras", accion="CREAR",
                             descripcion=f"El usuario creó la bitácora {folio} ({pct}% avance)", registro_afectado=folio)
        evidencias_pdf = fotos_subidas if fotos_subidas else list(evidencias_locales)
        ruta_pdf = generar_pdf_archivo("Bitácora de Avance", datos_pdf(evidencias_pdf), nombre_archivo=folio, subcarpeta="bitacoras")
        mensaje_pdf = f"\n\nPDF guardado en:\n{ruta_pdf}" if ruta_pdf else "\n\nNo se pudo guardar el PDF local."
        messagebox.showinfo("Registro correcto", "La bitácora fue registrada correctamente." + mensaje_pdf + aviso_fotos)
        app.mostrar_vista_inicio_aco()

    if var_aco.get():
        cargar_aco(var_aco.get())

    botones = ctk.CTkFrame(contenedor, fg_color="#F4F4F4", height=58, corner_radius=0)
    botones.grid(row=1, column=0, sticky="ew")
    barra = ctk.CTkFrame(botones, fg_color="transparent")
    barra.pack(anchor="center", pady=4)
    ctk.CTkButton(barra, text="⬅ Atrás", width=120, height=38, corner_radius=10,
                  fg_color="#64748B", hover_color="#475569", font=BUTTON_FONT,
                  command=app.volver_atras).grid(row=0, column=0, padx=4)
    ctk.CTkButton(barra, text="💾 Guardar Bitácora", width=190, height=38, corner_radius=10,
                  fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT,
                  command=guardar_bitacora).grid(row=0, column=1, padx=4)
    btn_preview = ctk.CTkButton(barra, text="👁 Preview PDF", width=165, height=38, corner_radius=10,
                                fg_color="#1F4E79", hover_color="#173B5C", font=BUTTON_FONT,
                                command=preview_pdf, state="disabled")
    btn_preview.grid(row=0, column=2, padx=4)
    ctk.CTkButton(barra, text="↩ Cancelar", width=130, height=38, corner_radius=10,
                  fg_color="gray", font=BUTTON_FONT,
                  command=app.mostrar_vista_inicio_aco).grid(row=0, column=3, padx=4)

    enfocar_inicio_formulario(card)
    validar_preview()
