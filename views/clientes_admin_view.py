"""
=========================================================
MÓDULO: views/clientes_admin_view.py
DESCRIPCIÓN:
Vista administrativa para buscar, crear y modificar clientes.

Adaptada a los campos reales de db_clientes:
cli_tipo, cli_estatus, cli_razonsocial, cli_rfc, cli_contacto,
cli_telefono, cli_calle, cli_numero, cli_colonia, cli_municipio,
cli_estado, cli_cp, cli_correo y cli_notas.
=========================================================
"""

import customtkinter as ctk
from tkinter import messagebox
from ui.native_combobox import NativeComboBox

from app_context import obtener_usuario_actual
from security.permissions import puede_administrar_clientes
from ui.date_picker import abrir_selector_fecha
from ui.native_table import NativeTreeTable
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TEXT_SM, BUTTON_FONT
from services.clientes_service import (
    buscar_clientes,
    crear_cliente,
    actualizar_cliente,
    construir_direccion_cliente,
    CAMPOS_CLIENTE,
)
from services.sucursales_service import (
    obtener_sucursales_por_cliente,
    obtener_contactos_por_sucursal,
    crear_sucursal,
    crear_contacto_sucursal,
    actualizar_sucursal,
    actualizar_contacto_sucursal,
    construir_domicilio_sucursal,
)


ETIQUETAS_CLIENTE = {
    "cli_tipo": "Tipo",
    "cli_estatus": "Estatus",
    "cli_razonsocial": "Razón social",
    "cli_rfc": "RFC",
    "cli_contacto": "Contacto",
    "cli_telefono": "Teléfono",
    "cli_correo": "Correo",
    "cli_calle": "Calle",
    "cli_numero": "Número",
    "cli_colonia": "Colonia",
    "cli_municipio": "Municipio",
    "cli_estado": "Estado",
    "cli_cp": "Código Postal",
    "cli_notas": "Notas",
}


CAMPOS_ANCHO_COMPLETO = {"cli_razonsocial", "cli_notas"}


def mostrar_clientes_admin(parent, app):
    """
    Renderiza la administración de clientes.
    """

    usuario_activo = obtener_usuario_actual()
    if not puede_administrar_clientes(usuario_activo):
        messagebox.showerror("Acceso denegado", "Tu nivel de usuario no tiene permiso para administrar clientes.")
        app.mostrar_vista_inicio_aco()
        return

    for widget in parent.winfo_children():
        widget.destroy()

    estado = {
        "seleccionado": None,
        "resultados": [],
        "variables": {},
        "entradas": {},
        "modo": "lectura",
    }

    contenedor = ctk.CTkFrame(parent, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=14, pady=4)

    barra = ctk.CTkFrame(contenedor, fg_color="transparent")
    barra.pack(fill="x", pady=(0, 5))
    barra.grid_columnconfigure(0, weight=1)

    var_busqueda = ctk.StringVar()
    entry_busqueda = ctk.CTkEntry(
        barra,
        textvariable=var_busqueda,
        placeholder_text="Buscar cliente por razón social, RFC, contacto, teléfono, correo o municipio...",
        height=38,
    )
    entry_busqueda.grid(row=0, column=0, sticky="ew", padx=(0, 5))

    ctk.CTkButton(
        barra,
        text="🔎 Buscar",
        width=120,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: cargar_resultados(var_busqueda.get()),
    ).grid(row=0, column=1)

    cuerpo = ctk.CTkFrame(contenedor, fg_color="transparent")
    cuerpo.pack(fill="both", expand=True)
    cuerpo.grid_columnconfigure(0, weight=1)
    cuerpo.grid_columnconfigure(1, weight=2)
    cuerpo.grid_rowconfigure(0, weight=1)

    panel_resultados = ctk.CTkFrame(cuerpo, fg_color=WHITE, corner_radius=16)
    panel_resultados.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    panel_resultados.grid_rowconfigure(1, weight=1)
    panel_resultados.grid_columnconfigure(0, weight=1)
    lbl_resultados = ctk.CTkLabel(
        panel_resultados, text="Resultados (0)", font=("Montserrat", 16, "bold"),
        text_color=TEXT_PRIMARY, anchor="w",
    )
    lbl_resultados.grid(row=0, column=0, sticky="ew", padx=9, pady=(8, 4))
    tabla_resultados = NativeTreeTable(
        panel_resultados,
        columns=(("razon", "Razón social", 190), ("contacto", "Contacto", 140), ("telefono", "Teléfono", 105), ("municipio", "Municipio", 130)),
        on_select=lambda cliente: cargar_en_formulario(cliente),
        on_open=lambda cliente: cargar_en_formulario(cliente),
        height=18,
    )
    tabla_resultados.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    panel_formulario = ctk.CTkScrollableFrame(cuerpo, fg_color=WHITE, corner_radius=16)
    panel_formulario.grid(row=0, column=1, sticky="nsew")

    ctk.CTkLabel(
        panel_formulario,
        text="Datos del cliente",
        font=("Montserrat", 18, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(anchor="w", padx=10, pady=(9, 3))

    form_grid = ctk.CTkFrame(panel_formulario, fg_color="transparent")
    form_grid.pack(fill="x", padx=10, pady=(0, 6))
    form_grid.grid_columnconfigure(0, weight=1)
    form_grid.grid_columnconfigure(1, weight=1)
    form_grid.grid_columnconfigure(2, weight=1)

    fila_actual = 0
    columna_actual = 0

    for campo in CAMPOS_CLIENTE:
        ancho_completo = campo in CAMPOS_ANCHO_COMPLETO

        if ancho_completo and columna_actual != 0:
            fila_actual += 1
            columna_actual = 0

        wrapper = ctk.CTkFrame(form_grid, fg_color="transparent")
        wrapper.grid(
            row=fila_actual,
            column=0 if ancho_completo else columna_actual,
            columnspan=3 if ancho_completo else 1,
            sticky="ew",
            padx=0 if ancho_completo else ((0, 8) if columna_actual == 0 else ((8, 8) if columna_actual == 1 else (8, 0))),
            pady=2,
        )
        wrapper.grid_columnconfigure(0, weight=1)

        requerido = " *" if campo == "cli_razonsocial" else ""
        icono = "🏢" if campo == "cli_razonsocial" else ("📄" if campo == "cli_rfc" else ("👤" if campo == "cli_contacto" else ("☎️" if campo == "cli_telefono" else ("✉️" if campo == "cli_correo" else ("📍" if campo.startswith("cli_") and campo in ("cli_calle", "cli_numero", "cli_colonia", "cli_municipio", "cli_estado", "cli_cp") else "•")))))
        ctk.CTkLabel(
            wrapper,
            text=f"{icono} {ETIQUETAS_CLIENTE.get(campo, campo)}{requerido}",
            font=TEXT_SM,
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        var = ctk.StringVar()
        estado["variables"][campo] = var

        if campo == "cli_notas":
            entry = ctk.CTkEntry(wrapper, textvariable=var, height=36, placeholder_text="Notas internas del cliente...")
        else:
            entry = ctk.CTkEntry(wrapper, textvariable=var, height=36)

        entry.grid(row=1, column=0, sticky="ew", pady=(1, 0))
        if "fecha" in campo.lower():
            entry.bind("<Button-1>", lambda _event, var=var: abrir_selector_fecha(wrapper, var))
        entry.configure(state="disabled")
        estado["entradas"][campo] = entry

        if ancho_completo:
            fila_actual += 1
            columna_actual = 0
        else:
            if columna_actual < 2:
                columna_actual += 1
            else:
                columna_actual = 0
                fila_actual += 1

    acciones = ctk.CTkFrame(panel_formulario, fg_color="transparent")
    acciones.pack(fill="x", padx=10, pady=(2, 9))


    btn_guardar = ctk.CTkButton(
        acciones,
        text="💾 Guardar nuevo",
        width=150,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: guardar_nuevo(),
    )
    btn_guardar.pack(side="left", padx=4)

    btn_actualizar = ctk.CTkButton(
        acciones,
        text="⚠️ Actualizar seleccionado",
        width=190,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: actualizar_seleccionado(),
    )
    btn_actualizar.pack(side="left", padx=4)

    # =========================================================
    # SUCURSALES Y CONTACTOS OPERATIVOS
    # =========================================================
    panel_operativo = ctk.CTkFrame(panel_formulario, fg_color="#F8FAFC", corner_radius=14)
    panel_operativo.pack(fill="x", padx=10, pady=(1, 9))
    panel_operativo.grid_columnconfigure((0, 1), weight=1, uniform="operativo")

    sucursales_estado = {"lista": [], "por_nombre": {}, "contactos": [], "contactos_por_nombre": {}, "sucursal_edicion": None, "contacto_edicion": None}

    var_suc_nombre = ctk.StringVar()
    var_suc_calle_numero = ctk.StringVar()
    var_suc_colonia = ctk.StringVar()
    var_suc_municipio = ctk.StringVar()
    var_suc_estado = ctk.StringVar()
    var_suc_codigo_postal = ctk.StringVar()
    var_suc_telefono = ctk.StringVar()

    var_contacto_sucursal = ctk.StringVar(value="Selecciona sucursal")
    var_contacto_nombre = ctk.StringVar()
    var_contacto_puesto = ctk.StringVar()
    var_contacto_correo = ctk.StringVar()
    var_contacto_celular = ctk.StringVar()

    ctk.CTkLabel(
        panel_operativo,
        text="Sucursales operativas",
        font=("Montserrat", 14, "bold"),
        text_color=TEXT_PRIMARY,
    ).grid(row=0, column=0, sticky="w", padx=7, pady=(6, 2))

    ctk.CTkLabel(
        panel_operativo,
        text="Contactos por sucursal",
        font=("Montserrat", 14, "bold"),
        text_color=TEXT_PRIMARY,
    ).grid(row=0, column=1, sticky="w", padx=7, pady=(6, 2))

    panel_suc = ctk.CTkFrame(panel_operativo, fg_color="transparent")
    panel_suc.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
    panel_suc.grid_columnconfigure(0, weight=1)

    panel_con = ctk.CTkFrame(panel_operativo, fg_color="transparent")
    panel_con.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 6))
    panel_con.grid_columnconfigure(0, weight=1)

    def input_operativo(panel, texto, variable, fila, placeholder=""):
        ctk.CTkLabel(panel, text=texto, font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=fila, column=0, sticky="w", pady=(2, 1))
        entry = ctk.CTkEntry(panel, textvariable=variable, height=32, placeholder_text=placeholder)
        entry.grid(row=fila + 1, column=0, sticky="ew", pady=(0, 2))
        return entry

    ctk.CTkLabel(panel_suc, text="Sucursal registrada", font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=0, column=0, sticky="w", pady=(2, 1))
    var_sucursal_editar = ctk.StringVar(value="Selecciona sucursal")
    selector_sucursal_editar = NativeComboBox(panel_suc, variable=var_sucursal_editar, values=["Selecciona sucursal"], height=32)
    selector_sucursal_editar.grid(row=1, column=0, sticky="ew", pady=(0, 4))

    # Formulario compacto de sucursal: conserva legibilidad sin crecer demasiado
    # en vertical al incorporar colonia y código postal.
    campos_suc = ctk.CTkFrame(panel_suc, fg_color="transparent")
    campos_suc.grid(row=2, column=0, sticky="ew", pady=(0, 2))
    campos_suc.grid_columnconfigure((0, 1), weight=1, uniform="suc_campos")

    def input_sucursal(texto, variable, fila, columna=0, columnspan=1, placeholder=""):
        ctk.CTkLabel(campos_suc, text=texto, font=TEXT_SM, text_color=TEXT_PRIMARY).grid(
            row=fila, column=columna, columnspan=columnspan, sticky="w",
            padx=(0, 4) if columna == 0 and columnspan == 1 else (4, 0) if columna == 1 else 0,
            pady=(2, 1),
        )
        entry = ctk.CTkEntry(campos_suc, textvariable=variable, height=32, placeholder_text=placeholder)
        entry.grid(
            row=fila + 1, column=columna, columnspan=columnspan, sticky="ew",
            padx=(0, 4) if columna == 0 and columnspan == 1 else (4, 0) if columna == 1 else 0,
            pady=(0, 2),
        )
        return entry

    input_sucursal("Nombre de sucursal *", var_suc_nombre, 0, columnspan=2, placeholder="Ej. Sucursal Centro")
    input_sucursal("Calle y Número", var_suc_calle_numero, 2, columnspan=2)
    input_sucursal("Colonia", var_suc_colonia, 4, 0)
    input_sucursal("Municipio", var_suc_municipio, 4, 1)
    input_sucursal("Estado", var_suc_estado, 6, 0)
    input_sucursal("Código Postal", var_suc_codigo_postal, 6, 1)
    input_sucursal("Teléfono", var_suc_telefono, 8, columnspan=2)

    ctk.CTkLabel(panel_con, text="Sucursal *", font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=0, column=0, sticky="w", pady=(2, 1))
    selector_contacto_sucursal = NativeComboBox(panel_con, variable=var_contacto_sucursal, values=["Selecciona sucursal"], height=32)
    selector_contacto_sucursal.grid(row=1, column=0, sticky="ew", pady=(0, 2))
    ctk.CTkLabel(panel_con, text="Contacto registrado", font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=2, column=0, sticky="w", pady=(2, 1))
    var_contacto_editar = ctk.StringVar(value="Selecciona contacto")
    selector_contacto_editar = NativeComboBox(panel_con, variable=var_contacto_editar, values=["Selecciona contacto"], height=32)
    selector_contacto_editar.grid(row=3, column=0, sticky="ew", pady=(0, 4))
    input_operativo(panel_con, "Nombre contacto *", var_contacto_nombre, 4)
    input_operativo(panel_con, "Puesto", var_contacto_puesto, 6)
    input_operativo(panel_con, "Correo", var_contacto_correo, 8)
    input_operativo(panel_con, "Celular", var_contacto_celular, 10)

    lista_sucursales = ctk.CTkLabel(
        panel_suc,
        text="Selecciona un cliente para ver sus sucursales.",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        justify="left",
        anchor="w",
        wraplength=360,
    )
    lista_sucursales.grid(row=5, column=0, sticky="ew", pady=(3, 0))

    lista_contactos = ctk.CTkLabel(
        panel_con,
        text="Selecciona una sucursal para ver sus contactos.",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        justify="left",
        anchor="w",
        wraplength=360,
    )
    lista_contactos.grid(row=15, column=0, sticky="ew", pady=(3, 0))

    def limpiar_sucursal_form():
        for variable in (var_suc_nombre, var_suc_calle_numero, var_suc_colonia, var_suc_municipio, var_suc_estado, var_suc_codigo_postal, var_suc_telefono):
            variable.set("")

    def limpiar_contacto_form():
        for variable in (var_contacto_nombre, var_contacto_puesto, var_contacto_correo, var_contacto_celular):
            variable.set("")

    def refrescar_sucursales_contactos():
        seleccionado = estado.get("seleccionado")
        id_cliente = seleccionado.get("id_cliente") if seleccionado else None
        if not id_cliente:
            sucursales_estado["lista"] = []
            sucursales_estado["por_nombre"] = {}
            selector_contacto_sucursal.configure(values=["Selecciona sucursal"])
            selector_sucursal_editar.configure(values=["Selecciona sucursal"])
            selector_contacto_editar.configure(values=["Selecciona contacto"])
            var_contacto_sucursal.set("Selecciona sucursal")
            var_sucursal_editar.set("Selecciona sucursal")
            var_contacto_editar.set("Selecciona contacto")
            lista_sucursales.configure(text="Selecciona un cliente para ver sus sucursales.")
            lista_contactos.configure(text="Selecciona una sucursal para ver sus contactos.")
            return

        sucursales = obtener_sucursales_por_cliente(id_cliente)
        sucursales_estado["lista"] = sucursales
        sucursales_estado["por_nombre"] = {str(s.get("suc_nombre", "") or ""): s for s in sucursales if s.get("suc_nombre")}
        nombres = list(sucursales_estado["por_nombre"].keys()) or ["Selecciona sucursal"]
        selector_contacto_sucursal.configure(values=nombres)
        selector_sucursal_editar.configure(values=nombres)
        var_contacto_sucursal.set(nombres[0])
        var_sucursal_editar.set("Selecciona sucursal")
        limpiar_sucursal_form()

        if sucursales:
            lista_sucursales.configure(text=f"Cantidad de Sucursales Registradas: {len(sucursales)}")
        else:
            lista_sucursales.configure(text="Cantidad de Sucursales Registradas: 0")
        refrescar_contactos()

    def refrescar_contactos():
        sucursal = sucursales_estado["por_nombre"].get(var_contacto_sucursal.get())
        if not sucursal:
            lista_contactos.configure(text="Selecciona una sucursal para ver sus contactos.")
            return
        contactos = obtener_contactos_por_sucursal(sucursal.get("suc_id"))
        sucursales_estado["contactos"] = contactos
        sucursales_estado["contactos_por_nombre"] = {str(c.get("con_nombre", "") or ""): c for c in contactos if c.get("con_nombre")}
        nombres_contactos = list(sucursales_estado["contactos_por_nombre"].keys()) or ["Selecciona contacto"]
        selector_contacto_editar.configure(values=nombres_contactos)
        var_contacto_editar.set("Selecciona contacto")
        limpiar_contacto_form()
        if contactos:
            texto = "\n".join(
                f"• {c.get('con_nombre', '-')} | {c.get('con_celular') or c.get('con_telefono') or 'Sin teléfono'}"
                for c in contactos[:6]
            )
            lista_contactos.configure(text=texto)
        else:
            lista_contactos.configure(text="Esta sucursal aún no tiene contactos registrados.")

    def cargar_sucursal_para_editar(_valor=None):
        sucursal = sucursales_estado["por_nombre"].get(var_sucursal_editar.get())
        sucursales_estado["sucursal_edicion"] = sucursal
        if not sucursal:
            limpiar_sucursal_form()
            return
        var_suc_nombre.set(str(sucursal.get("suc_nombre", "") or ""))
        var_suc_calle_numero.set(str(sucursal.get("suc_calle_numero") or sucursal.get("suc_domicilio") or ""))
        var_suc_colonia.set(str(sucursal.get("suc_colonia", "") or ""))
        var_suc_municipio.set(str(sucursal.get("suc_municipio", "") or ""))
        var_suc_estado.set(str(sucursal.get("suc_estado", "") or ""))
        var_suc_codigo_postal.set(str(sucursal.get("suc_codigo_postal", "") or ""))
        var_suc_telefono.set(str(sucursal.get("suc_telefono", "") or ""))

    def cargar_contacto_para_editar(_valor=None):
        contacto = sucursales_estado["contactos_por_nombre"].get(var_contacto_editar.get())
        sucursales_estado["contacto_edicion"] = contacto
        if not contacto:
            limpiar_contacto_form()
            return
        var_contacto_nombre.set(str(contacto.get("con_nombre", "") or ""))
        var_contacto_puesto.set(str(contacto.get("con_puesto", "") or ""))
        var_contacto_correo.set(str(contacto.get("con_correo", "") or ""))
        var_contacto_celular.set(str(contacto.get("con_celular") or contacto.get("con_telefono") or ""))

    selector_contacto_sucursal.configure(command=lambda _valor: refrescar_contactos())
    selector_sucursal_editar.configure(command=cargar_sucursal_para_editar)
    selector_contacto_editar.configure(command=cargar_contacto_para_editar)

    def guardar_sucursal_operativa():
        seleccionado = estado.get("seleccionado")
        if not seleccionado:
            messagebox.showwarning("Sucursales", "Selecciona primero un cliente.")
            return
        nombre_nuevo = var_suc_nombre.get().strip()
        exito, mensaje, registro = crear_sucursal({
            "id_cliente": seleccionado.get("id_cliente"),
            "suc_nombre": nombre_nuevo,
            "suc_calle_numero": var_suc_calle_numero.get(),
            "suc_colonia": var_suc_colonia.get(),
            "suc_municipio": var_suc_municipio.get(),
            "suc_estado": var_suc_estado.get(),
            "suc_codigo_postal": var_suc_codigo_postal.get(),
            "suc_telefono": var_suc_telefono.get(),
        })
        if exito:
            messagebox.showinfo("Sucursales", mensaje)
            limpiar_sucursal_form()
            refrescar_sucursales_contactos()
            nombre_guardado = str((registro or {}).get("suc_nombre") or nombre_nuevo).strip()
            if nombre_guardado and nombre_guardado in sucursales_estado["por_nombre"]:
                var_contacto_sucursal.set(nombre_guardado)
                refrescar_contactos()
        else:
            messagebox.showerror("Sucursales", mensaje)

    def guardar_contacto_operativo():
        sucursal = sucursales_estado["por_nombre"].get(var_contacto_sucursal.get())
        if not estado.get("seleccionado"):
            messagebox.showwarning("Contactos", "Selecciona primero un cliente.")
            return
        if not sucursal:
            messagebox.showwarning("Contactos", "Selecciona primero una sucursal válida.")
            return
        exito, mensaje, _ = crear_contacto_sucursal({
            "id_sucursal": sucursal.get("suc_id"),
            "con_nombre": var_contacto_nombre.get(),
            "con_puesto": var_contacto_puesto.get(),
            "con_correo": var_contacto_correo.get(),
            "con_celular": var_contacto_celular.get(),
        })
        if exito:
            messagebox.showinfo("Contactos", mensaje)
            limpiar_contacto_form()
            refrescar_contactos()
        else:
            messagebox.showerror("Contactos", mensaje)

    def actualizar_sucursal_operativa():
        sucursal = sucursales_estado.get("sucursal_edicion")
        if not sucursal:
            messagebox.showwarning("Sucursales", "Selecciona la sucursal que deseas editar.")
            return
        if not messagebox.askyesno("Confirmar", "¿Actualizar los datos de esta sucursal?"):
            return
        exito, mensaje, _ = actualizar_sucursal(sucursal.get("suc_id"), {
            "suc_nombre": var_suc_nombre.get(), "suc_calle_numero": var_suc_calle_numero.get(),
            "suc_colonia": var_suc_colonia.get(), "suc_municipio": var_suc_municipio.get(),
            "suc_estado": var_suc_estado.get(), "suc_codigo_postal": var_suc_codigo_postal.get(),
            "suc_telefono": var_suc_telefono.get(), "suc_estatus": sucursal.get("suc_estatus", 1),
        })
        (messagebox.showinfo if exito else messagebox.showerror)("Sucursales", mensaje)
        if exito:
            sucursales_estado["sucursal_edicion"] = None
            refrescar_sucursales_contactos()

    def actualizar_contacto_operativo():
        contacto = sucursales_estado.get("contacto_edicion")
        if not contacto:
            messagebox.showwarning("Contactos", "Selecciona el contacto que deseas editar.")
            return
        if not messagebox.askyesno("Confirmar", "¿Actualizar los datos de este contacto?"):
            return
        exito, mensaje, _ = actualizar_contacto_sucursal(contacto.get("con_id"), {
            "con_nombre": var_contacto_nombre.get(), "con_puesto": var_contacto_puesto.get(),
            "con_correo": var_contacto_correo.get(), "con_celular": var_contacto_celular.get(),
            "con_estatus": contacto.get("con_estatus", 1),
        })
        (messagebox.showinfo if exito else messagebox.showerror)("Contactos", mensaje)
        if exito:
            sucursales_estado["contacto_edicion"] = None
            refrescar_contactos()

    botones_suc = ctk.CTkFrame(panel_suc, fg_color="transparent")
    botones_suc.grid(row=4, column=0, sticky="ew", pady=(3, 2))
    botones_suc.grid_columnconfigure((0,1), weight=1)
    ctk.CTkButton(botones_suc, text="+ Nueva / Guardar", height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=guardar_sucursal_operativa).grid(row=0,column=0,sticky="ew",padx=(0,3))
    ctk.CTkButton(botones_suc, text="✏ Editar seleccionada", height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=actualizar_sucursal_operativa).grid(row=0,column=1,sticky="ew",padx=(3,0))

    botones_con = ctk.CTkFrame(panel_con, fg_color="transparent")
    botones_con.grid(row=14, column=0, sticky="ew", pady=(3, 2))
    botones_con.grid_columnconfigure((0,1), weight=1)
    ctk.CTkButton(botones_con, text="+ Nuevo / Guardar", height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=guardar_contacto_operativo).grid(row=0,column=0,sticky="ew",padx=(0,3))
    ctk.CTkButton(botones_con, text="✏ Editar seleccionado", height=34, fg_color=SECONDARY, hover_color=BUTTON_HOVER, font=BUTTON_FONT, command=actualizar_contacto_operativo).grid(row=0,column=1,sticky="ew",padx=(3,0))

    def bloquear_formulario():
        """Bloquea todos los campos para evitar ediciones accidentales."""
        for entry in estado["entradas"].values():
            entry.configure(state="disabled")
        estado["modo"] = "lectura"
        btn_guardar.configure(text="💾 Guardar nuevo")
        btn_actualizar.configure(text="⚠️ Actualizar seleccionado")

    def desbloquear_formulario(modo):
        """Desbloquea campos únicamente cuando se va a crear o actualizar."""
        estado["modo"] = modo
        for entry in estado["entradas"].values():
            entry.configure(state="normal")
        if modo == "nuevo":
            btn_guardar.configure(text="✅ Confirmar guardado")
            btn_actualizar.configure(text="⚠️ Actualizar seleccionado")
        elif modo == "editar":
            btn_guardar.configure(text="💾 Guardar nuevo")
            btn_actualizar.configure(text="✅ Confirmar actualización")

    def datos_formulario():
        return {campo: variable.get().strip() for campo, variable in estado["variables"].items()}

    def limpiar_formulario():
        estado["seleccionado"] = None
        refrescar_sucursales_contactos()
        for campo, variable in estado["variables"].items():
            if campo == "cli_tipo":
                variable.set("Cliente")
            elif campo == "cli_estatus":
                variable.set("Activo")
            else:
                variable.set("")

    def cargar_en_formulario(cliente):
        estado["seleccionado"] = cliente
        for campo, variable in estado["variables"].items():
            variable.set(str(cliente.get(campo, "") or ""))
        bloquear_formulario()
        refrescar_sucursales_contactos()

    def crear_item_resultado(cliente, texto):
        """
        Crea un resultado alineado a la izquierda.

        Se usa un frame + label en lugar de un botón multilínea,
        porque algunos temas de CustomTkinter centran el texto de
        botones cuando el texto tiene saltos de línea.
        """

        item = ctk.CTkFrame(
            panel_resultados,
            fg_color="transparent",
            corner_radius=10,
        )
        item.pack(fill="x", padx=6, pady=2)

        label = ctk.CTkLabel(
            item,
            text=texto,
            anchor="w",
            justify="left",
            font=TEXT_SM,
            text_color=TEXT_PRIMARY,
            wraplength=320,
        )
        label.pack(fill="x", padx=5, pady=4, anchor="w")

        item.bind("<Button-1>", lambda _event, seleccionado=cliente: cargar_en_formulario(seleccionado))
        label.bind("<Button-1>", lambda _event, seleccionado=cliente: cargar_en_formulario(seleccionado))

    def pintar_resultados():
        lbl_resultados.configure(text=f"Resultados ({len(estado['resultados'])})")
        tabla_resultados.set_rows(
            estado["resultados"],
            value_factory=lambda cliente: (
                cliente.get("cli_razonsocial", "-"),
                cliente.get("cli_contacto", ""),
                cliente.get("cli_telefono", ""),
                cliente.get("cli_municipio", ""),
            ),
        )

    def cargar_resultados(termino=""):
        termino = (termino or "").strip()
        if not termino:
            estado["resultados"] = []
            pintar_resultados()
            messagebox.showwarning("Búsqueda requerida", "Ingresa un dato para buscar clientes.")
            return
        estado["resultados"] = buscar_clientes(termino)
        pintar_resultados()

    def guardar_nuevo():
        if estado.get("modo") != "nuevo":
            limpiar_formulario()
            desbloquear_formulario("nuevo")
            return

        exito, mensaje, _ = crear_cliente(datos_formulario())
        if exito:
            messagebox.showinfo("Clientes", mensaje)
            limpiar_formulario()
            bloquear_formulario()
            cargar_resultados(var_busqueda.get())
        else:
            messagebox.showerror("Clientes", mensaje)

    def actualizar_seleccionado():
        seleccionado = estado.get("seleccionado")
        if not seleccionado:
            messagebox.showwarning("Clientes", "Selecciona un cliente de la lista.")
            return

        if estado.get("modo") != "editar":
            desbloquear_formulario("editar")
            return

        confirmar = messagebox.askyesno(
            "Confirmar actualización",
            "¿Estás seguro de modificar los datos de este cliente en la base de datos?"
        )

        if not confirmar:
            return

        exito, mensaje, _ = actualizar_cliente(
            seleccionado.get("id_cliente"),
            datos_formulario(),
        )
        if exito:
            messagebox.showinfo("Clientes", mensaje)
            bloquear_formulario()
            cargar_resultados(var_busqueda.get())
        else:
            messagebox.showerror("Clientes", mensaje)

    entry_busqueda.bind("<Return>", lambda _event: cargar_resultados(var_busqueda.get()))
    limpiar_formulario()
    pintar_resultados()
