"""
=========================================================
MÓDULO: views/usuarios_admin_view.py
DESCRIPCIÓN:
Vista administrativa para buscar, crear y modificar usuarios.
=========================================================
"""

import customtkinter as ctk
from tkinter import messagebox

from app_context import obtener_usuario_actual
from security.permissions import es_admin
from ui.date_picker import abrir_selector_fecha
from ui.colors import WHITE, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY, BUTTON_HOVER
from ui.fonts import TEXT_MD, TEXT_SM, BUTTON_FONT
from services.usuarios_service import (
    buscar_usuarios,
    crear_usuario_admin,
    actualizar_usuario_admin,
)


CAMPOS_USUARIO = [
    ("usu_nickname", "Usuario / Nickname", True),
    ("usu_password", "Nueva contraseña", False),
    ("usu_nombre", "Nombre", True),
    ("usu_apellido", "Apellido", True),
    ("usu_rfc", "RFC", False),
    ("usu_curp", "CURP", False),
    ("usu_imss", "IMSS", False),
    ("usu_ine", "INE", False),
    ("usu_fechanac", "Fecha nacimiento", False),
    ("usu_telefono", "Teléfono", False),
    ("usu_depto", "Departamento", False),
    ("usu_puesto", "Puesto", False),
    ("usu_calle", "Calle", False),
    ("usu_numero", "Número", False),
    ("usu_colonia", "Colonia", False),
    ("usu_municipio", "Municipio", False),
    ("usu_estado", "Estado", False),
    ("usu_cp", "Código Postal", False),
    ("usu_regimen", "Régimen", False),
]


def mostrar_usuarios_admin(parent, app):
    """
    Renderiza la administración de usuarios.
    """

    usuario_activo = obtener_usuario_actual()
    if not es_admin(usuario_activo):
        messagebox.showerror("Acceso denegado", "Solo administradores pueden administrar usuarios.")
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
        placeholder_text="Buscar usuario por nickname, nombre o apellido...",
        height=38,
    )
    entry_busqueda.grid(row=0, column=0, sticky="ew", padx=(0, 10))

    btn_buscar = ctk.CTkButton(
        barra,
        text="🔎 Buscar",
        width=120,
        height=38,
        fg_color=SECONDARY,
        hover_color=BUTTON_HOVER,
        font=BUTTON_FONT,
        command=lambda: cargar_resultados(var_busqueda.get()),
    )
    btn_buscar.grid(row=0, column=1)

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
        text="Datos del usuario",
        font=("Montserrat", 18, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(anchor="w", padx=20, pady=(18, 6))

    form_grid = ctk.CTkFrame(panel_formulario, fg_color="transparent")
    form_grid.pack(fill="x", padx=20, pady=(0, 12))
    form_grid.grid_columnconfigure(0, weight=1)
    form_grid.grid_columnconfigure(1, weight=1)
    form_grid.grid_columnconfigure(2, weight=1)

    for indice, (campo, etiqueta, obligatorio) in enumerate(CAMPOS_USUARIO):
        fila = indice // 3
        columna = indice % 3
        wrapper = ctk.CTkFrame(form_grid, fg_color="transparent")
        wrapper.grid(row=fila, column=columna, sticky="ew", padx=(0, 8) if columna == 0 else ((8, 8) if columna == 1 else (8, 0)), pady=5)
        wrapper.grid_columnconfigure(0, weight=1)

        texto = f"{etiqueta}{' *' if obligatorio else ''}"
        icono = "🔐" if campo == "usu_password" else ("👤" if campo in ("usu_nickname", "usu_nombre", "usu_apellido") else ("📄" if campo in ("usu_rfc", "usu_curp", "usu_imss", "usu_ine") else ("📍" if campo in ("usu_calle", "usu_numero", "usu_colonia", "usu_municipio", "usu_estado", "usu_cp") else "•")))
        ctk.CTkLabel(wrapper, text=f"{icono} {texto}", font=TEXT_SM, text_color=TEXT_PRIMARY).grid(row=0, column=0, sticky="w")

        var = ctk.StringVar()
        estado["variables"][campo] = var
        entry = ctk.CTkEntry(
            wrapper,
            textvariable=var,
            height=36,
            show="*" if campo == "usu_password" else None,
        )
        entry.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        if "fecha" in campo.lower():
            entry.bind("<Button-1>", lambda _event, var=var: abrir_selector_fecha(wrapper, var))
        entry.configure(state="disabled")
        estado["entradas"][campo] = entry

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
        datos = {campo: variable.get().strip() for campo, variable in estado["variables"].items()}
        datos["confirmar_password"] = datos.get("usu_password", "")
        return datos

    def limpiar_formulario():
        estado["seleccionado"] = None
        for variable in estado["variables"].values():
            variable.set("")

    def cargar_en_formulario(usuario):
        estado["seleccionado"] = usuario
        for campo, variable in estado["variables"].items():
            if campo == "usu_password":
                variable.set("")
            else:
                variable.set(str(usuario.get(campo, "") or ""))
        bloquear_formulario()

    def crear_item_resultado(usuario, texto):
        """
        Crea un resultado alineado a la izquierda.
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

        item.bind("<Button-1>", lambda _event, seleccionado=usuario: cargar_en_formulario(seleccionado))
        label.bind("<Button-1>", lambda _event, seleccionado=usuario: cargar_en_formulario(seleccionado))

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
                text="Ingresa un dato de búsqueda para consultar usuarios.",
                font=TEXT_SM,
                text_color=TEXT_SECONDARY,
            ).pack(anchor="w", padx=18, pady=8)
            return

        for usuario in estado["resultados"]:
            texto = f"{usuario.get('usu_nickname', '-') }\n{usuario.get('usu_nombre', '')} {usuario.get('usu_apellido', '')}".strip()
            crear_item_resultado(usuario, texto)

    def cargar_resultados(termino=""):
        termino = (termino or "").strip()
        if not termino:
            estado["resultados"] = []
            pintar_resultados()
            messagebox.showwarning("Búsqueda requerida", "Ingresa un dato para buscar usuarios.")
            return
        estado["resultados"] = buscar_usuarios(termino)
        pintar_resultados()

    def guardar_nuevo():
        if estado.get("modo") != "nuevo":
            limpiar_formulario()
            desbloquear_formulario("nuevo")
            return

        exito, mensaje, _ = crear_usuario_admin(datos_formulario())
        if exito:
            messagebox.showinfo("Usuarios", mensaje)
            limpiar_formulario()
            bloquear_formulario()
            cargar_resultados(var_busqueda.get())
        else:
            messagebox.showerror("Usuarios", mensaje)

    def actualizar_seleccionado():
        seleccionado = estado.get("seleccionado")
        if not seleccionado:
            messagebox.showwarning("Usuarios", "Selecciona un usuario de la lista.")
            return

        if estado.get("modo") != "editar":
            desbloquear_formulario("editar")
            return

        confirmar = messagebox.askyesno(
            "Confirmar actualización",
            "¿Estás seguro de modificar los datos de este usuario en la base de datos?"
        )

        if not confirmar:
            return

        exito, mensaje, _ = actualizar_usuario_admin(
            seleccionado.get("id_usuario"),
            datos_formulario(),
        )
        if exito:
            messagebox.showinfo("Usuarios", mensaje)
            bloquear_formulario()
            cargar_resultados(var_busqueda.get())
        else:
            messagebox.showerror("Usuarios", mensaje)

    entry_busqueda.bind("<Return>", lambda _event: cargar_resultados(var_busqueda.get()))
    bloquear_formulario()
    pintar_resultados()
