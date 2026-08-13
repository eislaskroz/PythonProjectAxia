from core.error_reporting import show_operation_error
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
from ui.native_combobox import NativeComboBox
from core.background_tasks import run_async

from ui.colors import (
    PRIMARY,
    SECONDARY,
    WHITE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    BUTTON_HOVER
)

from ui.date_picker import asociar_selector_fecha
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
from services.clientes_service import (
    buscar_clientes,
    construir_direccion_cliente,
    crear_cliente,
    actualizar_cliente,
)
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
        height=112,
        fg_color="transparent"
    )
    # Se integra al flujo normal del layout para que no desaparezca al usar
    # otras resoluciones o escalas de Windows.
    panel_superior.pack(
        fill="x",
        padx=18,
        pady=(10, 0)
    )
    panel_superior.pack_propagate(False)

    ctk.CTkLabel(
        panel_superior,
        text="¿Tienes ACO asignado?",
        font=TITLE_MD,
        text_color=TEXT_PRIMARY
    ).pack(
        pady=(0, 1)
    )

    ctk.CTkLabel(
        panel_superior,
        text="El ACO conecta levantamientos, órdenes de servicio y bitácoras operativas.",
        font=TEXT_MD,
        text_color=TEXT_SECONDARY,
        justify="center"
    ).pack(
        pady=(0, 4)
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
        padx=18,
        pady=(8, 12)
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
            pady=110
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
            pady=(18, 4)
        )

        var_aco = ctk.StringVar()

        var_aco.trace_add("write", lambda *_: normalizar_aco_visual(var_aco))

        seleccion_operativa = {
            "clientes_por_nombre": {},
            "sucursales_por_nombre": {},
            "contactos_por_nombre": {},
            "selector_sucursal": None,
            "selector_contacto": None,
            "selector_cliente": None,
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
            pady=(2, 8)
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
            pady=4
        )

    # =================================================
    # OPCIONES CON ACO VALIDADO
    # =================================================
    def mostrar_opciones_con_aco(aco):
        """
        Muestra las opciones operativas disponibles
        después de validar correctamente un ACO.

        Las opciones se construyen con la matriz central de permisos:
        Administrador, Jefe de Operaciones, Supervisor, Administrativo y
        Especial pueden usar todos los flujos operativos. El Operador solo
        puede generar levantamientos.
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

        # =================================================
        # ENCABEZADO DE CONFIRMACIÓN
        # =================================================

        ctk.CTkLabel(
            panel_dinamico,
            text=f"ACO validado: {numero_aco}",
            font=TITLE_MD,
            text_color=PRIMARY
        ).pack(
            pady=(22, 2)
        )

        ctk.CTkLabel(
            panel_dinamico,
            text=f"Cliente: {cliente}",
            font=TEXT_MD,
            text_color=TEXT_SECONDARY
        ).pack(
            pady=(0, 4)
        )

        ctk.CTkLabel(
            panel_dinamico,
            text="Selecciona la operación que deseas realizar:",
            font=TEXT_MD,
            text_color=TEXT_PRIMARY
        ).pack(
            pady=(0, 12)
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
                pady=4
            )

    # =================================================
    # CREAR ACO
    # =================================================

    def mostrar_formulario_crear_aco():
        """Muestra el formulario de alta de ACO usando toda el área disponible."""

        limpiar_frame(panel_dinamico)
        usuario_activo = obtener_usuario_actual()

        # El contenido desplazable ocupa toda el área útil que deja la barra lateral.
        # La botonera queda fuera del scroll para permanecer visible en todo momento.
        contenedor_aco = ctk.CTkFrame(panel_dinamico, fg_color="transparent")
        contenedor_aco.pack(fill="both", expand=True, padx=10, pady=(10, 8))

        form = ctk.CTkScrollableFrame(
            contenedor_aco,
            fg_color="#f1f5f9",
            corner_radius=16,
        )
        form.pack(fill="both", expand=True, padx=0, pady=(0, 8))

        barra_acciones = ctk.CTkFrame(contenedor_aco, fg_color="transparent", height=54)
        barra_acciones.pack(fill="x", padx=4, pady=(0, 2))
        barra_acciones.pack_propagate(False)

        var_aco = ctk.StringVar(value="Se asigna automáticamente al guardar")
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

        seleccion_operativa = {
            "clientes_por_nombre": {},
            "sucursales_por_nombre": {},
            "contactos_por_nombre": {},
            "selector_sucursal": None,
            "selector_contacto": None,
            "selector_cliente": None,
        }

        # Anchura responsiva: los controles se estiran con la ventana en vez de
        # quedar limitados a 620 px. Se usa grid para que toda la zona derecha sea útil.
        form.grid_columnconfigure(0, weight=1)

        def crear_label(texto):
            etiqueta = ctk.CTkLabel(
                form,
                text=texto,
                font=TEXT_SM,
                text_color=TEXT_PRIMARY,
            )
            etiqueta.grid(row=crear_label.fila, column=0, sticky="w", padx=28, pady=(7, 2))
            crear_label.fila += 1
            return etiqueta
        crear_label.fila = 0

        def _grid_control(widget):
            widget.grid(row=crear_label.fila, column=0, sticky="ew", padx=68, pady=(0, 3))
            crear_label.fila += 1
            return widget

        def crear_entry(variable, placeholder, state="normal", date=False):
            entry = ctk.CTkEntry(
                form,
                textvariable=variable,
                height=40,
                corner_radius=10,
                placeholder_text=placeholder,
                state=state,
            )
            _grid_control(entry)
            if date and state != "disabled":
                # Solo se abre con clic. El antiguo FocusIn provocaba que al cerrar
                # el calendario se abriera de nuevo inmediatamente.
                asociar_selector_fecha(entry, form, variable, abrir_con_foco=False)
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

            selector = NativeComboBox(
                form,
                variable=variable,
                values=nombres,
                height=38,
                command=lambda _nombre: cargar_datos_cliente(),
            )
            _grid_control(selector)
            seleccion_operativa["selector_cliente"] = selector
            return clientes_por_nombre

        def refrescar_clientes(seleccionar_nombre=None):
            """Recarga el catálogo de clientes tras una alta o modificación."""
            clientes = buscar_clientes("", limite=500) or []
            clientes_por_nombre = {}
            for cliente_db in clientes:
                nombre = str(cliente_db.get("cli_razonsocial", "") or "").strip()
                if nombre:
                    clientes_por_nombre[nombre] = cliente_db

            seleccion_operativa["clientes_por_nombre"] = clientes_por_nombre
            nombres = sorted(clientes_por_nombre.keys()) or ["Sin clientes registrados"]
            selector = seleccion_operativa.get("selector_cliente")
            if selector:
                selector.configure(values=nombres)

            destino = str(seleccionar_nombre or "").strip()
            if destino and destino in clientes_por_nombre:
                var_cliente.set(destino)
            elif var_cliente.get() not in clientes_por_nombre:
                var_cliente.set(nombres[0])

            cargar_datos_cliente()

        def abrir_editor_cliente(modo="nuevo"):
            """Abre un editor modal de cliente sin abandonar el ACO en captura."""
            cliente_actual = seleccion_operativa["clientes_por_nombre"].get(var_cliente.get())
            if modo == "editar" and not cliente_actual:
                messagebox.showwarning(
                    "Cliente requerido",
                    "Selecciona un cliente válido antes de modificarlo.",
                )
                return

            ventana = ctk.CTkToplevel(panel_dinamico)
            ventana.title("Cliente nuevo" if modo == "nuevo" else "Modificar cliente")
            ventana.geometry("920x720")
            ventana.minsize(760, 620)
            ventana.transient(panel_dinamico.winfo_toplevel())
            ventana.grab_set()

            cont = ctk.CTkFrame(ventana, fg_color=WHITE, corner_radius=16)
            cont.pack(fill="both", expand=True, padx=14, pady=14)

            ctk.CTkLabel(
                cont,
                text="Cliente nuevo" if modo == "nuevo" else "Modificar cliente",
                font=TITLE_MD,
                text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=18, pady=(14, 2))
            ctk.CTkLabel(
                cont,
                text=(
                    "Registra los datos del cliente y vuelve automáticamente al ACO."
                    if modo == "nuevo"
                    else "Actualiza el cliente seleccionado; los cambios se reflejarán en el ACO."
                ),
                font=TEXT_SM,
                text_color=TEXT_SECONDARY,
            ).pack(anchor="w", padx=18, pady=(0, 10))

            scroll = ctk.CTkScrollableFrame(cont, fg_color="#f1f5f9", corner_radius=14)
            scroll.pack(fill="both", expand=True, padx=14, pady=(0, 8))
            scroll.grid_columnconfigure((0, 1), weight=1, uniform="cliente")

            campos = {
                "cli_tipo": ctk.StringVar(value="Cliente"),
                "cli_estatus": ctk.StringVar(value="Activo"),
                "cli_razonsocial": ctk.StringVar(),
                "cli_rfc": ctk.StringVar(),
                "cli_contacto": ctk.StringVar(),
                "cli_telefono": ctk.StringVar(),
                "cli_correo": ctk.StringVar(),
                "cli_calle": ctk.StringVar(),
                "cli_numero": ctk.StringVar(),
                "cli_colonia": ctk.StringVar(),
                "cli_municipio": ctk.StringVar(),
                "cli_estado": ctk.StringVar(),
                "cli_cp": ctk.StringVar(),
                "cli_notas": ctk.StringVar(),
            }

            # Solo el modo edición debe precargar datos.
            # "Cliente nuevo" siempre abre un formulario limpio para evitar
            # mezclar accidentalmente información del cliente seleccionado en el ACO.
            if modo == "editar" and cliente_actual:
                for nombre_campo, variable in campos.items():
                    variable.set(str(cliente_actual.get(nombre_campo, "") or ""))

            etiquetas = [
                ("cli_tipo", "Tipo"), ("cli_estatus", "Estatus"),
                ("cli_razonsocial", "Razón social *"), ("cli_rfc", "RFC"),
                ("cli_contacto", "Contacto"), ("cli_telefono", "Teléfono"),
                ("cli_correo", "Correo"), ("cli_calle", "Calle"),
                ("cli_numero", "Número"), ("cli_colonia", "Colonia"),
                ("cli_municipio", "Municipio"), ("cli_estado", "Estado"),
                ("cli_cp", "Código Postal"), ("cli_notas", "Notas"),
            ]

            for pos, (nombre_campo, etiqueta) in enumerate(etiquetas):
                fila, col = divmod(pos, 2)
                wrapper = ctk.CTkFrame(scroll, fg_color="transparent")
                wrapper.grid(row=fila, column=col, sticky="ew", padx=9, pady=6)
                wrapper.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(
                    wrapper, text=etiqueta, font=TEXT_SM, text_color=TEXT_PRIMARY
                ).grid(row=0, column=0, sticky="w", pady=(0, 2))

                if nombre_campo == "cli_tipo":
                    control = NativeComboBox(
                        wrapper, variable=campos[nombre_campo],
                        values=["Cliente", "Proveedor", "Prospecto", "Interno"], height=36
                    )
                elif nombre_campo == "cli_estatus":
                    control = NativeComboBox(
                        wrapper, variable=campos[nombre_campo],
                        values=["Activo", "Inactivo"], height=36
                    )
                else:
                    control = ctk.CTkEntry(wrapper, textvariable=campos[nombre_campo], height=38)
                control.grid(row=1, column=0, sticky="ew")

            acciones_cliente = ctk.CTkFrame(cont, fg_color="transparent")
            acciones_cliente.pack(fill="x", padx=14, pady=(0, 10))

            def guardar_cliente_modal():
                datos = {campo: variable.get().strip() for campo, variable in campos.items()}
                if not datos.get("cli_razonsocial"):
                    messagebox.showwarning("Campo requerido", "La razón social es obligatoria.", parent=ventana)
                    return

                if modo == "nuevo":
                    ok, mensaje, cliente_guardado = crear_cliente(datos)
                else:
                    ok, mensaje, cliente_guardado = actualizar_cliente(
                        cliente_actual.get("id_cliente"), datos
                    )

                if not ok:
                    messagebox.showerror("Cliente", mensaje, parent=ventana)
                    return

                nombre_guardado = str((cliente_guardado or {}).get("cli_razonsocial", "") or "").strip()
                ventana.grab_release()
                ventana.destroy()
                refrescar_clientes(nombre_guardado)
                messagebox.showinfo("Cliente", mensaje)

            ctk.CTkButton(
                acciones_cliente,
                text="Cancelar",
                width=150,
                height=40,
                fg_color=PRIMARY,
                hover_color=BUTTON_HOVER,
                font=BUTTON_FONT,
                command=ventana.destroy,
            ).pack(side="right", padx=5)
            ctk.CTkButton(
                acciones_cliente,
                text="Guardar cliente" if modo == "nuevo" else "Guardar cambios",
                width=190,
                height=40,
                fg_color=SECONDARY,
                hover_color=BUTTON_HOVER,
                font=BUTTON_FONT,
                command=guardar_cliente_modal,
            ).pack(side="right", padx=5)

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
            selector = NativeComboBox(
                form,
                variable=variable,
                values=["Sin sucursales registradas"],
                height=38,
                command=lambda _nombre: cargar_datos_sucursal(),
            )
            _grid_control(selector)
            seleccion_operativa["selector_sucursal"] = selector
            return selector

        def crear_selector_contacto(variable):
            selector = NativeComboBox(
                form,
                variable=variable,
                values=["Sin contactos registrados"],
                height=38,
                command=lambda _nombre: cargar_datos_contacto(),
            )
            _grid_control(selector)
            seleccion_operativa["selector_contacto"] = selector
            return selector

        crear_label("Número de ACO")
        crear_entry(
            var_aco,
            "Se asigna automáticamente al guardar",
            state="disabled",
        )

        crear_label("Cliente")
        crear_selector_cliente(var_cliente)

        acciones_cliente_aco = ctk.CTkFrame(form, fg_color="transparent")
        acciones_cliente_aco.grid(
            row=crear_label.fila, column=0, sticky="e", padx=68, pady=(2, 5)
        )
        crear_label.fila += 1
        ctk.CTkButton(
            acciones_cliente_aco,
            text="+ Cliente nuevo",
            width=160,
            height=36,
            corner_radius=10,
            fg_color=SECONDARY,
            hover_color=BUTTON_HOVER,
            font=BUTTON_FONT,
            command=lambda: abrir_editor_cliente("nuevo"),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            acciones_cliente_aco,
            text="Modificar cliente",
            width=170,
            height=36,
            corner_radius=10,
            fg_color=PRIMARY,
            hover_color=BUTTON_HOVER,
            font=BUTTON_FONT,
            command=lambda: abrir_editor_cliente("editar"),
        ).pack(side="left")

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

        crear_label("Observaciones")
        txt_observaciones = ctk.CTkTextbox(form, height=80, corner_radius=10)
        _grid_control(txt_observaciones)

        def guardar_aco():
            """Valida y guarda; Supabase asigna el folio ACO automáticamente."""
            cliente = var_cliente.get().strip()
            responsable = var_responsable.get().strip()
            fecha_inicio = var_fecha_inicio.get().strip()
            fecha_compromiso = var_fecha_compromiso.get().strip()
            observaciones = txt_observaciones.get("1.0", "end").strip()

            if not cliente or cliente == "Sin clientes registrados":
                messagebox.showwarning(
                    "Campos obligatorios",
                    "Debes seleccionar un cliente válido.",
                )
                return

            cliente_db = seleccion_operativa["clientes_por_nombre"].get(cliente)
            sucursal_db = seleccion_operativa["sucursales_por_nombre"].get(var_sucursal.get())
            contacto_db = seleccion_operativa["contactos_por_nombre"].get(var_contacto_operativo.get())

            datos_aco = {
                # aco_numero NO se envía: el trigger de Supabase lo asigna.
                "aco_estatus": 1,
                "id_cliente": cliente_db.get("id_cliente") if cliente_db else None,
                "id_sucursal": sucursal_db.get("suc_id") if sucursal_db else None,
                "id_contacto": contacto_db.get("con_id") if contacto_db else None,
                "aco_cliente": cliente,
                # Se conserva la columna histórica para compatibilidad con Supabase,
                # pero la captura visible del ACO utiliza únicamente Observaciones.
                "aco_descripcion": "",
                "aco_observaciones": observaciones,
                "aco_responsable": responsable,
                "aco_creado_por": usuario_activo.get("usuario"),
                "aco_fecha_inicio": fecha_inicio or None,
                "aco_fecha_compromiso": fecha_compromiso or None,
            }

            resultado = crear_aco(datos_aco)

            if resultado:
                creado = resultado[0] if isinstance(resultado, list) and resultado else {}
                numero_aco = str(creado.get("aco_numero", "") or "").strip()
                var_aco.set(numero_aco or "Asignado por Supabase")

                registrar_movimiento(
                    modulo="ACO",
                    accion="CREAR",
                    descripcion=f"El usuario creó el ACO {numero_aco or 'generado por Supabase'}",
                    registro_afectado=numero_aco or None,
                )

                messagebox.showinfo(
                    "ACO registrado",
                    f"El ACO {numero_aco or ''} fue registrado correctamente.".strip(),
                )
                mostrar_busqueda_aco()
            else:
                show_operation_error("Error al guardar", "Registrar ACO")

        ctk.CTkButton(
            barra_acciones,
            text="Guardar ACO",
            width=220,
            height=42,
            corner_radius=12,
            fg_color=SECONDARY,
            hover_color=BUTTON_HOVER,
            font=BUTTON_FONT,
            command=guardar_aco,
        ).pack(side="right", padx=(8, 4), pady=5)

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
            pady=(28, 5)
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
            pady=(0, 12)
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

    ctk.CTkButton(
        frame_botones,
        text="Sí, tengo ACO",
        width=220,
        height=40,
        corner_radius=12,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=mostrar_busqueda_aco
    ).grid(
        row=0,
        column=0,
        padx=5
    )

    ctk.CTkButton(
        frame_botones,
        text="No tengo ACO",
        width=220,
        height=40,
        corner_radius=12,
        fg_color=PRIMARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=mostrar_formulario_crear_aco
        if puede_crear_aco(usuario_activo)
        else mostrar_solicitud_aco
    ).grid(
        row=0,
        column=1,
        padx=5
    )

    if aco_validado:
        mostrar_opciones_con_aco(aco_validado)
    else:
        # El buscador vuelve a mostrarse de forma inmediata al entrar a ACO.
        mostrar_busqueda_aco()
