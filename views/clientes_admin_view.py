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

from app_context import obtener_usuario_actual
from security.permissions import es_admin
from ui.date_picker import abrir_selector_fecha
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
    if not es_admin(usuario_activo):
        messagebox.showerror("Acceso denegado", "Solo administradores pueden administrar clientes.")
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
    contenedor.pack(fill="both", expand=True, padx=28, pady=8)

    barra = ctk.CTkFrame(contenedor, fg_color="transparent")
    barra.pack(fill="x", pady=(0, 10))
    barra.grid_columnconfigure(0, weight=1)

    var_busqueda = ctk.StringVar()
    entry_busqueda = ctk.CTkEntry(
        barra,
        textvariable=var_busqueda,
        placeholder_text="Buscar cliente por razón social, RFC, contacto, teléfono, correo o municipio...",
        height=38,
    )
    entry_busqueda.grid(row=0, column=0, sticky="ew", padx=(0, 10))

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

    panel_resultados = ctk.CTkScrollableFrame(cuerpo, fg_color=WHITE, corner_radius=16)
    panel_resultados.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

    panel_formulario = ctk.CTkScrollableFrame(cuerpo, fg_color=WHITE, corner_radius=16)
    panel_formulario.grid(row=0, column=1, sticky="nsew")

    ctk.CTkLabel(
        panel_formulario,
        text="Datos del cliente",
        font=("Montserrat", 18, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(anchor="w", padx=20, pady=(18, 6))

    form_grid = ctk.CTkFrame(panel_formulario, fg_color="transparent")
    form_grid.pack(fill="x", padx=20, pady=(0, 12))
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
            pady=5,
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

        entry.grid(row=1, column=0, sticky="ew", pady=(2, 0))
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
    acciones.pack(fill="x", padx=20, pady=(5, 18))


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
    btn_guardar.pack(side="left", padx=8)

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
    btn_actualizar.pack(side="left", padx=8)

    # =========================================================
    # SUCURSALES Y CONTACTOS OPERATIVOS
    # =========================================================
    panel_operativo = ctk.CTkFrame(panel_formulario, fg_color="#F8FAFC", corner_radius=14)
    panel_operativo.pack(fill="x", padx=20, pady=(2, 18))
    panel_operativo.grid_columnconfigure((0, 1), weight=1, uniform="operativo")

    sucursales_estado = {"lista": [], "por_nombre": {}}

    var_suc_nombre = ctk.StringVar()
    var_suc_domicilio = ctk.StringVar()
    var_suc_municipio = ctk.StringVar()
    var_suc_estado = ctk.StringVar()
    var_suc_telefono = ctk.StringVar()

    var_contacto_sucursal = ctk.StringVar(value="Selecciona sucursal")
    var_contacto_nombre = ctk.StringVar()
    var_contacto_puesto = ctk.StringVar()
    var_contacto_correo = ctk.StringVar()
    var_contacto_celular = ctk.StringVar()

    ctk.CTkLabel(
        panel_operativo,
        text="Sucursales operativas",
        font=("Montserrat", 15, "bold"),
        text_color=TEXT_PRIMARY,
    ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

    ctk.CTkLabel(
        panel_operativo,
        text="Contactos por sucursal",
        font=("Montserrat", 15, "bold"),
        text_color=TEXT_PRIMARY,
    ).grid(row=0, column=1, sticky="w", padx=14, pady=(12, 4))

    panel_suc = ctk.CTkFrame(panel_operativo, fg_color="transparent")
    panel_suc.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
    panel_suc.grid_columnconfigure(0, weight=1)

    panel_con = ctk.CTkFrame(panel_operativo, fg_color="transparent")
    panel_con.grid(row=1, column=1, sticky="nsew", padx=12, pady=(0, 12))
    panel_con.grid_columnconfigure(0, weight=1)

    def input_operativo(panel, texto, variable, fila, placeholder=""):
        ctk.CTkLabel(panel, text=texto, font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=fila, column=0, sticky="w", pady=(4, 1))
        entry = ctk.CTkEntry(panel, textvariable=variable, height=32, placeholder_text=placeholder)
        entry.grid(row=fila + 1, column=0, sticky="ew", pady=(0, 3))
        return entry

    input_operativo(panel_suc, "Nombre de sucursal *", var_suc_nombre, 0, "Ej. Sucursal Centro")
    input_operativo(panel_suc, "Domicilio operativo", var_suc_domicilio, 2)
    input_operativo(panel_suc, "Municipio", var_suc_municipio, 4)
    input_operativo(panel_suc, "Estado", var_suc_estado, 6)
    input_operativo(panel_suc, "Teléfono", var_suc_telefono, 8)

    ctk.CTkLabel(panel_con, text="Sucursal *", font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=0, column=0, sticky="w", pady=(4, 1))
    selector_contacto_sucursal = ctk.CTkOptionMenu(
        panel_con,
        variable=var_contacto_sucursal,
        values=["Selecciona sucursal"],
        height=32,
    )
    selector_contacto_sucursal.grid(row=1, column=0, sticky="ew", pady=(0, 3))
    input_operativo(panel_con, "Nombre contacto *", var_contacto_nombre, 2)
    input_operativo(panel_con, "Puesto", var_contacto_puesto, 4)
    input_operativo(panel_con, "Correo", var_contacto_correo, 6)
    input_operativo(panel_con, "Celular", var_contacto_celular, 8)

    lista_sucursales = ctk.CTkLabel(
        panel_suc,
        text="Selecciona un cliente para ver sus sucursales.",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        justify="left",
        anchor="w",
        wraplength=360,
    )
    lista_sucursales.grid(row=11, column=0, sticky="ew", pady=(6, 0))

    lista_contactos = ctk.CTkLabel(
        panel_con,
        text="Selecciona una sucursal para ver sus contactos.",
        font=TEXT_SM,
        text_color=TEXT_SECONDARY,
        justify="left",
        anchor="w",
        wraplength=360,
    )
    lista_contactos.grid(row=11, column=0, sticky="ew", pady=(6, 0))

    def limpiar_sucursal_form():
        for variable in (var_suc_nombre, var_suc_domicilio, var_suc_municipio, var_suc_estado, var_suc_telefono):
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
            var_contacto_sucursal.set("Selecciona sucursal")
            lista_sucursales.configure(text="Selecciona un cliente para ver sus sucursales.")
            lista_contactos.configure(text="Selecciona una sucursal para ver sus contactos.")
            return

        sucursales = obtener_sucursales_por_cliente(id_cliente)
        sucursales_estado["lista"] = sucursales
        sucursales_estado["por_nombre"] = {str(s.get("suc_nombre", "") or ""): s for s in sucursales if s.get("suc_nombre")}
        nombres = list(sucursales_estado["por_nombre"].keys()) or ["Selecciona sucursal"]
        selector_contacto_sucursal.configure(values=nombres)
        var_contacto_sucursal.set(nombres[0])

        if sucursales:
            texto = "\n".join(
                f"• {s.get('suc_nombre', '-')} | {construir_domicilio_sucursal(s) or 'Sin domicilio'}"
                for s in sucursales[:6]
            )
            lista_sucursales.configure(text=texto)
        else:
            lista_sucursales.configure(text="Este cliente aún no tiene sucursales operativas registradas.")
        refrescar_contactos()

    def refrescar_contactos():
        sucursal = sucursales_estado["por_nombre"].get(var_contacto_sucursal.get())
        if not sucursal:
            lista_contactos.configure(text="Selecciona una sucursal para ver sus contactos.")
            return
        contactos = obtener_contactos_por_sucursal(sucursal.get("suc_id"))
        if contactos:
            texto = "\n".join(
                f"• {c.get('con_nombre', '-')} | {c.get('con_celular') or c.get('con_telefono') or 'Sin teléfono'}"
                for c in contactos[:6]
            )
            lista_contactos.configure(text=texto)
        else:
            lista_contactos.configure(text="Esta sucursal aún no tiene contactos registrados.")

    selector_contacto_sucursal.configure(command=lambda _valor: refrescar_contactos())

    def guardar_sucursal_operativa():
        seleccionado = estado.get("seleccionado")
        if not seleccionado:
            messagebox.showwarning("Sucursales", "Selecciona primero un cliente.")
            return
        exito, mensaje, _ = crear_sucursal({
            "id_cliente": seleccionado.get("id_cliente"),
            "suc_nombre": var_suc_nombre.get(),
            "suc_domicilio": var_suc_domicilio.get(),
            "suc_municipio": var_suc_municipio.get(),
            "suc_estado": var_suc_estado.get(),
            "suc_telefono": var_suc_telefono.get(),
        })
        if exito:
            messagebox.showinfo("Sucursales", mensaje)
            limpiar_sucursal_form()
            refrescar_sucursales_contactos()
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

    ctk.CTkButton(
        panel_suc,
        text="+ Guardar sucursal",
        height=34,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=guardar_sucursal_operativa,
    ).grid(row=10, column=0, sticky="ew", pady=(6, 4))

    ctk.CTkButton(
        panel_con,
        text="+ Guardar contacto",
        height=34,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=guardar_contacto_operativo,
    ).grid(row=10, column=0, sticky="ew", pady=(6, 4))

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
        item.pack(fill="x", padx=12, pady=4)

        label = ctk.CTkLabel(
            item,
            text=texto,
            anchor="w",
            justify="left",
            font=TEXT_SM,
            text_color=TEXT_PRIMARY,
            wraplength=320,
        )
        label.pack(fill="x", padx=10, pady=8, anchor="w")

        item.bind("<Button-1>", lambda _event, seleccionado=cliente: cargar_en_formulario(seleccionado))
        label.bind("<Button-1>", lambda _event, seleccionado=cliente: cargar_en_formulario(seleccionado))

    def pintar_resultados():
        for widget in panel_resultados.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            panel_resultados,
            text=f"Resultados ({len(estado['resultados'])})",
            font=("Montserrat", 16, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(16, 8))

        if not estado["resultados"]:
            ctk.CTkLabel(
                panel_resultados,
                text="Ingresa un dato de búsqueda para consultar clientes.",
                font=TEXT_SM,
                text_color=TEXT_SECONDARY,
            ).pack(anchor="w", padx=18, pady=8)
            return

        for cliente in estado["resultados"]:
            razon_social = cliente.get("cli_razonsocial", "-")
            contacto = cliente.get("cli_contacto", "")
            telefono = cliente.get("cli_telefono", "")
            direccion = construir_direccion_cliente(cliente)
            texto = f"{razon_social}\n{contacto} {telefono}".strip()
            if direccion:
                texto = f"{texto}\n{direccion}"

            crear_item_resultado(cliente, texto)

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