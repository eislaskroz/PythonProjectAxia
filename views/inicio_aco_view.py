"""
=========================================================
MÓDULO: inicio_aco_view.py
DESCRIPCIÓN:
Vista dinámica inicial posterior al login.

Permite:
- Validar un ACO existente
- Crear un nuevo ACO
- Enviar al usuario al flujo operativo correspondiente
=========================================================
"""

import customtkinter as ctk
from tkinter import messagebox
from core.background_tasks import run_async

from ui.colors import (
    PRIMARY,
    SECONDARY,
    WHITE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    BUTTON_HOVER
)

from ui.date_picker import abrir_selector_fecha
from ui.fonts import (
    TITLE_MD,
    TEXT_MD,
    TEXT_SM,
    BUTTON_FONT
)

from app_context import obtener_usuario_actual

from services.acos_service import (
    buscar_aco_por_numero,
    crear_aco
)
from services.clientes_service import buscar_clientes, construir_direccion_cliente
from services.sucursales_service import (
    obtener_sucursales_por_cliente,
    obtener_contactos_por_sucursal,
    construir_domicilio_sucursal,
)

from services.movimientos_service import registrar_movimiento

from security.permissions import (
    puede_crear_aco,
    puede_generar_levantamiento,
    puede_generar_orden,
    puede_generar_bitacora
)


def limpiar_frame(frame):
    """
    Elimina todos los widgets dentro de un frame.
    """

    for widget in frame.winfo_children():
        widget.destroy()


def normalizar_aco_visual(variable):
    """Mantiene el número de ACO en mayúsculas mientras se captura."""

    valor = variable.get()
    valor_mayusculas = valor.upper()
    if valor != valor_mayusculas:
        variable.set(valor_mayusculas)


def mostrar_inicio_aco(parent, app, aco_validado=None):
    """
    Construye la vista principal del flujo ACO.

    Args:
        aco_validado:
            Registro ACO opcional. Si llega informado, se muestra directamente
            la pantalla de selección de formulario sin repetir la validación.
    """

    registrar_movimiento(
        modulo="ACO",
        accion="CONSULTAR",
        descripcion="El usuario abrió la vista inicial de ACO"
    )

    # =================================================
    # PANEL SUPERIOR DERECHO
    # =================================================

    panel_superior = ctk.CTkFrame(
        parent,
        width=620,
        height=135,
        fg_color="transparent"
    )
    panel_superior.place(
        relx=0.98,
        y=10,
        anchor="ne"
    )
    panel_superior.pack_propagate(False)

    ctk.CTkLabel(
        panel_superior,
        text="¿Tienes ACO asignado?",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY
    ).pack(
        pady=(5, 4)
    )

    ctk.CTkLabel(
        panel_superior,
        text="El ACO conecta levantamientos, órdenes de servicio y bitácoras operativas.",
        font=TEXT_MD,
        text_color=TEXT_SECONDARY,
        justify="center"
    ).pack(
        pady=(0, 10)
    )

    frame_botones = ctk.CTkFrame(
        panel_superior,
        fg_color="transparent"
    )
    frame_botones.pack()

    # =================================================
    # PANEL DINÁMICO PRINCIPAL
    # =================================================

    panel_dinamico = ctk.CTkFrame(
        parent,
        fg_color=WHITE,
        corner_radius=22
    )
    panel_dinamico.pack(
        fill="both",
        expand=True,
        padx=35,
        pady=(160, 25)
    )

    # =================================================
    # MENSAJE INICIAL
    # =================================================

    def mostrar_mensaje_inicial():
        """
        Muestra el mensaje inicial del panel dinámico.
        """

        limpiar_frame(panel_dinamico)

        ctk.CTkLabel(
            panel_dinamico,
            text="Selecciona una opción para comenzar.",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY
        ).pack(
            pady=220
        )

    # =================================================
    # BUSCAR ACO
    # =================================================

    def mostrar_busqueda_aco():
        """
        Muestra formulario para validar un ACO existente.
        """

        limpiar_frame(panel_dinamico)

        ctk.CTkLabel(
            panel_dinamico,
            text="Captura el número de ACO",
            font=TITLE_MD,
            text_color=TEXT_PRIMARY
        ).pack(
            pady=(35, 8)
        )

        var_aco = ctk.StringVar()

        var_aco.trace_add("write", lambda *_: normalizar_aco_visual(var_aco))

        seleccion_operativa = {
            "clientes_por_nombre": {},
            "sucursales_por_nombre": {},
            "contactos_por_nombre": {},
            "selector_sucursal": None,
            "selector_contacto": None,
        }

        entry_aco = ctk.CTkEntry(
            panel_dinamico,
            textvariable=var_aco,
            width=360,
            height=42,
            corner_radius=12,
            placeholder_text="Ejemplo: ACO-0001"
        )
        entry_aco.pack(
            pady=(5, 15)
        )

        def validar_aco():
            """
            Valida el ACO capturado contra Supabase.
            """

            numero_aco = var_aco.get().strip().upper()
            var_aco.set(numero_aco)

            if not numero_aco:
                messagebox.showwarning(
                    "Campo requerido",
                    "Debes capturar el número de ACO."
                )
                return

            def manejar_resultado(aco):
                if not aco:
                    messagebox.showerror(
                        "ACO no encontrado",
                        "No se encontró ningún ACO con ese número."
                    )
                    return

                registrar_movimiento(
                    modulo="ACO",
                    accion="VALIDAR",
                    descripcion=f"El usuario validó el ACO {numero_aco}",
                    registro_afectado=numero_aco
                )

                mostrar_opciones_con_aco(aco)

            run_async(
                root=panel_dinamico.winfo_toplevel(),
                task=lambda: buscar_aco_por_numero(numero_aco),
                on_success=manejar_resultado,
                on_error=lambda error: messagebox.showerror("Error", f"No fue posible validar el ACO.\n\n{error}")
            )

        entry_aco.bind("<Return>", lambda _event: validar_aco())
        entry_aco.focus_set()

        ctk.CTkButton(
            panel_dinamico,
            text="Validar ACO",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=SECONDARY,
            hover_color=BUTTON_HOVER,
            font=BUTTON_FONT,
            command=validar_aco
        ).pack(
            pady=8
        )

    # =================================================
    # OPCIONES CON ACO VALIDADO
    # =================================================
    def mostrar_opciones_con_aco(aco):
        """
        Muestra las opciones operativas disponibles
        después de validar correctamente un ACO.

        REGLA OPERATIVA:
            - ADMIN / usu_tipo = 1:
                Puede generar levantamiento, orden de servicio,
                orden de trabajo y bitácora operativa.

            - TÉCNICO / otros tipos:
                Solo puede generar orden de servicio, orden de trabajo
                o bitácora operativa de avance.
        """

        limpiar_frame(panel_dinamico)

        # =================================================
        # OBTENER DATOS DEL ACO
        # =================================================

        numero_aco = aco.get("aco_numero", "")
        cliente = aco.get("aco_cliente", "")

        # =================================================
        # OBTENER USUARIO ACTIVO
        # =================================================

        usuario_activo = obtener_usuario_actual()
        usu_tipo = usuario_activo.get("usu_tipo", 3)

        # =================================================
        # ENCABEZADO DE CONFIRMACIÓN
        # =================================================

        ctk.CTkLabel(
            panel_dinamico,
            text=f"ACO validado: {numero_aco}",
            font=TITLE_MD,
            text_color=PRIMARY
        ).pack(
            pady=(45, 5)
        )

        ctk.CTkLabel(
            panel_dinamico,
            text=f"Cliente: {cliente}",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY
        ).pack(
            pady=(0, 8)
        )

        ctk.CTkLabel(
            panel_dinamico,
            text="Selecciona la operación que deseas realizar:",
            font=TEXT_MD,
            text_color=TEXT_PRIMARY
        ).pack(
            pady=(0, 25)
        )

        # =================================================
        # OPCIONES SEGÚN TIPO DE USUARIO
        # =================================================

        opciones = []

        # =================================================
        # LEVANTAMIENTOS
        # =================================================
        # Tanto administrativos como técnicos pueden
        # generar levantamientos operativos.

        opciones = []

        if puede_generar_levantamiento(usuario_activo):
            opciones.append(
                (
                    "Generar Levantamiento",
                    lambda: app.mostrar_vista_selector_levantamiento(aco)
                )
            )

        if puede_generar_orden(usuario_activo):
            opciones.append(
                (
                    "Generar Orden de Servicio",
                    lambda: app.mostrar_vista_orden_servicio(aco)
                )
            )

            opciones.append(
                (
                    "Generar Orden de Trabajo",
                    lambda: app.mostrar_vista_orden_trabajo(aco)
                )
            )

        if puede_generar_bitacora(usuario_activo):
            opciones.append(
                (
                    "Bitácora Operativa de Avance",
                    lambda: app.mostrar_vista_bitacora_avance(aco)
                )
            )

        # =================================================
        # RENDERIZAR BOTONES
        # =================================================

        for texto, comando in opciones:
            ctk.CTkButton(
                panel_dinamico,
                text=texto,
                width=340,
                height=46,
                corner_radius=12,
                fg_color=SECONDARY,
                hover_color=BUTTON_HOVER,
                font=BUTTON_FONT,
                command=comando
            ).pack(
                pady=8
            )

    # =================================================
    # CREAR ACO
    # =================================================

    def mostrar_formulario_crear_aco():
        """
        Muestra formulario para crear un nuevo ACO.
        """

        limpiar_frame(panel_dinamico)

        usuario_activo = obtener_usuario_actual()

        form = ctk.CTkScrollableFrame(
            panel_dinamico,
            width=720,
            height=430,
            fg_color="#f1f5f9",
            corner_radius=16
        )
        form.pack(
            pady=25
        )

        var_aco = ctk.StringVar()
        var_cliente = ctk.StringVar()
        var_sucursal = ctk.StringVar()
        var_contacto_operativo = ctk.StringVar()
        var_cliente_domicilio = ctk.StringVar()
        var_sucursal_domicilio = ctk.StringVar()
        var_contacto_telefono = ctk.StringVar()
        var_contacto_correo = ctk.StringVar()
        var_cliente_telefono = ctk.StringVar()
        var_cliente_correo = ctk.StringVar()
        var_responsable = ctk.StringVar()
        var_fecha_inicio = ctk.StringVar()
        var_fecha_compromiso = ctk.StringVar()

        var_aco.trace_add("write", lambda *_: normalizar_aco_visual(var_aco))

        seleccion_operativa = {
            "clientes_por_nombre": {},
            "sucursales_por_nombre": {},
            "contactos_por_nombre": {},
            "selector_sucursal": None,
            "selector_contacto": None,
        }

        def crear_label(texto):
            ctk.CTkLabel(
                form,
                text=texto,
                font=TEXT_SM,
                text_color=TEXT_PRIMARY
            ).pack(
                anchor="w",
                padx=35,
                pady=(10, 3)
            )

        def crear_entry(variable, placeholder, state="normal", date=False):
            entry = ctk.CTkEntry(
                form,
                textvariable=variable,
                width=620,
                height=38,
                corner_radius=10,
                placeholder_text=placeholder,
                state=state
            )
            entry.pack(
                padx=35,
                pady=(0, 4)
            )
            if date and state != "disabled":
                entry.bind("<Button-1>", lambda _event: abrir_selector_fecha(form, variable))
                entry.bind("<FocusIn>", lambda _event: abrir_selector_fecha(form, variable))
            return entry

        def crear_selector_cliente(variable):
            clientes = buscar_clientes("", limite=500) or []
            clientes_por_nombre = {}
            for cliente_db in clientes:
                nombre = str(cliente_db.get("cli_razonsocial", "") or "").strip()
                if nombre:
                    clientes_por_nombre[nombre] = cliente_db

            seleccion_operativa["clientes_por_nombre"] = clientes_por_nombre
            nombres = sorted(clientes_por_nombre.keys()) or ["Sin clientes registrados"]
            variable.set(nombres[0])

            selector = ctk.CTkOptionMenu(
                form,
                variable=variable,
                values=nombres,
                width=620,
                height=38,
                command=lambda _nombre: cargar_datos_cliente()
            )
            selector.pack(
                padx=35,
                pady=(0, 4)
            )
            return clientes_por_nombre

        def refrescar_sucursales(cliente_db):
            id_cliente = cliente_db.get("id_cliente") if cliente_db else None
            sucursales = obtener_sucursales_por_cliente(id_cliente) if id_cliente else []
            sucursales_por_nombre = {
                str(s.get("suc_nombre", "") or "").strip(): s
                for s in sucursales
                if str(s.get("suc_nombre", "") or "").strip()
            }
            seleccion_operativa["sucursales_por_nombre"] = sucursales_por_nombre
            nombres = sorted(sucursales_por_nombre.keys()) or ["Sin sucursales registradas"]
            var_sucursal.set(nombres[0])
            if seleccion_operativa.get("selector_sucursal"):
                seleccion_operativa["selector_sucursal"].configure(values=nombres)
            cargar_datos_sucursal()

        def refrescar_contactos(sucursal_db):
            suc_id = sucursal_db.get("suc_id") if sucursal_db else None
            contactos = obtener_contactos_por_sucursal(suc_id) if suc_id else []
            contactos_por_nombre = {
                str(c.get("con_nombre", "") or "").strip(): c
                for c in contactos
                if str(c.get("con_nombre", "") or "").strip()
            }
            seleccion_operativa["contactos_por_nombre"] = contactos_por_nombre
            nombres = sorted(contactos_por_nombre.keys()) or ["Sin contactos registrados"]
            var_contacto_operativo.set(nombres[0])
            if seleccion_operativa.get("selector_contacto"):
                seleccion_operativa["selector_contacto"].configure(values=nombres)
            cargar_datos_contacto()

        def cargar_datos_cliente():
            cliente_db = seleccion_operativa["clientes_por_nombre"].get(var_cliente.get())
            if not cliente_db:
                var_cliente_domicilio.set("")
                var_cliente_telefono.set("")
                var_cliente_correo.set("")
                refrescar_sucursales(None)
                return
            var_cliente_domicilio.set(construir_direccion_cliente(cliente_db))
            var_cliente_telefono.set(cliente_db.get("cli_telefono", "") or "")
            var_cliente_correo.set(cliente_db.get("cli_correo", "") or "")
            refrescar_sucursales(cliente_db)

        def cargar_datos_sucursal():
            sucursal_db = seleccion_operativa["sucursales_por_nombre"].get(var_sucursal.get())
            if not sucursal_db:
                var_sucursal_domicilio.set("")
                refrescar_contactos(None)
                return
            var_sucursal_domicilio.set(construir_domicilio_sucursal(sucursal_db))
            refrescar_contactos(sucursal_db)

        def cargar_datos_contacto():
            contacto_db = seleccion_operativa["contactos_por_nombre"].get(var_contacto_operativo.get())
            if not contacto_db:
                var_contacto_telefono.set("")
                var_contacto_correo.set("")
                return
            var_contacto_telefono.set(contacto_db.get("con_telefono", "") or "")
            var_contacto_correo.set(contacto_db.get("con_correo", "") or "")

        def crear_selector_sucursal(variable):
            selector = ctk.CTkOptionMenu(
                form, variable=variable, values=["Sin sucursales registradas"],
                width=620, height=38, command=lambda _nombre: cargar_datos_sucursal()
            )
            selector.pack(padx=35, pady=(0, 4))
            seleccion_operativa["selector_sucursal"] = selector
            return selector

        def crear_selector_contacto(variable):
            selector = ctk.CTkOptionMenu(
                form, variable=variable, values=["Sin contactos registrados"],
                width=620, height=38, command=lambda _nombre: cargar_datos_contacto()
            )
            selector.pack(padx=35, pady=(0, 4))
            seleccion_operativa["selector_contacto"] = selector
            return selector

        crear_label("Número de ACO")
        entry_numero_aco = crear_entry(var_aco, "Ejemplo: ACO-0001")

        crear_label("Cliente")
        clientes_por_nombre = crear_selector_cliente(var_cliente)

        crear_label("Sucursal operativa")
        crear_selector_sucursal(var_sucursal)

        crear_label("Contacto de sucursal")
        crear_selector_contacto(var_contacto_operativo)

        crear_label("Domicilio fiscal del cliente")
        crear_entry(var_cliente_domicilio, "Autollenado desde cliente", state="disabled")

        crear_label("Domicilio de sucursal")
        crear_entry(var_sucursal_domicilio, "Autollenado desde sucursal", state="disabled")

        crear_label("Teléfono de contacto")
        crear_entry(var_contacto_telefono, "Autollenado desde contacto", state="disabled")

        crear_label("Correo de contacto")
        crear_entry(var_contacto_correo, "Autollenado desde contacto", state="disabled")

        crear_label("Teléfono del cliente")
        crear_entry(var_cliente_telefono, "Autollenado desde cliente", state="disabled")

        crear_label("Correo del cliente")
        crear_entry(var_cliente_correo, "Autollenado desde cliente", state="disabled")

        crear_label("Responsable")
        crear_entry(var_responsable, "Responsable del pedido")

        crear_label("Fecha de inicio")
        crear_entry(var_fecha_inicio, "Selecciona fecha", date=True)

        crear_label("Fecha compromiso")
        crear_entry(var_fecha_compromiso, "Selecciona fecha", date=True)

        cargar_datos_cliente()
        entry_numero_aco.focus_set()

        crear_label("Descripción")
        txt_descripcion = ctk.CTkTextbox(
            form,
            width=620,
            height=80,
            corner_radius=10
        )
        txt_descripcion.pack(
            padx=35,
            pady=(0, 4)
        )

        crear_label("Observaciones")
        txt_observaciones = ctk.CTkTextbox(
            form,
            width=620,
            height=70,
            corner_radius=10
        )
        txt_observaciones.pack(
            padx=35,
            pady=(0, 15)
        )

        def guardar_aco():
            """
            Valida y guarda el ACO en Supabase.
            """

            numero_aco = var_aco.get().strip().upper()
            var_aco.set(numero_aco)
            cliente = var_cliente.get().strip()
            responsable = var_responsable.get().strip()
            fecha_inicio = var_fecha_inicio.get().strip()
            fecha_compromiso = var_fecha_compromiso.get().strip()
            descripcion = txt_descripcion.get("1.0", "end").strip()
            observaciones = txt_observaciones.get("1.0", "end").strip()

            if not numero_aco or not cliente or cliente == "Sin clientes registrados" or not descripcion:
                messagebox.showwarning(
                    "Campos obligatorios",
                    "Debes capturar número de ACO, seleccionar un cliente válido y agregar descripción."
                )
                return

            if buscar_aco_por_numero(numero_aco):
                messagebox.showerror(
                    "ACO existente",
                    "Ya existe un ACO registrado con ese número."
                )
                return

            cliente_db = seleccion_operativa["clientes_por_nombre"].get(cliente)
            sucursal_db = seleccion_operativa["sucursales_por_nombre"].get(var_sucursal.get())
            contacto_db = seleccion_operativa["contactos_por_nombre"].get(var_contacto_operativo.get())

            datos_aco = {
                "aco_numero": numero_aco,
                "aco_estatus": 1,
                "id_cliente": cliente_db.get("id_cliente") if cliente_db else None,
                "id_sucursal": sucursal_db.get("suc_id") if sucursal_db else None,
                "id_contacto": contacto_db.get("con_id") if contacto_db else None,
                "aco_cliente": cliente,
                "aco_descripcion": descripcion,
                "aco_observaciones": observaciones,
                "aco_responsable": responsable,
                "aco_creado_por": usuario_activo.get("usuario"),
                "aco_fecha_inicio": fecha_inicio or None,
                "aco_fecha_compromiso": fecha_compromiso or None
            }

            resultado = crear_aco(datos_aco)

            if resultado:
                registrar_movimiento(
                    modulo="ACO",
                    accion="CREAR",
                    descripcion=f"El usuario creó el ACO {numero_aco}",
                    registro_afectado=numero_aco
                )

                messagebox.showinfo(
                    "ACO registrado",
                    "El ACO fue registrado correctamente."
                )

                mostrar_busqueda_aco()

            else:
                messagebox.showerror(
                    "Error",
                    "No se pudo registrar el ACO."
                )

        ctk.CTkButton(
            form,
            text="Guardar ACO",
            width=180,
            height=40,
            corner_radius=12,
            fg_color=SECONDARY,
            hover_color=BUTTON_HOVER,
            font=BUTTON_FONT,
            command=guardar_aco
        ).pack(
            pady=(0, 15)
        )

    # =================================================
    # FUNCIÓN: mostrar_solicitud_aco()
    # =================================================
    def mostrar_solicitud_aco():
        """
        Muestra aviso para usuarios no administrativos.

        Los usuarios técnicos o de operación no pueden
        crear ACO directamente; únicamente pueden solicitarlo
        al área administrativa correspondiente.
        """

        limpiar_frame(panel_dinamico)

        ctk.CTkLabel(
            panel_dinamico,
            text="Solicitud de ACO requerida",
            font=TITLE_MD,
            text_color=TEXT_PRIMARY
        ).pack(
            pady=(55, 10)
        )

        ctk.CTkLabel(
            panel_dinamico,
            text=(
                "Tu usuario no cuenta con permisos para crear ACO.\n\n"
                "Solicita al área administrativa la generación del pedido\n"
                "correspondiente antes de continuar con el flujo operativo."
            ),
            font=TEXT_MD,
            text_color=TEXT_SECONDARY,
            justify="center"
        ).pack(
            pady=(0, 25)
        )

        ctk.CTkButton(
            panel_dinamico,
            text="Entendido",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=SECONDARY,
            hover_color=BUTTON_HOVER,
            font=BUTTON_FONT,
            command=mostrar_mensaje_inicial
        ).pack()

    # =================================================
    # BOTONES SUPERIORES
    # =================================================

    usuario_activo = obtener_usuario_actual()
    es_administrativo = usuario_activo.get("usu_tipo") == 1

    ctk.CTkButton(
        frame_botones,
        text="Sí, tengo ACO",
        width=220,
        height=46,
        corner_radius=14,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=mostrar_busqueda_aco
    ).grid(
        row=0,
        column=0,
        padx=10
    )

    ctk.CTkButton(
        frame_botones,
        text="No tengo ACO",
        width=220,
        height=46,
        corner_radius=14,
        fg_color=PRIMARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=mostrar_formulario_crear_aco
        if puede_crear_aco(usuario_activo)
        else mostrar_solicitud_aco
    ).grid(
        row=0,
        column=1,
        padx=10
    )

    if aco_validado:
        mostrar_opciones_con_aco(aco_validado)
    else:
        mostrar_mensaje_inicial()